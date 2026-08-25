"""
RAG System for Bank Document Querying
Uses ChromaDB for vector storage and sentence-transformers for embeddings
"""
import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class BankRAGSystem:
    """RAG system for bank document querying"""
    
    def __init__(
        self,
        chroma_url: Optional[str] = None,
        collection_name: str = "bank_documents",
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        persist_dir: Optional[str] = None,
    ):
        self.chroma_url = chroma_url or os.getenv("CHROMA_URL")
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize ChromaDB client
        # Use PersistentClient (local file storage) by default for simplicity
        # Only use HttpClient if CHROMA_URL is explicitly set
        if self.chroma_url:
            self.client = chromadb.HttpClient(
                host=self.chroma_url.replace("http://", "").split(":")[0],
                port=int(self.chroma_url.split(":")[-1]) if ":" in self.chroma_url else 8000,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            # Use local persistent storage - no network needed
            persist_path = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "/data/chroma")
            self.client = chromadb.PersistentClient(
                path=persist_path,
                settings=Settings(anonymized_telemetry=False)
            )
        
        # Initialize embedding model
        self.embedder = SentenceTransformer(embedding_model)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def _chunk_text(self, text: str, source: str, doc_type: str) -> List[DocumentChunk]:
        """Split text into overlapping chunks"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            if len(chunk_words) < 50:  # Skip very small chunks
                continue
            
            chunk_text = " ".join(chunk_words)
            chunk_id = hashlib.md5(f"{source}:{i}:{chunk_text[:50]}".encode()).hexdigest()[:16]
            
            chunks.append(DocumentChunk(
                id=chunk_id,
                content=chunk_text,
                metadata={
                    "source": source,
                    "doc_type": doc_type,
                    "chunk_index": i // (self.chunk_size - self.chunk_overlap),
                    "total_chunks": (len(words) + self.chunk_size - 1) // self.chunk_size,
                }
            ))
        
        return chunks
    
    def add_document(
        self,
        content: str,
        source: str,
        doc_type: str = "policy",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a document to the RAG system"""
        chunks = self._chunk_text(content, source, doc_type)
        
        # Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = self.embedder.encode(texts, show_progress_bar=False).tolist()
        
        # Prepare for ChromaDB
        ids = [c.id for c in chunks]
        metadatas = []
        for c in chunks:
            meta = c.metadata.copy()
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)
        
        # Add to collection
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return len(chunks)
    
    def add_documents_from_directory(self, directory: str, doc_type: str = "policy") -> Dict[str, int]:
        """Add all documents from a directory"""
        results = {}
        path = Path(directory)
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.json']:
                try:
                    if file_path.suffix.lower() == '.json':
                        with open(file_path) as f:
                            data = json.load(f)
                        content = json.dumps(data, indent=2)
                    else:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    count = self.add_document(
                        content=content,
                        source=str(file_path.relative_to(path)),
                        doc_type=doc_type
                    )
                    results[str(file_path.relative_to(path))] = count
                except Exception as e:
                    results[str(file_path.relative_to(path))] = f"Error: {e}"
        
        return results
    
    def query(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query the RAG system"""
        # Generate query embedding
        query_embedding = self.embedder.encode([query]).tolist()[0]
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
            include=['documents', 'metadatas', 'distances']
        )
        
        return {
            "query": query,
            "results": [
                {
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "similarity": round(1 - results['distances'][0][i], 4),
                }
                for i in range(len(results['ids'][0]))
            ]
        }
    
    def query_with_context(
        self,
        query: str,
        n_results: int = 5,
        max_context_length: int = 3000
    ) -> Dict[str, Any]:
        """Query and return formatted context for LLM"""
        results = self.query(query, n_results)
        
        context_parts = []
        total_length = 0
        
        for r in results['results']:
            part = f"[Source: {r['metadata'].get('source', 'unknown')}]\n{r['content']}"
            if total_length + len(part) > max_context_length:
                break
            context_parts.append(part)
            total_length += len(part)
        
        return {
            "query": query,
            "context": "\n\n---\n\n".join(context_parts),
            "sources": [r['metadata'].get('source', 'unknown') for r in results['results']],
            "similarities": [r['similarity'] for r in results['results']],
        }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        count = self.collection.count()
        
        # Sample some documents to get metadata distribution
        sample = self.collection.get(limit=min(100, count), include=['metadatas'])
        
        doc_types = {}
        sources = set()
        for meta in sample.get('metadatas', []):
            dt = meta.get('doc_type', 'unknown')
            doc_types[dt] = doc_types.get(dt, 0) + 1
            sources.add(meta.get('source', 'unknown'))
        
        return {
            "total_chunks": count,
            "unique_sources": len(sources),
            "doc_types": doc_types,
            "embedding_model": self.embedding_model_name,
        }
    
    def delete_collection(self):
        """Delete the entire collection"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )


# ============ PREDEFINED BANK DOCUMENT TEMPLATES ============

BANK_DOCUMENT_TEMPLATES = {
    "loan_policy": """
BANK LOAN POLICY DOCUMENT

PERSONAL LOAN POLICY
- Maximum loan amount: ₹50,00,000
- Interest rate range: 10.5% - 14.5% per annum
- Tenure: 12 to 84 months
- Minimum CIBIL score: 700
- Processing fee: 1.5% of loan amount + GST
- Prepayment charges: 2% of outstanding principal after 12 months
- Documentation required: PAN, Aadhaar, Income proof (salary slips/ITR), Bank statements

HOME LOAN POLICY
- Maximum loan amount: ₹10,00,00,000
- Interest rate range: 8.5% - 10.5% per annum
- Tenure: up to 30 years
- LTV ratio: up to 90% for loans up to ₹75L, 80% above
- Minimum CIBIL score: 700
- Processing fee: 0.5% of loan amount + GST
- No prepayment charges for floating rate loans

VEHICLE LOAN POLICY
- Maximum loan amount: ₹2,00,00,000
- Interest rate range: 9.0% - 12.0% per annum
- Tenure: up to 84 months
- LTV: up to 90% for new, 80% for used vehicles
- Minimum CIBIL score: 650
- Processing fee: 1% of loan amount + GST

COLLECTION POLICY
- Payment due reminder: Day 1, Day 7, Day 15
- Late payment fee: 2% per month on overdue amount
- Settlement offers: Up to 30% discount on principal for accounts >180 days overdue
- Legal action initiation: After 90 days overdue with notice
- Distress handling: Immediate escalation to senior officer

COMPLIANCE RULES
- No threatening language in communications
- All amounts must be exact from borrower records
- Automated messages must disclose automated nature
- Interest rates must match sanctioned rate exactly
- No promises outside policy limits
""",
    
    "rbai_guidelines": """
RBI GUIDELINES FOR LOAN RECOVERY

FAIR PRACTICES CODE
1. Banks shall not resort to undue harassment of borrowers
2. Recovery agents must carry identity cards
3. No calls before 8 AM or after 7 PM
4. No visits to workplace without consent
5. No disclosure of debt to third parties

SETTLEMENT GUIDELINES
- One-time settlement (OTS) schemes for NPA accounts
- Transparent criteria for OTS eligibility
- Board-approved delegation of powers
- Written communication of settlement terms

INTEREST RATE REGULATIONS
- External benchmark linking mandatory
- Reset frequency: at least once in 3 months
- Transparent spread disclosure
- No hidden charges

DATA PRIVACY
- Borrower data cannot be shared without consent
- Credit information reporting per CICRA
- Secure storage and transmission
""",
    
"product_catalog": """
BANK PRODUCT CATALOG 2024

PERSONAL LOAN PRODUCTS
1. Salary Plus Personal Loan
   - Rate: 10.75% p.a.
   - Max: ₹40,00,000
   - For salaried employees with min 2 years experience
   - Instant approval for existing customers

2. Professional Personal Loan
   - Rate: 11.25% p.a.
   - Max: ₹50,00,000
   - For doctors, CAs, engineers, architects
   - Flexible repayment options

3. Senior Citizen Personal Loan
   - Rate: 11.50% p.a.
   - Max: ₹20,00,000
   - Pensioners up to age 75
   - Minimal documentation

HOME LOAN PRODUCTS
1. Home Loan - Standard
   - Rate: 8.75% p.a. (floating)
   - Max: ₹10 Cr
   - Up to 30 years tenure
   - PMAY subsidy eligible

2. Home Loan - Top Up
   - Rate: 9.25% p.a.
   - Max: ₹50,00,000
   - For existing home loan customers
   - Minimal documentation

3. NRI Home Loan
   - Rate: 9.50% p.a.
   - Max: ₹5 Cr
   - For NRIs/PIOs
   - Power of attorney required

VEHICLE LOAN PRODUCTS
1. New Car Loan
   - Rate: 9.00% p.a.
   - Max: ₹2 Cr
   - Up to 100% on-road funding for select models

2. Used Car Loan
   - Rate: 11.50% p.a.
   - Max: ₹75,00,000
   - Car age up to 8 years
   - 80% LTV

3. Two Wheeler Loan
   - Rate: 10.50% p.a.
   - Max: ₹3,00,000
   - Up to 95% LTV
   - Quick approval
""",
    
    "credit_cards": """
CREDIT CARD PORTFOLIO 2024

PREMIUM CARDS
1. Signature Visa Infinite
   - Annual fee: ₹10,000
   - Rewards: 5% on dining, 3% on travel, 1.5% on other
   - Lounge access: Unlimited domestic, 8 international/year
   - Credit limit: ₹10L - ₹1Cr
   - Welcome benefit: 50,000 reward points

2. Platinum Select
   - Annual fee: ₹3,500
   - Rewards: 3% on dining, 2% on travel, 1% on other
   - Lounge access: 4 domestic/year
   - Credit limit: ₹5L - ₹50L
   - Welcome benefit: 15,000 reward points

STANDARD CARDS
3. Smart Shopper
   - Annual fee: ₹999
   - Rewards: 2% on groceries, 1.5% on fuel, 1% on other
   - Credit limit: ₹1L - ₹10L
   - Welcome benefit: 5,000 reward points

4. Young Professional
   - Annual fee: ₹499 (waived first year)
   - Rewards: 1.5% on all spends
   - Credit limit: ₹50K - ₹5L
   - Welcome benefit: 2,000 reward points

BUSINESS CARDS
5. Corporate Elite
   - Annual fee: ₹5,000
   - Rewards: 2% on business expenses, 1% on other
   - Expense management tools included
   - Credit limit: ₹10L - ₹2Cr
""",
    
    "digital_banking": """
DIGITAL BANKING SERVICES 2024

MOBILE APP FEATURES
- UPI payments with QR scan
- Bill payments (electricity, water, gas, DTH, broadband)
- Fund transfers (IMPS, NEFT, RTGS, UPI)
- Investment platform (mutual funds, FD, RD)
- Credit card management
- Loan application tracking
- Card control (block/unblock, set limits)

INTERNET BANKING
- Account statements & passbook
- Tax payment (income tax, GST, property tax)
- Scheduled transfers & standing instructions
- Trade finance (LC, BG, export/import)
- Cash management for corporates

SECURITY FEATURES
- Biometric login (fingerprint, face ID)
- 2FA with OTP and grid authentication
- Transaction alerts (SMS, email, push)
- Device registration & management
- Virtual keyboard for password entry

WHATSAPP BANKING
- Balance enquiry
- Mini statement
- Credit card due & payment
- Loan EMI status
- Branch/ATM locator
- Complaint registration

CHATBOT (AI-powered)
- 24/7 customer support
- Product recommendations
- Complaint tracking
- FAQ automation
- Multi-language support (Hindi, English, 8 regional)
""",
    
    "npa_management": """
NPA MANAGEMENT & RECOVERY POLICY 2024

CLASSIFICATION NORMS (RBI)
- SMA-0: Principal/interest overdue 1-30 days
- SMA-1: Principal/interest overdue 31-60 days
- SMA-2: Principal/interest overdue 61-90 days
- NPA: Overdue > 90 days

PROVISIONING REQUIREMENTS
- Standard assets: 0.40%
- Sub-standard: 15% (secured), 25% (unsecured)
- Doubtful (up to 1 year): 25% (secured), 100% (unsecured)
- Doubtful (1-3 years): 40% (secured), 100% (unsecured)
- Doubtful (>3 years): 100%
- Loss assets: 100%

RECOVERY MECHANISMS
1. Internal Recovery
   - Tele-calling: Day 1, 7, 15, 30, 60, 90
   - Field visits: After 60 days overdue
   - Legal notices: After 90 days

2. External Recovery Agents
   - Empanelled agencies only
   - Code of conduct compliance mandatory
   - No coercion, harassment, or intimidation
   - Monthly performance review

3. Legal Recovery
   - SARFAESI Act: Secured assets > ₹1L
   - DRT: Claims > ₹20L
   - Lok Adalat: Up to ₹20L
   - IBC: Corporate borrowers > ₹1Cr

ONE-TIME SETTLEMENT (OTS)
- Eligibility: NPA > 2 years, or written-off accounts
- Discount: Up to 50% on principal for >5 year old NPAs
- Board approval required for >₹1Cr
- No fresh lending for 2 years post-settlement

ASSET RECONSTRUCTION
- Sale to ARCs at fair value
- Transparent bidding process
- Minimum reserve price policy
- RBI reporting within 7 days
""",
    
    "risk_management": """
RISK MANAGEMENT FRAMEWORK 2024

CREDIT RISK
- Internal rating models (10-grade scale)
- Single borrower limit: 15% of Tier I capital
- Group exposure limit: 25% of Tier I capital
- Sectoral caps: Real estate 15%, Infrastructure 20%
- Unsecured lending cap: 10% of advances

MARKET RISK
- VaR limit: 1.5% of Tier I capital (99%, 10-day)
- Interest rate risk: EaR limit 2% of NII
- Equity portfolio: 5% of Tier I capital
- FX open position: Overnight $10M, Intraday $25M

OPERATIONAL RISK
- BIA approach for capital charge
- Key risk indicators (KRIs) monitored monthly
- Loss data collection since 2018
- BCP/DR tested quarterly
- Cyber risk: Dedicated SOC, 24/7 monitoring

LIQUIDITY RISK
- LCR: Minimum 100% (regulatory), 110% (internal)
- NSFR: Minimum 100%
- ALM gaps monitored bucket-wise
- Contingency funding plan updated annually

COUNTERPARTY RISK
- Bank lines: External rating based limits
- Corporate exposures: Internal rating + financial analysis
- CCP exposures: As per RBI guidelines
- Derivative limits: PFE + add-on methodology
""",
    
    "msme_lending": """
MSME LENDING POLICY 2024

TARGET SEGMENTS
- Manufacturing: Up to ₹25Cr
- Services: Up to ₹10Cr
- Trading: Up to ₹5Cr
- Startups: Up to ₹5Cr (under CGTMSE)

PRODUCTS
1. Working Capital
   - Cash Credit: 8.5% - 11.5%
   - Overdraft: 9% - 12%
   - Bill Discounting: 7.5% - 10%
   - Supply Chain Finance: 7% - 9.5%

2. Term Loans
   - Machinery: 8.75% - 11%
   - Expansion: 9% - 11.5%
   - Technology Upgradation: 8.5% - 10.5%

3. Government Schemes
   - CGTMSE: Up to ₹5Cr, 75-85% guarantee
   - PMEGP: Up to ₹25L (mfg), ₹10L (service)
   - MUDRA: Shishu ₹50K, Kishore ₹5L, Tarun ₹10L
   - Stand-Up India: ₹10L - ₹1Cr (SC/ST/Women)

COLLATERAL REQUIREMENTS
- Up to ₹10L: No collateral (under CGTMSE)
- ₹10L - ₹2Cr: Primary security + CGTMSE
- Above ₹2Cr: Full collateral + CGTMSE optional

DIGITAL MSME LENDING
- GST return based assessment
- Bank statement analysis (12 months)
- Credit bureau score integration
- 48-hour sanction for up to ₹50L
- Fully digital documentation
""",
}

def initialize_bank_rag(
    chroma_url: Optional[str] = None,
    collection_name: str = "bank_documents",
    data_dir: Optional[str] = None,
    persist_dir: Optional[str] = None
) -> BankRAGSystem:
    """Initialize RAG system with bank documents"""
    rag = BankRAGSystem(
        chroma_url=chroma_url, 
        collection_name=collection_name,
        persist_dir=persist_dir
    )
    
    for doc_type, content in BANK_DOCUMENT_TEMPLATES.items():
        rag.add_document(
            content=content,
            source=f"template_{doc_type}",
            doc_type=doc_type,
            metadata={"category": "bank_policy", "version": "2024"}
        )
    
    # Add custom documents from directory if provided
    if data_dir:
        rag.add_documents_from_directory(data_dir)
    
    return rag