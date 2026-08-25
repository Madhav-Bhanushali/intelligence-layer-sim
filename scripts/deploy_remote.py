#!/usr/bin/env python3
"""
SSH Deployment Script for Remote GPU
Deploys the intelligence layer simulation to a remote GPU server
"""
import os
import sys
import argparse
import paramiko
import subprocess
import time
from pathlib import Path
from typing import Optional, List
import json


class RemoteDeployer:
    """Deploy to remote GPU server via SSH"""
    
    def __init__(
        self,
        host: str,
        user: str = "ubuntu",
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 22,
        remote_dir: str = "/opt/intelligence-layer-sim"
    ):
        self.host = host
        self.user = user
        self.key_path = key_path
        self.password = password
        self.port = port
        self.remote_dir = remote_dir
        self.ssh: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
    
    def connect(self) -> bool:
        """Establish SSH connection"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_path:
                key = paramiko.RSAKey.from_private_key_file(self.key_path)
                self.ssh.connect(
                    self.host, port=self.port, username=self.user,
                    pkey=key, timeout=30
                )
            elif self.password:
                self.ssh.connect(
                    self.host, port=self.port, username=self.user,
                    password=self.password, timeout=30
                )
            else:
                # Try default SSH keys
                self.ssh.connect(
                    self.host, port=self.port, username=self.user,
                    timeout=30
                )
            
            self.sftp = self.ssh.open_sftp()
            print(f"✅ Connected to {self.user}@{self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"❌ SSH connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close SSH connection"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
    
    def run_command(self, cmd: str, timeout: int = 300) -> tuple:
        """Run command on remote server"""
        if not self.ssh:
            raise RuntimeError("Not connected")
        
        stdin, stdout, stderr = self.ssh.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        error = stderr.read().decode()
        return exit_code, output, error
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file via SFTP"""
        if not self.sftp:
            raise RuntimeError("SFTP not connected")
        
        try:
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            self._mkdir_p(remote_dir)
            
            self.sftp.put(local_path, remote_path)
            return True
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False
    
    def upload_directory(self, local_dir: str, remote_dir: str, exclude: List[str] = None) -> bool:
        """Upload directory recursively"""
        exclude = exclude or ['.git', '__pycache__', '*.pyc', '.env', 'venv', 'node_modules']
        
        import fnmatch
        
        for root, dirs, files in os.walk(local_dir):
            # Filter excluded directories
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pat) for pat in exclude)]
            
            for file in files:
                if any(fnmatch.fnmatch(file, pat) for pat in exclude):
                    continue
                
                local_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_path, local_dir)
                remote_path = os.path.join(remote_dir, rel_path).replace("\\", "/")
                
                if not self.upload_file(local_path, remote_path):
                    return False
        
        return True
    
    def _mkdir_p(self, path: str):
        """Create directory recursively on remote"""
        try:
            self.sftp.stat(path)
        except IOError:
            parent = os.path.dirname(path)
            if parent:
                self._mkdir_p(parent)
            self.sftp.mkdir(path)
    
    def check_gpu(self) -> Dict:
        """Check GPU availability on remote"""
        exit_code, output, error = self.run_command("nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits")
        if exit_code != 0:
            return {"available": False, "error": error}
        
        gpus = []
        for line in output.strip().split("\n"):
            if line:
                parts = line.split(", ")
                gpus.append({
                    "name": parts[0],
                    "memory_total_mb": int(parts[1]),
                    "memory_free_mb": int(parts[2]),
                })
        
        return {"available": True, "gpus": gpus}
    
    def install_docker(self) -> bool:
        """Install Docker and NVIDIA Container Toolkit"""
        print("📦 Installing Docker...")
        
        commands = [
            "apt-get update",
            "apt-get install -y ca-certificates curl gnupg lsb-release",
            "install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null',
            "apt-get update",
            "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            "systemctl enable docker",
            "systemctl start docker",
        ]
        
        for cmd in commands:
            print(f"  Running: {cmd}")
            exit_code, out, err = self.run_command(cmd, timeout=300)
            if exit_code != 0:
                print(f"❌ Failed: {err}")
                return False
        
        print("✅ Docker installed")
        return True
    
    def install_nvidia_toolkit(self) -> bool:
        """Install NVIDIA Container Toolkit"""
        print("📦 Installing NVIDIA Container Toolkit...")
        
        commands = [
            "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
            'curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list',
            "apt-get update",
            "apt-get install -y nvidia-container-toolkit",
            "nvidia-ctk runtime configure --runtime=docker",
            "systemctl restart docker",
        ]
        
        for cmd in commands:
            print(f"  Running: {cmd}")
            exit_code, out, err = self.run_command(cmd, timeout=300)
            if exit_code != 0:
                print(f"❌ Failed: {err}")
                return False
        
        print("✅ NVIDIA Container Toolkit installed")
        return True
    
    def deploy_project(self, local_project_dir: str) -> bool:
        """Deploy project files to remote"""
        print(f"📤 Uploading project to {self.remote_dir}...")
        
        exclude = ['.git', '__pycache__', '*.pyc', '.env', 'venv', 'node_modules', '.pytest_cache', '*.log', 'traces', '*.csv']
        
        if not self.upload_directory(local_project_dir, self.remote_dir, exclude):
            return False
        
        print("✅ Project uploaded")
        return True
    
    def build_and_start(self, gpu_count: int = 1) -> bool:
        """Build and start Docker containers"""
        print("🔨 Building and starting containers...")
        
        # Modify docker-compose for GPU count
        compose_path = f"{self.remote_dir}/deployment/docker-compose.yml"
        
        # Check if we need to modify GPU assignment
        exit_code, compose_content, _ = self.run_command(f"cat {compose_path}")
        if exit_code != 0:
            print("❌ Failed to read docker-compose")
            return False
        
        # Start services
        cmd = f"cd {self.remote_dir}/deployment && docker compose up -d --build"
        print(f"  Running: {cmd}")
        exit_code, out, err = self.run_command(cmd, timeout=600)
        
        if exit_code != 0:
            print(f"❌ Build failed: {err}")
            return False
        
        print("✅ Containers started")
        return True
    
    def verify_deployment(self) -> bool:
        """Verify deployment is working"""
        print("🔍 Verifying deployment...")
        
        # Check container status
        exit_code, out, err = self.run_command(f"cd {self.remote_dir}/deployment && docker compose ps")
        print(out)
        
        # Check API health
        time.sleep(10)
        exit_code, out, err = self.run_command("curl -s http://localhost:8080/health")
        if exit_code == 0:
            try:
                health = json.loads(out)
                if health.get("status") == "healthy":
                    print("✅ API is healthy")
                    return True
            except:
                pass
        
        print("⚠️ API not responding yet, may need more time")
        return False
    
    def pull_models(self) -> bool:
        """Pull required models on remote"""
        print("📥 Pulling models...")
        
        # Pull Ollama models
        models = ["llama3.2:3b", "llama3.1:8b"]
        for model in models:
            print(f"  Pulling {model}...")
            exit_code, out, err = self.run_command(
                f"docker exec ollama-server ollama pull {model}",
                timeout=600
            )
            if exit_code != 0:
                print(f"  ⚠️ Warning: {err}")
        
        print("✅ Models pulled")
        return True


def create_ssh_config(
    host: str,
    user: str,
    key_path: str = None,
    alias: str = None
) -> str:
    """Generate SSH config entry"""
    alias = alias or host
    config = f"""Host {alias}
    HostName {host}
    User {user}
    Port 22
"""
    if key_path:
        config += f"    IdentityFile {key_path}\n"
    config += "    ForwardAgent yes\n"
    config += "    ServerAliveInterval 60\n"
    config += "    ServerAliveCountMax 3\n"
    return config


def main():
    parser = argparse.ArgumentParser(description="Deploy Intelligence Layer Simulation to remote GPU")
    parser.add_argument("host", help="Remote server hostname or IP")
    parser.add_argument("--user", default="ubuntu", help="SSH username")
    parser.add_argument("--key", help="Path to SSH private key")
    parser.add_argument("--password", help="SSH password (not recommended)")
    parser.add_argument("--port", type=int, default=22, help="SSH port")
    parser.add_argument("--remote-dir", default="/opt/intelligence-layer-sim", help="Remote deployment directory")
    parser.add_argument("--local-dir", default=".", help="Local project directory")
    parser.add_argument("--gpu-count", type=int, default=1, help="Number of GPUs to use")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker installation")
    parser.add_argument("--skip-nvidia", action="store_true", help="Skip NVIDIA toolkit installation")
    parser.add_argument("--ssh-config-only", action="store_true", help="Only generate SSH config")
    parser.add_argument("--check-gpu", action="store_true", help="Only check GPU availability")
    
    args = parser.parse_args()
    
    if args.ssh_config_only:
        config = create_ssh_config(args.host, args.user, args.key, args.host)
        print(config)
        return
    
    deployer = RemoteDeployer(
        host=args.host,
        user=args.user,
        key_path=args.key,
        password=args.password,
        port=args.port,
        remote_dir=args.remote_dir
    )
    
    if not deployer.connect():
        sys.exit(1)
    
    try:
        if args.check_gpu:
            gpu_info = deployer.check_gpu()
            print(json.dumps(gpu_info, indent=2))
            return
        
        # Check GPU
        print("🔍 Checking GPU availability...")
        gpu_info = deployer.check_gpu()
        if gpu_info.get("available"):
            print(f"✅ GPUs found: {len(gpu_info['gpus'])}")
            for gpu in gpu_info['gpus']:
                print(f"  • {gpu['name']}: {gpu['memory_free_mb']}MB free / {gpu['memory_total_mb']}MB total")
        else:
            print(f"❌ No GPU available: {gpu_info.get('error')}")
            sys.exit(1)
        
        # Install Docker
        if not args.skip_docker:
            if not deployer.install_docker():
                sys.exit(1)
        
        # Install NVIDIA toolkit
        if not args.skip_nvidia:
            if not deployer.install_nvidia_toolkit():
                sys.exit(1)
        
        # Deploy project
        if not deployer.deploy_project(args.local_dir):
            sys.exit(1)
        
        # Build and start
        if not deployer.build_and_start(args.gpu_count):
            sys.exit(1)
        
        # Pull models
        if not deployer.pull_models():
            sys.exit(1)
        
        # Verify
        if not deployer.verify_deployment():
            print("⚠️ Deployment may need more time. Check manually:")
            print(f"  ssh {args.user}@{args.host} 'cd {args.remote_dir}/deployment && docker compose logs -f'")
        
        print("\n🎉 Deployment complete!")
        print(f"API: http://{args.host}:8080")
        print(f"Frontend: http://{args.host}:8501")
        print(f"Ollama: http://{args.host}:11434")
        print(f"vLLM Routine: http://{args.host}:8001")
        print(f"vLLM Complex: http://{args.host}:8002")
        print(f"ChromaDB: http://{args.host}:8003")
        
    finally:
        deployer.disconnect()


if __name__ == "__main__":
    main()