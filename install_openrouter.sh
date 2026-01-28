#!/bin/bash
# Setup OpenRouter API for VPPctl AI Agent

set -e

echo "🚀 Setting up OpenRouter API for VPPctl AI Agent"
echo "================================================"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "   Consider activating venv: source venv/bin/activate"
    echo ""
fi

# Install required packages
echo "📦 Installing required packages..."
pip install openai requests

echo ""
echo "🔑 OpenRouter API Setup"
echo "======================="
echo ""
echo "1. Visit: https://openrouter.ai/keys"
echo "2. Sign up for a free account (no credit card required)"
echo "3. Create an API key"
echo "4. Set the environment variable:"
echo ""
echo "   export OPENROUTER_API_KEY='your_api_key_here'"
echo ""
echo "   Or add to your ~/.bashrc:"
echo "   echo 'export OPENROUTER_API_KEY=\"your_key\"' >> ~/.bashrc"
echo ""

# Test API key if set
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo "🧪 Testing API connection..."
    python3 -c "
import openai
import os
client = openai.OpenAI(
    api_key=os.getenv('OPENROUTER_API_KEY'),
    base_url='https://openrouter.ai/api/v1'
)
try:
    response = client.chat.completions.create(
        model='anthropic/claude-3-haiku',
        messages=[{'role': 'user', 'content': 'Hello!'}],
        max_tokens=10
    )
    print('✅ API connection successful!')
    print('🤖 Response:', response.choices[0].message.content)
except Exception as e:
    print('❌ API test failed:', str(e))
    echo ''
    echo 'Please check your API key and try again.'
"
else
    echo "⚠️  OPENROUTER_API_KEY not set - skipping API test"
fi

echo ""
echo "🎉 Setup completed!"
echo ""
echo "Available AI models (via OpenRouter - all FREE):"
echo "  anthropic/claude-3-haiku     # Fast & capable (default)"
echo "  anthropic/claude-3-sonnet    # High quality"
echo "  openai/gpt-4o-mini           # Fast GPT-4"
echo "  openai/gpt-3.5-turbo         # Classic GPT"
echo "  google/gemini-pro           # Google's model"
echo "  meta-llama/llama-3.1-8b     # Meta's model"
echo "  mistralai/mistral-7b        # Fast open-source"
echo ""
echo "To use the VPPctl AI Agent:"
echo "  export OPENROUTER_API_KEY='your_key'"
echo "  ./run_agent.sh"
echo ""
echo "To use different models:"
echo "  ./run_agent.sh -m anthropic/claude-3-sonnet"
echo "  ./run_agent.sh -m openai/gpt-4o-mini"