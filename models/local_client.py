"""
Local Model Client with Latency Tracking
Supports Ollama and vLLM (OpenAI-compatible) endpoints
"""
import os
import time
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime
import httpx
from openai import AsyncOpenAI


@dataclass
class LatencyMetrics:
    """Latency metrics for a model call"""
    total_ms: float
    ttft_ms: float  # Time to first token
    tbt_ms: float   # Time between tokens (avg)
    input_tokens: int
    output_tokens: int
    tokens_per_second: float
    model: str
    provider: str
    timestamp: str
    success: bool
    error: Optional[str] = None


class LocalModelClient:
    """Client for local model serving (Ollama / vLLM) with latency tracking"""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        vllm_routine_url: str = "http://localhost:8001/v1",
        vllm_complex_url: str = "http://localhost:8002/v1",
        default_routine_model: str = "llama3.2:3b",
        default_complex_model: str = "llama3.1:8b",
        timeout: float = 120.0
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.vllm_routine_url = vllm_routine_url.rstrip("/")
        self.vllm_complex_url = vllm_complex_url.rstrip("/")
        self.default_routine_model = default_routine_model
        self.default_complex_model = default_complex_model
        self.timeout = timeout
        
        self._vllm_routine_client: Optional[AsyncOpenAI] = None
        self._vllm_complex_client: Optional[AsyncOpenAI] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        
        self.latency_history: List[LatencyMetrics] = []
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client
    
    async def _get_vllm_client(self, complex: bool = False) -> AsyncOpenAI:
        if complex:
            if self._vllm_complex_client is None:
                self._vllm_complex_client = AsyncOpenAI(
                    base_url=self.vllm_complex_url,
                    api_key="not-needed"
                )
            return self._vllm_complex_client
        else:
            if self._vllm_routine_client is None:
                self._vllm_routine_client = AsyncOpenAI(
                    base_url=self.vllm_routine_url,
                    api_key="not-needed"
                )
            return self._vllm_routine_client
    
    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
        if self._vllm_routine_client:
            await self._vllm_routine_client.close()
        if self._vllm_complex_client:
            await self._vllm_complex_client.close()
    
    # ============ OLLAMA METHODS ============
    
    async def call_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Call Ollama API with latency tracking"""
        client = await self._get_http_client()
        start_time = time.perf_counter()
        first_token_time = None
        token_times = []
        
        url = f"{self.ollama_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            if stream:
                output = ""
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                output += chunk
                                if first_token_time is None:
                                    first_token_time = time.perf_counter()
                                token_times.append(time.perf_counter())
                                
                                if data.get("done", False):
                                    break
            else:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                output = data.get("message", {}).get("content", "")
                first_token_time = time.perf_counter()
        
        except Exception as e:
            total_ms = (time.perf_counter() - start_time) * 1000
            return self._error_result(model, "ollama", str(e), total_ms)
        
        total_ms = (time.perf_counter() - start_time) * 1000
        
        return self._success_result(
            model=model,
            provider="ollama",
            output=output,
            total_ms=total_ms,
            first_token_time=first_token_time,
            token_times=token_times,
            start_time=start_time
        )
    
    # ============ VLLM METHODS ============
    
    async def call_vllm(
        self,
        messages: List[Dict[str, str]],
        model: str,
        complex: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Call vLLM (OpenAI-compatible) API with latency tracking"""
        client = await self._get_vllm_client(complex=complex)
        start_time = time.perf_counter()
        first_token_time = None
        token_times = []
        output = ""
        
        try:
            if stream:
                stream_response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                async for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token_text = chunk.choices[0].delta.content
                        output += token_text
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        token_times.append(time.perf_counter())
            else:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                output = response.choices[0].message.content or ""
                first_token_time = time.perf_counter()
                if hasattr(response, 'usage') and response.usage:
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                else:
                    input_tokens = len(" ".join(m["content"] for m in messages).split())
                    output_tokens = len(output.split())
        
        except Exception as e:
            total_ms = (time.perf_counter() - start_time) * 1000
            return self._error_result(model, "vllm", str(e), total_ms)
        
        total_ms = (time.perf_counter() - start_time) * 1000
        
        return self._success_result(
            model=model,
            provider="vllm",
            output=output,
            total_ms=total_ms,
            first_token_time=first_token_time,
            token_times=token_times,
            start_time=start_time,
            input_tokens=getattr(response, 'usage', None) and response.usage.prompt_tokens,
            output_tokens=getattr(response, 'usage', None) and response.usage.completion_tokens
        )
    
    # ============ UNIFIED INTERFACE ============
    
    async def call_model(
        self,
        messages: List[Dict[str, str]],
        classification: str,  # "routine" or "complex"
        provider: str = "auto",  # "auto", "ollama", "vllm"
        temperature: float = 0.3,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Unified interface for calling models based on classification"""
        
        # Determine provider
        if provider == "auto":
            provider = "vllm"  # Prefer vLLM for performance
        
        # Select model based on classification
        if classification == "routine":
            model = self.default_routine_model
        else:
            model = self.default_complex_model
        
        if provider == "ollama":
            return await self.call_ollama(messages, model, temperature, max_tokens, stream)
        elif provider == "vllm":
            return await self.call_vllm(messages, model, complex=(classification=="complex"), 
                                        temperature=temperature, max_tokens=max_tokens, stream=stream)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    # ============ LATENCY CALCULATION ============
    
    def _success_result(
        self,
        model: str,
        provider: str,
        output: str,
        total_ms: float,
        first_token_time: Optional[float],
        token_times: List[float],
        start_time: float,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calculate latency metrics from timing data"""
        
        ttft_ms = 0.0
        if first_token_time:
            ttft_ms = (first_token_time - start_time) * 1000
        
        tbt_ms = 0.0
        if len(token_times) > 1:
            intervals = [token_times[i] - token_times[i-1] for i in range(1, len(token_times))]
            tbt_ms = (sum(intervals) / len(intervals)) * 1000
        
        tokens_per_sec = 0.0
        if total_ms > 0 and output_tokens:
            tokens_per_sec = (output_tokens / total_ms) * 1000
        
        # Estimate tokens if not provided
        if input_tokens is None:
            input_tokens = len(" ".join(m["content"] for m in messages).split()) * 1.3  # rough estimate
        if output_tokens is None:
            output_tokens = len(output.split()) * 1.3
        
        metrics = LatencyMetrics(
            total_ms=round(total_ms, 2),
            ttft_ms=round(ttft_ms, 2),
            tbt_ms=round(tbt_ms, 2),
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            tokens_per_second=round(tokens_per_sec, 2),
            model=model,
            provider=provider,
            timestamp=datetime.utcnow().isoformat(),
            success=True
        )
        
        self.latency_history.append(metrics)
        
        return {
            "success": True,
            "output": output,
            "model": model,
            "provider": provider,
            "latency": asdict(metrics)
        }
    
    def _error_result(
        self,
        model: str,
        provider: str,
        error: str,
        total_ms: float
    ) -> Dict[str, Any]:
        metrics = LatencyMetrics(
            total_ms=round(total_ms, 2),
            ttft_ms=0.0,
            tbt_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            tokens_per_second=0.0,
            model=model,
            provider=provider,
            timestamp=datetime.utcnow().isoformat(),
            success=False,
            error=error
        )
        self.latency_history.append(metrics)
        
        return {
            "success": False,
            "output": "",
            "model": model,
            "provider": provider,
            "error": error,
            "latency": asdict(metrics)
        }
    
    # ============ LATENCY REPORTING ============
    
    def get_latency_stats(self) -> Dict[str, Any]:
        """Get aggregate latency statistics"""
        if not self.latency_history:
            return {"error": "No latency data available"}
        
        successful = [m for m in self.latency_history if m.success]
        if not successful:
            return {"error": "No successful calls"}
        
        return {
            "total_calls": len(self.latency_history),
            "successful_calls": len(successful),
            "success_rate": round(len(successful) / len(self.latency_history) * 100, 2),
            "avg_total_ms": round(sum(m.total_ms for m in successful) / len(successful), 2),
            "avg_ttft_ms": round(sum(m.ttft_ms for m in successful) / len(successful), 2),
            "avg_tbt_ms": round(sum(m.tbt_ms for m in successful) / len(successful), 2),
            "avg_tokens_per_sec": round(sum(m.tokens_per_second for m in successful) / len(successful), 2),
            "p50_total_ms": self._percentile([m.total_ms for m in successful], 50),
            "p95_total_ms": self._percentile([m.total_ms for m in successful], 95),
            "p99_total_ms": self._percentile([m.total_ms for m in successful], 99),
            "by_provider": self._group_by_provider(successful),
            "by_model": self._group_by_model(successful),
        }
    
    def _percentile(self, values: List[float], p: int) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * p / 100)
        return round(sorted_vals[min(idx, len(sorted_vals)-1)], 2)
    
    def _group_by_provider(self, metrics: List[LatencyMetrics]) -> Dict[str, Any]:
        groups = {}
        for m in metrics:
            if m.provider not in groups:
                groups[m.provider] = []
            groups[m.provider].append(m)
        
        return {
            provider: {
                "count": len(vals),
                "avg_total_ms": round(sum(v.total_ms for v in vals) / len(vals), 2),
                "avg_ttft_ms": round(sum(v.ttft_ms for v in vals) / len(vals), 2),
                "avg_tokens_per_sec": round(sum(v.tokens_per_second for v in vals) / len(vals), 2),
            }
            for provider, vals in groups.items()
        }
    
    def _group_by_model(self, metrics: List[LatencyMetrics]) -> Dict[str, Any]:
        groups = {}
        for m in metrics:
            if m.model not in groups:
                groups[m.model] = []
            groups[m.model].append(m)
        
        return {
            model: {
                "count": len(vals),
                "avg_total_ms": round(sum(v.total_ms for v in vals) / len(vals), 2),
                "avg_ttft_ms": round(sum(v.ttft_ms for v in vals) / len(vals), 2),
                "avg_tokens_per_sec": round(sum(v.tokens_per_second for v in vals) / len(vals), 2),
            }
            for model, vals in groups.items()
        }
    
    def export_latency_csv(self, filepath: str):
        """Export latency history to CSV"""
        import csv
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'model', 'provider', 'success', 'total_ms', 'ttft_ms',
                'tbt_ms', 'input_tokens', 'output_tokens', 'tokens_per_second', 'error'
            ])
            for m in self.latency_history:
                writer.writerow([
                    m.timestamp, m.model, m.provider, m.success, m.total_ms,
                    m.ttft_ms, m.tbt_ms, m.input_tokens, m.output_tokens,
                    m.tokens_per_second, m.error or ''
                ])


# ============ SYNC WRAPPER FOR BACKWARD COMPAT ============

class SyncLocalModelClient:
    """Synchronous wrapper for the async client"""
    
    def __init__(self, *args, **kwargs):
        self._async_client = LocalModelClient(*args, **kwargs)
        self._loop = None
    
    def _get_loop(self):
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def call_model(self, *args, **kwargs) -> Dict[str, Any]:
        loop = self._get_loop()
        return loop.run_until_complete(self._async_client.call_model(*args, **kwargs))
    
    def get_latency_stats(self) -> Dict[str, Any]:
        return self._async_client.get_latency_stats()
    
    def export_latency_csv(self, filepath: str):
        self._async_client.export_latency_csv(filepath)
    
    def close(self):
        loop = self._get_loop()
        loop.run_until_complete(self._async_client.close())


# ============ FACTORY FUNCTION ============

def create_local_client(
    provider: str = "auto",
    ollama_url: str = None,
    vllm_routine_url: str = None,
    vllm_complex_url: str = None,
) -> SyncLocalModelClient:
    """Create a local model client from environment or defaults"""
    
    ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    vllm_routine_url = vllm_routine_url or os.getenv("VLLM_ROUTINE_URL", "http://localhost:8001/v1")
    vllm_complex_url = vllm_complex_url or os.getenv("VLLM_COMPLEX_URL", "http://localhost:8002/v1")
    
    return SyncLocalModelClient(
        ollama_url=ollama_url,
        vllm_routine_url=vllm_routine_url,
        vllm_complex_url=vllm_complex_url,
        default_routine_model=os.getenv("LOCAL_ROUTINE_MODEL", "llama3.2:3b"),
        default_complex_model=os.getenv("LOCAL_COMPLEX_MODEL", "llama3.1:8b"),
    )