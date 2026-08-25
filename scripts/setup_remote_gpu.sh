#!/bin/bash
# Remote GPU Server Setup Script
# Run this ON the remote GPU server to set up everything

set -e

echo "========================================="
echo "Remote GPU Server Setup"
echo "========================================="

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    docker.io docker-compose \
    nvidia-docker2 \
    curl git htop nvtop

# Add user to docker group
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.4-base nvidia-smi

# Create project directory
sudo mkdir -p /opt/intelligence-layer-sim
sudo chown $USER:$USER /opt/intelligence-layer-sim

echo "========================================="
echo "Server setup complete!"
echo "Now copy your project files to /opt/intelligence-layer-sim"
echo "Then run: cd /opt/intelligence-layer-sim && docker compose -f deployment/docker-compose.yml up -d --build"
echo "========================================="