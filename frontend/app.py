"""
Streamlit Frontend for Intelligence Layer Simulation
"""
import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List
import time
import os
from functools import wraps

# Page config
st.set_page_config(
    page_title="Intelligence Layer Simulation",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL - read from environment variable for Docker compatibility
API_URL = os.getenv("API_URL", "http://localhost:8080")

# ============ HELPER FUNCTIONS ============

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry API calls on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.ConnectionError:
                    last_error = "Cannot connect to API. Is the backend running?"
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
                    st.error(last_error)
                    return {}
                except Exception as e:
                    last_error = f"API error: {e}"
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
                    st.error(last_error)
                    return {}
            return {}
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=1.0)
def api_get(endpoint: str, params: Dict = None) -> Dict:
    """Make GET request to API with retry"""
    resp = requests.get(f"{API_URL}{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

@retry_on_failure(max_retries=3, delay=1.0)
def api_post(endpoint: str, data: Dict = None) -> Dict:
    """Make POST request to API with retry"""
    resp = requests.post(f"{API_URL}{endpoint}", json=data, timeout=60)
    resp.raise_for_status()
    return resp.json()

# ============ SIDEBAR ============

with st.sidebar:
    st.title("🤖 Intelligence Layer")
    st.caption("Loan Bot Simulation & Monitoring")
    
    # Health check
    health = api_get("/health")
    if health:
        status = health.get("status", "unknown")
        if status == "healthy":
            st.success("✅ System Healthy")
        elif status == "degraded":
            st.warning("⚠️ System Degraded")
        else:
            st.error("❌ System Unhealthy")
        
        with st.expander("Service Status"):
            for service, state in health.get("services", {}).items():
                icon = "✅" if state == "healthy" else "⚠️" if state == "degraded" else "❌"
                st.write(f"{icon} {service}: {state}")
        
        if health.get("models_loaded"):
            st.write("**Models Loaded:**")
            for m in health["models_loaded"]:
                st.write(f"  • {m}")
    
    st.divider()
    
    # Navigation
    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "🧪 Scenario Runner", "📊 Latency Monitor", "🔍 RAG Query", "📚 Document Manager", "⚙️ Settings"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Quick actions
    if st.button("🔄 Refresh Health"):
        st.rerun()
    
    if st.button("📥 Export Latency CSV"):
        result = api_post("/latency/export", {"filepath": "latency_export.csv"})
        if result:
            st.success(f"Exported to {result.get('filepath')}")
    
    if st.button("🗑️ Reset Latency History"):
        result = api_post("/latency/reset")
        if result:
            st.success("Latency history reset")

# ============ PAGE: DASHBOARD ============

if page == "🏠 Dashboard":
    st.header("📊 Dashboard")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    latency_stats = api_get("/latency/stats")
    if latency_stats and "error" not in latency_stats:
        with col1:
            st.metric("Total Calls", latency_stats.get("total_calls", 0))
        with col2:
            st.metric("Success Rate", f"{latency_stats.get('success_rate', 0):.1f}%")
        with col3:
            st.metric("Avg Latency", f"{latency_stats.get('avg_total_ms', 0):.0f} ms")
        with col4:
            st.metric("Avg Tokens/sec", f"{latency_stats.get('avg_tokens_per_sec', 0):.1f}")
    else:
        for col in [col1, col2, col3, col4]:
            col.metric("No Data", "—")
    
    st.divider()
    
    # Recent activity
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Recent Latency History")
        history = api_get("/latency/history", {"limit": 20})
        if history and history.get("history"):
            df = pd.DataFrame(history["history"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
            fig = px.line(
                df, x="timestamp", y="total_ms", color="model",
                title="Latency Over Time",
                labels={"total_ms": "Total Latency (ms)", "timestamp": "Time"}
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No latency data yet. Run some scenarios!")
    
    with col2:
        st.subheader("🤖 Model Performance")
        if latency_stats and "by_model" in latency_stats:
            model_data = []
            for model, stats in latency_stats["by_model"].items():
                model_data.append({
                    "Model": model,
                    "Calls": stats["count"],
                    "Avg Latency (ms)": stats["avg_total_ms"],
                    "Avg TTFT (ms)": stats["avg_ttft_ms"],
                    "Tokens/sec": stats["avg_tokens_per_sec"]
                })
            
            df_models = pd.DataFrame(model_data)
            st.dataframe(df_models, use_container_width=True, hide_index=True)
            
            # Bar chart
            fig = px.bar(
                df_models, x="Model", y="Avg Latency (ms)",
                title="Average Latency by Model"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No model performance data yet.")
    
    # Quick scenario runner
    st.divider()
    st.subheader("🚀 Quick Scenario Test")
    
    cases = api_get("/cases/collection")
    coll_cases = cases.get("cases", []) if cases else []
    cases = api_get("/cases/marketing")
    mkt_cases = cases.get("cases", []) if cases else []
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        bot_type = st.selectbox("Bot", ["collection", "marketing"])
    with col2:
        case_options = coll_cases if bot_type == "collection" else mkt_cases
        case_id = st.selectbox("Case", case_options)
    with col3:
        provider = st.selectbox("Provider", ["local", "groq", "gemini", "mock"])
    
    if st.button("▶️ Run Scenario", type="primary"):
        with st.spinner("Running scenario..."):
            result = api_post("/scenario/run", {
                "bot": bot_type,
                "case": case_id,
                "provider": provider,
                "mock": provider == "mock",
                "save_trace": True
            })
        
        if result:
            st.success("Scenario completed!")
            
            # Show results
            col1, col2 = st.columns(2)
            with col1:
                st.json({
                    "Router": result.get("router"),
                    "Validator": result.get("validator_result"),
                })
            with col2:
                if result.get("final_output"):
                    st.text_area("Output", result["final_output"], height=200)
                else:
                    st.error("BLOCKED: " + result.get("validator_result", {}).get("reason", "Unknown"))
            
            if result.get("latency"):
                st.json({"Latency": result["latency"]})


# ============ PAGE: SCENARIO RUNNER ============

elif page == "🧪 Scenario Runner":
    st.header("🧪 Scenario Runner")
    st.caption("Run complete intelligence layer pipeline with full trace")
    
    # Configuration
    col1, col2, col3 = st.columns(3)
    with col1:
        bot_type = st.selectbox("Bot Type", ["collection", "marketing"], key="runner_bot")
    with col2:
        cases = api_get(f"/cases/{bot_type}")
        case_options = cases.get("cases", []) if cases else []
        case_id = st.selectbox("Case ID", case_options, key="runner_case")
    with col3:
        provider = st.selectbox("Provider", ["local", "groq", "gemini", "anthropic", "mock"], key="runner_provider")
    
    mock_mode = st.checkbox("Mock Mode (no API calls)", value=(provider == "mock"))
    save_trace = st.checkbox("Save Trace (JSON + MD)", value=True)
    
    # Show case details
    if case_id:
        case = api_get(f"/cases/{bot_type}")
        # Load case details from local file
        try:
            import sys
            sys.path.insert(0, "..")
            from src.context_assembler import load_case
            case_data = load_case(bot_type, case_id)
            
            with st.expander("📋 Case Details"):
                st.json({
                    "bot_type": case_data.get("bot_type"),
                    "borrower_name": case_data.get("borrower_name") or case_data.get("lead_name"),
                    "balance": case_data.get("balance"),
                    "interest_rate": case_data.get("interest_rate"),
                    "max_amount": case_data.get("max_amount"),
                    "case_state": case_data.get("case_state"),
                    "current_message": case_data.get("current_message"),
                })
        except:
            pass
    
    if st.button("▶️ Run Scenario", type="primary", use_container_width=True):
        if not case_id:
            st.error("Select a case first")
        else:
            with st.spinner("Running pipeline..."):
                progress = st.progress(0)
                steps = ["Loading case", "Router decision", "Building prompt", "Model call", "Validation", "Complete"]
                
                result = api_post("/scenario/run", {
                    "bot": bot_type,
                    "case": case_id,
                    "provider": provider,
                    "mock": mock_mode,
                    "save_trace": save_trace
                })
                
                progress.progress(100)
                
                if result:
                    st.success("✅ Scenario completed!")
                    
                    # Trace display
                    tabs = st.tabs(["📋 Trace", "🤖 Model Output", "✅ Validator", "📊 Latency", "💾 Raw JSON"])
                    
                    with tabs[0]:
                        st.subheader("Pipeline Trace")
                        
                        # Step 1: Context
                        with st.expander("1️⃣ Assembled Context", expanded=True):
                            st.json(result.get("context", {}))
                        
                        # Step 2: Router
                        with st.expander("2️⃣ Router Decision", expanded=True):
                            st.json(result.get("router", {}))
                        
                        # Step 3: Prompt
                        with st.expander("3️⃣ Prompt Version", expanded=False):
                            st.json(result.get("prompt_version", {}))
                        
                        # Step 4: Model
                        with st.expander("4️⃣ Model Called", expanded=True):
                            mr = result.get("model_result", {})
                            st.write(f"**Model:** {mr.get('model')} ({mr.get('provider', 'unknown')})")
                            st.write(f"**Success:** {mr.get('success')}")
                            if mr.get("latency"):
                                lat = mr["latency"]
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("Total", f"{lat.get('total_ms', 0):.0f} ms")
                                col2.metric("TTFT", f"{lat.get('ttft_ms', 0):.0f} ms")
                                col3.metric("TBT", f"{lat.get('tbt_ms', 0):.0f} ms")
                                col4.metric("Tokens/s", f"{lat.get('tokens_per_second', 0):.1f}")
                        
                        # Step 5: Validator
                        with st.expander("5️⃣ Validator Result", expanded=True):
                            st.json(result.get("validator_result", {}))
                        
                        # Step 6: Final
                        with st.expander("6️⃣ Final Output", expanded=True):
                            if result.get("final_output"):
                                st.success("✅ PASSED")
                                st.text_area("Output", result["final_output"], height=150)
                            else:
                                st.error("❌ BLOCKED")
                                st.write(result.get("validator_result", {}).get("reason", "Unknown"))
                    
                    with tabs[1]:
                        mr = result.get("model_result", {})
                        if mr.get("output"):
                            st.text_area("Raw Model Output", mr["output"], height=300)
                        else:
                            st.write("No output (model call failed)")
                            if mr.get("error"):
                                st.error(mr["error"])
                    
                    with tabs[2]:
                        st.json(result.get("validator_result", {}))
                    
                    with tabs[3]:
                        st.json(result.get("latency", {}))
                    
                    with tabs[4]:
                        st.json(result)


# ============ PAGE: LATENCY MONITOR ============

elif page == "📊 Latency Monitor":
    st.header("📊 Latency Monitor")
    
    latency_stats = api_get("/latency/stats")
    
    if not latency_stats or "error" in latency_stats:
        st.info("No latency data available. Run some scenarios first!")
    else:
        # Summary metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Total Calls", latency_stats["total_calls"])
        with col2:
            st.metric("Success Rate", f"{latency_stats['success_rate']:.1f}%")
        with col3:
            st.metric("Avg Total", f"{latency_stats['avg_total_ms']:.0f} ms")
        with col4:
            st.metric("Avg TTFT", f"{latency_stats['avg_ttft_ms']:.0f} ms")
        with col5:
            st.metric("Avg TBT", f"{latency_stats['avg_tbt_ms']:.0f} ms")
        with col6:
            st.metric("Tokens/sec", f"{latency_stats['avg_tokens_per_sec']:.1f}")
        
        # Percentiles
        st.subheader("Latency Percentiles")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("P50", f"{latency_stats.get('p50_total_ms', 0):.0f} ms")
        with col2:
            st.metric("P95", f"{latency_stats.get('p95_total_ms', 0):.0f} ms")
        with col3:
            st.metric("P99", f"{latency_stats.get('p99_total_ms', 0):.0f} ms")
        
        # By provider
        if latency_stats.get("by_provider"):
            st.subheader("By Provider")
            prov_data = []
            for prov, stats in latency_stats["by_provider"].items():
                prov_data.append({
                    "Provider": prov,
                    "Calls": stats["count"],
                    "Avg Total (ms)": stats["avg_total_ms"],
                    "Avg TTFT (ms)": stats["avg_ttft_ms"],
                    "Tokens/sec": stats["avg_tokens_per_sec"]
                })
            st.dataframe(pd.DataFrame(prov_data), use_container_width=True, hide_index=True)
        
        # By model
        if latency_stats.get("by_model"):
            st.subheader("By Model")
            model_data = []
            for model, stats in latency_stats["by_model"].items():
                model_data.append({
                    "Model": model,
                    "Calls": stats["count"],
                    "Avg Total (ms)": stats["avg_total_ms"],
                    "Avg TTFT (ms)": stats["avg_ttft_ms"],
                    "Tokens/sec": stats["avg_tokens_per_sec"]
                })
            st.dataframe(pd.DataFrame(model_data), use_container_width=True, hide_index=True)
            
            # Visualization
            fig = px.bar(
                pd.DataFrame(model_data), x="Model", y="Avg Total (ms)",
                title="Average Latency by Model"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # History chart
        history = api_get("/latency/history", {"limit": 100})
        if history and history.get("history"):
            st.subheader("Latency Timeline")
            df = pd.DataFrame(history["history"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
            fig = px.scatter(
                df, x="timestamp", y="total_ms", color="model",
                size="output_tokens", hover_data=["ttft_ms", "tokens_per_second"],
                title="Latency Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)


# ============ PAGE: RAG QUERY ============

elif page == "🔍 RAG Query":
    st.header("🔍 Bank Document RAG Query")
    st.caption("Query bank policies, RBI guidelines, and product catalogs")
    
    # Query input
    query = st.text_area(
        "Enter your question",
        placeholder="e.g., What is the maximum personal loan amount? What are the RBI guidelines for loan recovery?",
        height=100
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        n_results = st.slider("Number of results", 1, 10, 5)
    with col2:
        max_context = st.slider("Max context length", 500, 5000, 3000, step=500)
    with col3:
        filter_type = st.selectbox("Filter by type", ["All", "loan_policy", "rbi_guidelines", "product_catalog"])
    
    if st.button("🔍 Search", type="primary") and query:
        with st.spinner("Searching..."):
            filter_meta = None if filter_type == "All" else {"doc_type": filter_type}
            result = api_post("/rag/query", {
                "query": query,
                "n_results": n_results,
                "max_context_length": max_context
            })
        
        if result:
            # Display context
            st.subheader("📄 Retrieved Context")
            st.text_area("Context", result.get("context", ""), height=300)
            
            # Sources
            st.subheader("📚 Sources")
            sources = result.get("sources", [])
            similarities = result.get("similarities", [])
            
            for i, (src, sim) in enumerate(zip(sources, similarities)):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{i+1}.** {src}")
                with col2:
                    # Color code similarity
                    color = "🟢" if sim > 0.7 else "🟡" if sim > 0.5 else "🔴"
                    st.write(f"{color} {sim:.0%}")
            
            # Raw results
            with st.expander("Raw Results"):
                st.json(result)


# ============ PAGE: DOCUMENT MANAGER ============

elif page == "📚 Document Manager":
    st.header("📚 Document Manager")
    st.caption("Manage documents in the RAG system")
    
    # Stats
    stats = api_get("/rag/stats")
    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Chunks", stats.get("total_chunks", 0))
        with col2:
            st.metric("Unique Sources", stats.get("unique_sources", 0))
        with col3:
            st.metric("Embedding Model", stats.get("embedding_model", "unknown"))
        
        if stats.get("doc_types"):
            st.subheader("Document Types")
            st.bar_chart(stats["doc_types"])
    
    st.divider()
    
    # Add document
    st.subheader("➕ Add Document")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        doc_content = st.text_area("Document Content", height=200, placeholder="Paste document text here...")
    with col2:
        doc_source = st.text_input("Source Name", placeholder="e.g., policy_v2.txt")
        doc_type = st.selectbox("Document Type", ["policy", "guideline", "product", "faq", "other"])
        doc_metadata = st.text_area("Metadata (JSON)", placeholder='{"category": "credit", "version": "2024"}', height=100)
    
    if st.button("Add Document") and doc_content and doc_source:
        try:
            metadata = json.loads(doc_metadata) if doc_metadata else {}
        except:
            metadata = {}
        
        result = api_post("/rag/add-document", {
            "content": doc_content,
            "source": doc_source,
            "doc_type": doc_type,
            "metadata": metadata
        })
        
        if result:
            st.success(f"Added {result.get('chunks', 0)} chunks!")
            st.rerun()
    
    st.divider()
    
    # Add directory
    st.subheader("📁 Add Directory")
    dir_path = st.text_input("Directory Path", placeholder="/path/to/documents")
    dir_type = st.selectbox("Type for all files", ["policy", "guideline", "product", "faq", "other"], key="dir_type")
    
    if st.button("Add Directory") and dir_path:
        with st.spinner("Processing directory..."):
            result = api_post("/rag/add-directory", {"directory": dir_path, "doc_type": dir_type})
        
        if result:
            st.success("Directory processed!")
            st.json(result.get("results", {}))
    
    st.divider()
    
    # Reinitialize with templates
    st.subheader("🔄 Reinitialize with Templates")
    if st.button("Load Bank Templates"):
        with st.spinner("Loading templates..."):
            result = api_post("/rag/reinitialize")
        if result:
            st.success("Templates loaded!")
            st.json(result.get("stats", {}))


# ============ PAGE: SETTINGS ============

elif page == "⚙️ Settings":
    st.header("⚙️ Settings")
    
    # Model configuration
    st.subheader("🤖 Model Configuration")
    
    models = api_get("/models/available")
    if models:
        st.write("**Available Models:**")
        for provider, model_list in models.items():
            with st.expander(f"{provider} ({len(model_list)} models)"):
                for m in model_list[:10]:
                    st.write(f"  • {m}")
                if len(model_list) > 10:
                    st.write(f"  ... and {len(model_list) - 10} more")
    
    st.divider()
    
    # Update config
    col1, col2 = st.columns(2)
    with col1:
        provider = st.selectbox("Provider", ["local", "groq", "gemini", "anthropic", "mock"])
        routine_model = st.text_input("Routine Model", value="llama3.2:3b")
        complex_model = st.text_input("Complex Model", value="llama3.1:8b")
    with col2:
        ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")
        vllm_routine = st.text_input("vLLM Routine URL", value="http://localhost:8001/v1")
        vllm_complex = st.text_input("vLLM Complex URL", value="http://localhost:8002/v1")
    
    if st.button("Update Model Config"):
        result = api_post("/models/config", {
            "provider": provider,
            "routine_model": routine_model,
            "complex_model": complex_model,
            "ollama_url": ollama_url,
            "vllm_routine_url": vllm_routine,
            "vllm_complex_url": vllm_complex
        })
        if result:
            st.success("Configuration updated!")
            st.json(result)
    
    st.divider()
    
    # Environment
    st.subheader("🔧 Environment Variables")
    env_vars = [
        "MODEL_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
        "OLLAMA_BASE_URL", "VLLM_ROUTINE_URL", "VLLM_COMPLEX_URL",
        "LOCAL_ROUTINE_MODEL", "LOCAL_COMPLEX_MODEL",
        "CHROMA_URL"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "")
        if "KEY" in var and value:
            display = value[:8] + "..." + value[-4:]
        else:
            display = value or "(not set)"
        st.text(f"{var} = {display}")

# ============ FOOTER ============

st.divider()
st.caption("Intelligence Layer Simulation • Built with FastAPI + Streamlit + Local LLMs")