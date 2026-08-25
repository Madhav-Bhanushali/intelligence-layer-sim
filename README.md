# Intelligence Layer Simulation

A production-ready simulation of the intelligence layer for loan collection and marketing bots, with support for local GPU model serving, RAG-based document querying, and comprehensive latency monitoring.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENCE LAYER PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  User Input ──► Context Assembler ──► Model Router ──► Prompt Builder     │
│       │                                                                     │
│       ▼                                                                     │
│  Model Client (Local/Remote) ◄── Latency Tracker                           │
│       │                                                                     │
│       ▼                                                                     │
│  Output Validator ──► Final Output                                         │
│       │                                                                     │
│       ▼                                                                     │
│  RAG Enhancement (Optional)                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

### Core Pipeline
- **Context Assembler**: Merges mock borrower/lead data into structured context
- **Model Router**: Rule-based classification (routine vs complex) with keyword matching
- **Prompt Builder**: Versioned prompts with hash tracking (system + few-shot)
- **Model Client**: Multi-provider support (Local/Ollama/vLLM, Groq, Gemini, Anthropic)
- **Output Validator**: Strict amount matching, tone checking, distress detection
- **Trace Export**: Full pipeline traces saved as JSON/Markdown

### Local Model Serving (GPU)
- **Ollama**: Easy local inference (llama3.2:3b for routine, llama3.1:8b for complex)
- **vLLM**: High-throughput OpenAI-compatible API for production workloads
- **Latency Tracking**: TTFT, TBT, tokens/sec, percentiles (P50/P95/P99)

### RAG System
- **Vector DB**: ChromaDB for document storage
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Bank Templates**: Pre-loaded loan policies, RBI guidelines, product catalog
- **Query API**: Context retrieval with similarity scoring

### Monitoring & Observability
- Real-time latency dashboard
- Per-model/provider breakdown
- CSV export for analysis
- Health checks for all services

### Frontend
- Streamlit-based dashboard
- Scenario runner with full trace visualization
- RAG query interface
- Document management
- Model configuration

## Quick Start

### Prerequisites
- Python 3.11+
- NVIDIA GPU (for local models) or API keys (Groq/Gemini/Anthropic)
- 16GB+ RAM recommended

### 1. Local Development (No Docker)

```bash
# Clone and setup
cd intelligence-layer-sim
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start all services locally
python scripts/start_local.py
```

This starts:
- Ollama (port 11434) - pulls llama3.2:3b & llama3.1:8b
- ChromaDB (port 8003)
- FastAPI (port 8080)
- Streamlit (port 8501)

### 2. Docker Deployment (Recommended for Production)

```bash
cd deployment
docker compose up -d --build
```

Services:
- API: http://localhost:8080
- Frontend: http://localhost:8501
- Ollama: http://localhost:11434
- vLLM Routine: http://localhost:8001
- vLLM Complex: http://localhost:8002
- ChromaDB: http://localhost:8003

### 3. Remote GPU Deployment

```bash
# Deploy to remote GPU server
python scripts/deploy_remote.py your-gpu-server \
  --user ubuntu \
  --key ~/.ssh/id_rsa \
  --gpu-count 2
```

## Usage

### Run Scenarios (CLI)

```bash
# List cases
python -m src.run_scenario --bot collection --list
python -m src.run_scenario --bot marketing --list

# Run with local models (mock mode - no API needed)
python -m src.run_scenario --bot collection --case ramesh_negotiation --mock --save-json --save-md

# Run with Groq
export GROQ_API_KEY=your-key
python -m src.run_scenario --bot marketing --case sneha_tailored_pitch --save-json --save-md

# Run with local Ollama
python -m src.run_scenario --bot collection --case priya_payment_reminder --provider local --save-json --save-md
```

### API Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Run scenario
curl -X POST http://localhost:8080/scenario/run \
  -H "Content-Type: application/json" \
  -d '{"bot": "collection", "case": "ramesh_negotiation", "provider": "local"}'

# RAG query
curl -X POST http://localhost:8080/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the maximum personal loan amount?", "n_results": 5}'

# Latency stats
curl http://localhost:8080/latency/stats

# List available models
curl http://localhost:8080/models/available
```

### Frontend

Open http://localhost:8501 for the Streamlit dashboard with:
- **Dashboard**: System overview, latency metrics, quick scenario runner
- **Scenario Runner**: Full trace visualization (router → prompt → model → validator)
- **Latency Monitor**: Real-time charts, percentiles, per-model breakdown
- **RAG Query**: Natural language search over bank documents
- **Document Manager**: Add/manage documents in vector DB
- **Settings**: Model configuration, environment variables

## Test Cases

### Collection Bot (8 cases)
| Case | Type | Description |
|------|------|-------------|
| `priya_payment_reminder` | Routine | Due date query |
| `rajesh_payment_confirmation` | Routine | Payment confirmation |
| `meena_due_notice` | Routine | Upcoming payment |
| `ramesh_negotiation` | Complex | Partial payment proposal |
| `amit_dispute` | Complex | Disputes debt |
| `sunita_settlement` | Complex | Settlement offer |
| `vikram_repayment_plan` | Complex | Repayment plan request |
| `kavya_bad_case` | **Validator Test** | Prompt injection attempt |

### Marketing Bot (8 cases)
| Case | Type | Description |
|------|------|-------------|
| `arjun_offer_notice` | Routine | Standard product announcement |
| `rohit_eligibility_check` | Routine | Simple eligibility query |
| `karan_simple_announcement` | Routine | Offer notification inquiry |
| `priya_preapproved` | Complex | Specific terms question |
| `sneha_tailored_pitch` | Complex | Personalized pitch request |
| `deepika_terms_question` | Complex | Detailed terms inquiry |
| `ananya_complex_query` | Complex | Business-specific scenario |
| `rahul_bad_case` | **Validator Test** | Prompt injection attempt |

## Configuration

### Environment Variables

```bash
# Model Provider
MODEL_PROVIDER=local          # local, groq, gemini, anthropic, mock
GROQ_API_KEY=your-key
GEMINI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key

# Local Models
OLLAMA_BASE_URL=http://localhost:11434
VLLM_ROUTINE_URL=http://localhost:8001/v1
VLLM_COMPLEX_URL=http://localhost:8002/v1
LOCAL_ROUTINE_MODEL=llama3.2:3b
LOCAL_COMPLEX_MODEL=llama3.1:8b

# RAG
CHROMA_URL=http://localhost:8000
```

### Model Selection

| Provider | Routine Model | Complex Model |
|----------|---------------|---------------|
| Local (Ollama) | llama3.2:3b | llama3.1:8b |
| vLLM | Llama-3.2-3B-Instruct | Llama-3.1-8B-Instruct |
| Groq | gpt-oss-20b | gpt-oss-120b |
| Gemini | gemini-1.5-flash | gemini-1.5-pro |
| Anthropic | claude-haiku-4-5-20251001 | claude-sonnet-5 |

## Project Structure

```
intelligence-layer-sim/
├── README.md
├── requirements.txt
├── data/
│   ├── collection_cases.json
│   └── marketing_cases.json
├── src/
│   ├── context_assembler.py
│   ├── prompt_builder.py
│   ├── model_router.py
│   ├── model_client.py          # Multi-provider (API)
│   ├── output_validator.py
│   └── run_scenario.py
├── models/
│   └── local_client.py          # Local models with latency tracking
├── rag/
│   └── bank_rag.py              # RAG system with ChromaDB
├── api/
│   └── main.py                  # FastAPI backend
├── frontend/
│   └── app.py                   # Streamlit dashboard
├── prompts/
│   ├── collection_system.md
│   ├── collection_fewshot.md
│   ├── marketing_system.md
│   └── marketing_fewshot.md
├── deployment/
│   ├── docker-compose.yml
│   ├── Dockerfile.api
│   └── Dockerfile.frontend
├── scripts/
│   ├── deploy_remote.py         # SSH deployment to GPU server
│   └── start_local.py           # Local service manager
└── traces/                      # Generated trace files
```

## Latency Tracking

The local client tracks:
- **Total Latency**: End-to-end request time
- **TTFT (Time to First Token)**: Streaming responsiveness
- **TBT (Time Between Tokens)**: Token generation speed
- **Tokens/Second**: Throughput metric
- **Percentiles**: P50, P95, P99
- **Per-Model/Provider Breakdown**

Export to CSV:
```python
local_client.export_latency_csv("latency_report.csv")
```

## Validation Rules

### Collection Bot
- **Allowed amounts**: `balance`, `settlement_offer` only
- **Banned words**: threaten, legal action, court, sue, harass, etc.
- **Distress keywords**: suicide, self-harm, hopeless (triggers escalation)

### Marketing Bot
- **Allowed amounts**: `max_amount`, `interest_rate` (numeric) only
- **Banned words**: guarantee, 0%, no risk, instant approval, etc.

## Adding Bank Documents

```bash
# Via API
curl -X POST http://localhost:8080/rag/add-document \
  -H "Content-Type: application/json" \
  -d '{"content": "New policy...", "source": "policy_v2.pdf", "doc_type": "policy"}'

# Via directory
curl -X POST http://localhost:8080/rag/add-directory \
  -H "Content-Type: application/json" \
  -d '{"directory": "/path/to/pdfs", "doc_type": "policy"}'
```

## License

MIT