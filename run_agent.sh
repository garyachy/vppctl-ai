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

# Check if openai is installed
if ! python3 -c "import openai" 2>/dev/null; then
    echo "Warning: openai package not found in virtual environment"
    echo "Installing openai..."
    pip install openai
fi

# Check for OpenRouter API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️  Warning: OPENROUTER_API_KEY environment variable not set"
    echo "   This happens when using sudo (sudo doesn't preserve user environment)"
    echo ""
    echo "   Solutions:"
    echo "   1. Run without sudo: ./run_agent.sh"
    echo "   2. Or run: sudo -E ./run_agent.sh (preserves environment)"
    echo "   3. Or add key to root's bashrc: sudo su -c 'echo export OPENROUTER_API_KEY=\"your_key\" >> ~/.bashrc'"
    echo ""
    echo "   For now, AI features will be disabled, but you can still use VPP commands."
else
    echo "✅ OpenRouter API key found"
fi

# Default arguments if none provided
if [ $# -eq 0 ]; then
    echo "No arguments provided, using defaults..."
    set -- "-s" "/run/vpp/cli.sock"
fi

# Run the agent with all provided arguments
echo "Starting VPPctl AI Agent..."
echo "Command: python3 $SCRIPT_DIR/src/main.py $@"
echo "----------------------------------------"

exec python3 "$SCRIPT_DIR/src/main.py" "$@"