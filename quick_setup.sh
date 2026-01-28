#!/bin/bash
# Quick setup for OpenRouter API testing

echo "🚀 Quick OpenRouter Setup & Speed Test"
echo "======================================="
echo ""

# Check if API key is set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "🔑 Getting your FREE OpenRouter API key:"
    echo "1. Visit: https://openrouter.ai/keys"
    echo "2. Sign up (no credit card required)"
    echo "3. Create a new key"
    echo "4. Copy the key"
    echo ""
    read -p "Enter your OpenRouter API key: " api_key

    if [ -n "$api_key" ]; then
        export OPENROUTER_API_KEY="$api_key"
        echo "✅ API key set for this session"
        echo ""
        echo "💡 To make it permanent, add to your ~/.bashrc:"
        echo "   echo 'export OPENROUTER_API_KEY=\"$api_key\"' >> ~/.bashrc"
    else
        echo "❌ No API key entered. Exiting."
        exit 1
    fi
else
    echo "✅ OPENROUTER_API_KEY already set"
fi

echo ""
echo "🧪 Testing AI speed..."
echo ""

# Activate venv and run speed test
cd "$(dirname "$0")"
source venv/bin/activate
python3 tests/test_speed.py