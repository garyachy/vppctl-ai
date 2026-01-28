#!/usr/bin/env python3
"""
Test AI response speed with OpenRouter
"""

import time
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.main import VPPctlAgent

def test_ai_speed():
    """Test AI response speed"""
    print("🚀 Testing OpenRouter AI Response Speed")
    print("=" * 50)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set!")
        print("Get your free key from: https://openrouter.ai/keys")
        print("Then run: export OPENROUTER_API_KEY='your_key'")
        return

    print("✅ API key found")

    # Initialize agent
    print("🤖 Initializing agent...")
    agent = VPPctlAgent()

    if not agent.ai_available:
        print("❌ AI not available")
        return

    print("✅ AI client ready")
    print()

    # Test different queries
    test_queries = [
        "What is VPP?",
        "How do I configure IPsec?",
        "Show me interface commands"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"Test {i}: \"{query}\"")
        print("🤖 Thinking...")

        start_time = time.time()
        response = agent.get_ai_assistance(query)
        end_time = time.time()

        response_time = end_time - start_time

        if "failed" in response.lower():
            print(f"❌ Failed in {response_time:.2f}s: {response}")
        else:
            print(f"✅ Response in {response_time:.2f}s: {len(response)} characters")
            print(f"Preview: {response[:80]}...")
            print()

        # Check if within target time
        if response_time <= 2.0:
            print("✅ TARGET MET: Response within 2 seconds!")
        elif response_time <= 5.0:
            print("⚠️  Acceptable: Response within 5 seconds")
        else:
            print("🐌 Slow: Response took too long")

        print("-" * 50)

    # Summary
    print("🎯 Speed Test Summary:")
    print("- Target: 1-2 seconds per response")
    print("- OpenRouter typically delivers 0.5-3 seconds")
    print("- If slower, try different models:")
    print("  ./run_agent.sh -m openai/gpt-4o-mini")
    print("  ./run_agent.sh -m anthropic/claude-3-haiku")

if __name__ == "__main__":
    test_ai_speed()