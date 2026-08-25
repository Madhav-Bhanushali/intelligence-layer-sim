"""
FastAPI Backend for Intelligence Layer Simulation
Endpoints for bot simulation, RAG queries, latency monitoring, and model management
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import existing components
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.context_assembler import assemble_context, load_case, list_cases
from src.prompt_builder import build_prompt
from src.model_router import route_message
from src.output_validator import validate_output
from models.local_client import create_local_client, SyncLocalModelClient
from rag.bank_rag import BankRAGSystem, initialize_bank_rag, BANK_DOCUMENT_TEMPLATES


# ============ GLOBAL STATE ============

local_client: Optional[SyncLocalModelClient] = None
rag_system: Optional[BankRAGSystem] = None


# ============ PYDANTIC MODELS ============

class ScenarioRequest(BaseModel):
    bot: str = Field(..., pattern="^(collection|marketing)$")
    case: str
    provider: str = Field(default="local", pattern="^(local|groq|gemini|anthropic|mock)$")
    mock: bool = False
    save_trace: bool = False


class ScenarioResponse(BaseModel):
    case_id: str
    bot_type: str
    router: Dict[str, Any]
    model_result: Dict[str, Any]
    validator_result: Dict[str, Any]
    final_output: Optional[str]
    latency: Optional[Dict[str, Any]] = None


class RAGQueryRequest(BaseModel):
    query: str
    n_results: int = 5
    max_context_length: int = 3000


class RAGQueryResponse(BaseModel):
    query: str
    context: str
    sources: List[str]
    similarities: List[float]


class RAGAddDocumentRequest(BaseModel):
    content: str
    source: str
    doc_type: str = "policy"
    metadata: Optional[Dict[str, Any]] = None


class LatencyStatsResponse(BaseModel):
    total_calls: int
    successful_calls: int
    success_rate: float
    avg_total_ms: float
    avg_ttft_ms: float
    avg_tokens_per_sec: float
    p50_total_ms: float
    p95_total_ms: float
    p99_total_ms: float
    by_provider: Dict[str, Any]
    by_model: Dict[str, Any]


class ModelConfigRequest(BaseModel):
    provider: str
    routine_model: Optional[str] = None
    complex_model: Optional[str] = None
    ollama_url: Optional[str] = None
    vllm_routine_url: Optional[str] = None
    vllm_complex_url: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]
    models_loaded: List[str]


# ============ LIFESPAN ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    global local_client, rag_system
    
    # Initialize local model client
    local_client = create_local_client()
    
    # Initialize RAG system
    try:
        rag_system = initialize_bank_rag()
        print("RAG system initialized")
    except Exception as e:
        print(f"RAG initialization warning: {e}")
        rag_system = BankRAGSystem()
    
    yield
    
    # Cleanup
    if local_client:
        local_client.close()


# ============ APP ============

app = FastAPI(
    title="Intelligence Layer Simulation API",
    description="API for loan bot intelligence layer with local models, RAG, and latency tracking",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ HELPER FUNCTIONS ============

def run_scenario_pipeline(
    bot: str,
    case_id: str,
    provider: str = "local",
    mock: bool = False
) -> Dict[str, Any]:
    """Run the complete intelligence layer pipeline with latency tracking"""
    
    import time
    pipeline_start = time.perf_counter()
    latency_breakdown = {}
    
    # Load case and assemble context
    context_start = time.perf_counter()
    case = load_case(bot, case_id)
    context = assemble_context(case)
    current_message = case.get("current_message", "")
    latency_breakdown["context_assembly_ms"] = round((time.perf_counter() - context_start) * 1000, 2)
    
    # Router decision
    router_start = time.perf_counter()
    classification, reason = route_message(bot, current_message)
    latency_breakdown["router_ms"] = round((time.perf_counter() - router_start) * 1000, 2)
    
    # Build prompt
    prompt_start = time.perf_counter()
    prompt = build_prompt(context, current_message)
    latency_breakdown["prompt_build_ms"] = round((time.perf_counter() - prompt_start) * 1000, 2)
    
    # Model call
    model_start = time.perf_counter()
    if mock:
        import os
        os.environ["MOCK_MODE"] = "true"
    
    if provider == "local" and local_client:
        model_result = local_client.call_model(
            messages=prompt["messages"],
            classification=classification,
            provider="auto"
        )
    else:
        # Fallback to external providers (would need their clients)
        from src.model_client import call_model_by_type
        model_result = call_model_by_type(prompt["messages"], classification)
    latency_breakdown["model_call_ms"] = round((time.perf_counter() - model_start) * 1000, 2)
    
    # Validator
    validator_start = time.perf_counter()
    if model_result.get("success"):
        validator_result = validate_output(model_result["output"], context)
    else:
        validator_result = {"passed": False, "reason": "Model call failed"}
    latency_breakdown["validator_ms"] = round((time.perf_counter() - validator_start) * 1000, 2)
    
    # Final output
    final_output = model_result["output"] if model_result.get("success") and validator_result.get("passed") else None
    
    total_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)
    latency_breakdown["total_ms"] = total_ms
    
    # Add model's internal latency if available
    model_latency = model_result.get("latency")
    
    return {
        "case_id": case_id,
        "bot_type": bot,
        "context": context,
        "router": {"classification": classification, "reason": reason},
        "prompt_version": prompt["version_info"],
        "model_result": model_result,
        "validator_result": validator_result,
        "final_output": final_output,
        "latency": {
            "total_ms": total_ms,
            "breakdown": latency_breakdown,
            "model_internal": model_latency
        }
    }


# ============ ENDPOINTS ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = {
        "api": "healthy",
        "local_models": "unknown",
        "rag": "unknown",
    }
    
    # Check local models
    if local_client:
        try:
            stats = local_client.get_latency_stats()
            services["local_models"] = "healthy" if "error" not in stats else "degraded"
        except:
            services["local_models"] = "unhealthy"
    
    # Check RAG
    if rag_system:
        try:
            stats = rag_system.get_collection_stats()
            services["rag"] = "healthy" if stats.get("total_chunks", 0) > 0 else "empty"
        except:
            services["rag"] = "unhealthy"
    
    models_loaded = []
    if local_client:
        try:
            stats = local_client.get_latency_stats()
            if "by_model" in stats:
                models_loaded = list(stats["by_model"].keys())
        except:
            pass
    
    return HealthResponse(
        status="healthy" if all(v in ["healthy", "empty"] for v in services.values()) else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        services=services,
        models_loaded=models_loaded
    )


# --- Scenario Endpoints ---

@app.get("/cases/{bot}")
async def list_cases_endpoint(bot: str):
    """List available cases for a bot type"""
    if bot not in ["collection", "marketing"]:
        raise HTTPException(400, "Bot must be 'collection' or 'marketing'")
    return {"bot": bot, "cases": list_cases(bot)}


@app.post("/scenario/run", response_model=ScenarioResponse)
async def run_scenario(request: ScenarioRequest):
    """Run a complete scenario through the intelligence layer"""
    try:
        result = run_scenario_pipeline(
            bot=request.bot,
            case_id=request.case,
            provider=request.provider,
            mock=request.mock
        )
        return ScenarioResponse(**result)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {str(e)}")


@app.post("/scenario/batch")
async def run_batch_scenarios(
    bot: str,
    cases: List[str],
    provider: str = "local",
    mock: bool = False,
    background_tasks: BackgroundTasks = None
):
    """Run multiple scenarios"""
    results = []
    for case in cases:
        try:
            result = run_scenario_pipeline(bot, case, provider, mock)
            results.append(result)
        except Exception as e:
            results.append({"case": case, "error": str(e)})
    
    return {"results": results, "total": len(results)}


# --- Model Management ---

@app.get("/models/available")
async def get_available_models():
    """Get available models from local providers"""
    models = {
        "ollama": [],
        "vllm_routine": [],
        "vllm_complex": [],
    }
    
    if local_client:
        # Try to get models from Ollama
        try:
            import httpx
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{ollama_url}/api/tags", timeout=5.0)
                if resp.status_code == 200:
                    models["ollama"] = [m["name"] for m in resp.json().get("models", [])]
        except:
            pass
        
        # Get vLLM models
        for key, url_env in [("vllm_routine", "VLLM_ROUTINE_URL"), ("vllm_complex", "VLLM_COMPLEX_URL")]:
            try:
                url = os.getenv(url_env, "").replace("/v1", "/v1/models")
                if url:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(url, timeout=5.0)
                        if resp.status_code == 200:
                            models[key] = [m["id"] for m in resp.json().get("data", [])]
            except:
                pass
    
    return models


@app.post("/models/config")
async def update_model_config(request: ModelConfigRequest):
    """Update model configuration"""
    global local_client
    
    # Update environment variables
    if request.ollama_url:
        os.environ["OLLAMA_BASE_URL"] = request.ollama_url
    if request.vllm_routine_url:
        os.environ["VLLM_ROUTINE_URL"] = request.vllm_routine_url
    if request.vllm_complex_url:
        os.environ["VLLM_COMPLEX_URL"] = request.vllm_complex_url
    if request.routine_model:
        os.environ["LOCAL_ROUTINE_MODEL"] = request.routine_model
    if request.complex_model:
        os.environ["LOCAL_COMPLEX_MODEL"] = request.complex_model
    
    # Recreate client
    if local_client:
        local_client.close()
    local_client = create_local_client()
    
    return {"status": "updated", "config": {
        "provider": request.provider,
        "routine_model": os.getenv("LOCAL_ROUTINE_MODEL"),
        "complex_model": os.getenv("LOCAL_COMPLEX_MODEL"),
    }}


# --- Latency Endpoints ---

@app.get("/latency/stats", response_model=LatencyStatsResponse)
async def get_latency_stats():
    """Get latency statistics"""
    if not local_client:
        raise HTTPException(503, "Local client not initialized")
    
    stats = local_client.get_latency_stats()
    if "error" in stats:
        raise HTTPException(404, stats["error"])
    
    return LatencyStatsResponse(**stats)


@app.get("/latency/history")
async def get_latency_history(limit: int = Query(100, ge=1, le=1000)):
    """Get recent latency history"""
    if not local_client:
        raise HTTPException(503, "Local client not initialized")
    
    history = local_client._async_client.latency_history[-limit:]
    return {
        "history": [
            {
                "timestamp": m.timestamp,
                "model": m.model,
                "provider": m.provider,
                "success": m.success,
                "total_ms": m.total_ms,
                "ttft_ms": m.ttft_ms,
                "tokens_per_second": m.tokens_per_second,
                "error": m.error,
            }
            for m in history
        ]
    }


@app.post("/latency/export")
async def export_latency_csv(filepath: str = "latency_export.csv"):
    """Export latency data to CSV"""
    if not local_client:
        raise HTTPException(503, "Local client not initialized")
    
    local_client.export_latency_csv(filepath)
    return {"status": "exported", "filepath": filepath}


@app.post("/latency/reset")
async def reset_latency_history():
    """Reset latency history"""
    if not local_client:
        raise HTTPException(503, "Local client not initialized")
    
    local_client._async_client.latency_history.clear()
    return {"status": "reset"}


# --- RAG Endpoints ---

@app.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """Query the RAG system"""
    if not rag_system:
        raise HTTPException(503, "RAG system not initialized")
    
    try:
        result = rag_system.query_with_context(
            query=request.query,
            n_results=request.n_results,
            max_context_length=request.max_context_length
        )
        return RAGQueryResponse(**result)
    except Exception as e:
        raise HTTPException(500, f"RAG query failed: {str(e)}")


@app.post("/rag/add-document")
async def rag_add_document(request: RAGAddDocumentRequest):
    """Add a document to the RAG system"""
    if not rag_system:
        raise HTTPException(503, "RAG system not initialized")
    
    try:
        count = rag_system.add_document(
            content=request.content,
            source=request.source,
            doc_type=request.doc_type,
            metadata=request.metadata
        )
        return {"status": "added", "chunks": count}
    except Exception as e:
        raise HTTPException(500, f"Failed to add document: {str(e)}")


@app.post("/rag/add-directory")
async def rag_add_directory(directory: str, doc_type: str = "policy"):
    """Add all documents from a directory"""
    if not rag_system:
        raise HTTPException(503, "RAG system not initialized")
    
    try:
        results = rag_system.add_documents_from_directory(directory, doc_type)
        return {"status": "completed", "results": results}
    except Exception as e:
        raise HTTPException(500, f"Failed to add directory: {str(e)}")


@app.get("/rag/stats")
async def rag_stats():
    """Get RAG collection statistics"""
    if not rag_system:
        raise HTTPException(503, "RAG system not initialized")
    
    return rag_system.get_collection_stats()


@app.post("/rag/reinitialize")
async def rag_reinitialize():
    """Reinitialize RAG with default bank documents"""
    global rag_system
    try:
        rag_system = initialize_bank_rag()
        return {"status": "reinitialized", "stats": rag_system.get_collection_stats()}
    except Exception as e:
        raise HTTPException(500, f"Reinitialization failed: {str(e)}")


# --- Utility Endpoints ---

@app.get("/prompts/templates")
async def get_prompt_templates():
    """Get available prompt templates"""
    return {
        "collection": {
            "system": "collection_system.md",
            "fewshot": "collection_fewshot.md"
        },
        "marketing": {
            "system": "marketing_system.md",
            "fewshot": "marketing_fewshot.md"
        }
    }


@app.get("/bank/templates")
async def get_bank_templates():
    """Get available bank document templates"""
    return {k: len(v) for k, v in BANK_DOCUMENT_TEMPLATES.items()}


# ============ MAIN ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)