#!/bin/bash
# VPPctl AI Agent Launcher Script
# This script activates the virtual environment and runs the agent with provided arguments

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Error: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install ollama"
    exit 1
fi

# Check if virtual environment is activated, if not, activate it
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Check if ollama is installed
if ! python3 -c "import ollama" 2>/dev/null; then
    echo "Warning: ollama package not found in virtual environment"
    echo "Installing ollama..."
    pip install ollama
fi

# Check if Ollama service is running
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "Warning: Ollama service not running"
    echo "Starting Ollama service in background..."
    export PATH="$PATH:/home/denys/bin"
    if [ -x "/home/denys/bin/ollama" ]; then
        /home/denys/bin/ollama serve &
        sleep 2  # Give it time to start
    else
        echo "Ollama binary not found at /home/denys/bin/ollama"
        echo "Please install Ollama first: curl -fsSL https://ollama.ai/install.sh | sh"
    fi
fi

# Ensure fast model (mistral) is available
export PATH="$PATH:/home/denys/bin"
if [ -x "/home/denys/bin/ollama" ]; then
    if ! ollama list | grep -q "mistral"; then
        echo "Fast model (mistral) not found. Installing..."
        ollama pull mistral
    fi
fi

# Default arguments if none provided
if [ $# -eq 0 ]; then
    echo "No arguments provided, using defaults..."
    set -- "-s" "/run/vpp/cli.sock"
fi

# Run the agent with all provided arguments
echo "Starting VPPctl AI Agent..."
echo "Command: python3 $SCRIPT_DIR/main.py $@"
echo "----------------------------------------"

exec python3 "$SCRIPT_DIR/main.py" "$@"