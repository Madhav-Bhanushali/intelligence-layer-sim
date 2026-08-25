#!/bin/bash
# Remote Server Setup Script (API-only, no local models)
# Run this ON the remote server to set up everything

set -e

echo "========================================="
echo "Remote Server Setup (API + ChromaDB only)"
echo "========================================="

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies (no GPU needed)
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    docker.io docker-compose \
    curl git htop

# Add user to docker group
sudo usermod -aG docker $USER

# No GPU/NVIDIA toolkit needed - using API keys (Groq/Gemini)

# Create project directory
sudo mkdir -p /opt/intelligence-layer-sim
sudo chown $USER:$USER /opt/intelligence-layer-sim

echo "========================================="
echo "Server setup complete!"
echo "Now copy your project files to /opt/intelligence-layer-sim"
echo "Then run: cd /opt/intelligence-layer-sim && docker compose -f deployment/docker-compose.yml up -d --build"
echo "========================================="
echo ""
echo "Required .env file:"
echo "cat > .env << 'EOF'"
echo "MODEL_PROVIDER=groq"
echo "GROQ_API_KEY=your-groq-key"
echo "# Optional: GEMINI_API_KEY=your-gemini-key"
echo "EOF"