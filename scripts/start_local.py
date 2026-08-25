#!/usr/bin/env python3
"""
Local Startup Script
Starts all services locally without Docker
"""
import os
import sys
import subprocess
import time
import signal
import requests
from pathlib import Path
from typing import List, Optional


class LocalServiceManager:
    """Manage local services"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.processes: List[subprocess.Popen] = []
        self.venv_python = project_root / "venv" / "bin" / "python"
        if not self.venv_python.exists():
            self.venv_python = project_root / "venv" / "Scripts" / "python.exe"
    
    def check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def start_ollama(self) -> bool:
        """Start Ollama server"""
        if self.check_ollama():
            print("✅ Ollama already running")
            return True
        
        print("🚀 Starting Ollama...")
        try:
            # Try to start ollama serve
            proc = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes.append(proc)
            
            # Wait for startup
            for _ in range(30):
                time.sleep(1)
                if self.check_ollama():
                    print("✅ Ollama started")
                    return True
            
            print("❌ Ollama failed to start")
            return False
        except FileNotFoundError:
            print("❌ Ollama not installed. Install from https://ollama.ai")
            return False
    
    def pull_models(self) -> bool:
        """Pull required models"""
        models = ["llama3.2:3b", "llama3.1:8b"]
        for model in models:
            print(f"📥 Pulling {model}...")
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"❌ Failed to pull {model}: {result.stderr}")
                return False
            print(f"✅ Pulled {model}")
        return True
    
    def check_chromadb(self) -> bool:
        """Check if ChromaDB is running"""
        try:
            resp = requests.get("http://localhost:8003/api/v1/heartbeat", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def start_chromadb(self) -> bool:
        """Start ChromaDB"""
        if self.check_chromadb():
            print("✅ ChromaDB already running")
            return True
        
        print("🚀 Starting ChromaDB...")
        try:
            proc = subprocess.Popen(
                ["chroma", "run", "--host", "0.0.0.0", "--port", "8003"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes.append(proc)
            
            for _ in range(15):
                time.sleep(1)
                if self.check_chromadb():
                    print("✅ ChromaDB started")
                    return True
            
            print("❌ ChromaDB failed to start")
            return False
        except FileNotFoundError:
            print("❌ ChromaDB not installed. Run: pip install chromadb")
            return False
    
    def start_api(self) -> bool:
        """Start FastAPI backend"""
        print("🚀 Starting API...")
        api_dir = self.project_root / "api"
        proc = subprocess.Popen(
            [str(self.venv_python), "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"],
            cwd=api_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.processes.append(proc)
        
        for _ in range(15):
            time.sleep(1)
            try:
                resp = requests.get("http://localhost:8080/health", timeout=2)
                if resp.status_code == 200:
                    print("✅ API started")
                    return True
            except:
                pass
        
        print("❌ API failed to start")
        return False
    
    def start_frontend(self) -> bool:
        """Start Streamlit frontend"""
        print("🚀 Starting Frontend...")
        frontend_dir = self.project_root / "frontend"
        proc = subprocess.Popen(
            [str(self.venv_python), "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"],
            cwd=frontend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.processes.append(proc)
        
        time.sleep(5)
        print("✅ Frontend started (check http://localhost:8501)")
        return True
    
    def initialize_rag(self) -> bool:
        """Initialize RAG system with bank documents"""
        print("📚 Initializing RAG...")
        try:
            result = subprocess.run(
                [str(self.venv_python), "-c", "from rag.bank_rag import initialize_bank_rag; initialize_bank_rag(); print('RAG initialized')"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ RAG initialized")
                return True
            else:
                print(f"❌ RAG init failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ RAG init error: {e}")
            return False
    
    def run(self, skip_ollama=False, skip_chroma=False, skip_frontend=False):
        """Run all services"""
        print("🚀 Starting Intelligence Layer Simulation locally...")
        print("=" * 50)
        
        # Check Python
        if not self.venv_python.exists():
            print("❌ Virtual environment not found. Run: python -m venv venv && venv/bin/pip install -r requirements.txt")
            return False
        
        success = True
        
        if not skip_ollama:
            success &= self.start_ollama()
            if success:
                success &= self.pull_models()
        
        if not skip_chroma:
            success &= self.start_chromadb()
        
        if success:
            success &= self.initialize_rag()
        
        if success:
            success &= self.start_api()
        
        if success and not skip_frontend:
            success &= self.start_frontend()
        
        if success:
            print("\n" + "=" * 50)
            print("🎉 All services started!")
            print("=" * 50)
            print("📍 Services:")
            print("  • API:         http://localhost:8080")
            print("  • Frontend:    http://localhost:8501")
            print("  • Ollama:      http://localhost:11434")
            print("  • ChromaDB:    http://localhost:8003")
            print("\nPress Ctrl+C to stop all services")
            
            # Keep running
            def signal_handler(sig, frame):
                print("\n🛑 Stopping services...")
                self.stop()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            while True:
                time.sleep(1)
        else:
            print("\n❌ Some services failed to start")
            self.stop()
            return False
    
    def stop(self):
        """Stop all processes"""
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                except:
                    pass
        print("✅ All services stopped")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Start all services locally")
    parser.add_argument("--skip-ollama", action="store_true", help="Skip Ollama")
    parser.add_argument("--skip-chroma", action="store_true", help="Skip ChromaDB")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip Frontend")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    manager = LocalServiceManager(Path(args.project_root).resolve())
    manager.run(
        skip_ollama=args.skip_ollama,
        skip_chroma=args.skip_chroma,
        skip_frontend=args.skip_frontend
    )


if __name__ == "__main__":
    main()