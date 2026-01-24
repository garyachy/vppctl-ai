#!/bin/bash
# Install Ollama for AI capabilities

set -e

echo "Installing Ollama for VPPctl AI Agent..."

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Wait for installation to complete
sleep 2

# Pull recommended models for networking/VPP tasks
echo "Downloading AI models (this may take a while)..."

# Mistral - fast and capable (default)
echo "Pulling mistral model (fast, recommended)..."
ollama pull mistral

# Llama3.2:3b - excellent quality alternative
echo "Pulling llama3.2:3b model (high quality)..."
ollama pull llama3.2:3b

# Phi3 - good alternative
echo "Pulling phi3 model (fast alternative)..."
ollama pull phi3

echo "Starting Ollama service..."
# Start Ollama service in background
ollama serve &

# Wait a moment for service to start
sleep 3

echo "Ollama installation completed!"
echo ""
echo "Available models:"
ollama list
echo ""
echo "🚀 Fast Model (mistral) is now the default!"
echo ""
echo "To use the VPPctl AI Agent:"
echo "  ./run_agent.sh  (uses mistral - fast!)"
echo ""
echo "To use other models:"
echo "  ./run_agent.sh -m llama3.2:3b # High quality"
echo "  ./run_agent.sh -m phi3        # Fast alternative"
echo "  ./run_agent.sh -m llama2      # Original model"