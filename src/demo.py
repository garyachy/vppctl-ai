#!/usr/bin/env python3
"""
VPPctl AI Agent Demo Script
Shows all the key features working
"""

from .main import VPPctlAgent

def demo():
    """Run a comprehensive demo of the VPPctl AI Agent"""
    print("🚀 VPPctl AI Agent - Full Feature Demo")
    print("=" * 50)

    # Initialize agent
    print("🤖 Initializing AI Agent...")
    agent = VPPctlAgent()
    print(f"✅ AI Available: {agent.ai_available}")
    print()

    # Demo 1: Basic AI Questions
    print("1️⃣ Testing Natural Language Questions")
    questions = [
        "What is VPP?",
        "How do I configure an IPsec tunnel?",
        "What are VPP interface types?"
    ]

    for question in questions:
        print(f"❓ {question}")
        print("🤖 Thinking...")
        response = agent.get_ai_assistance(question)
        print(f"✅ Response: {response[:150]}..." if len(response) > 150 else f"✅ Response: {response}")
        print("-" * 30)

    # Demo 2: Analyze Feature
    print("2️⃣ Testing Issue Analysis")
    print("❓ Analyzing: packet loss between interfaces")
    print("🤖 Analyzing current VPP state...")
    analysis = agent.analyze_issue("packet loss between interfaces")
    print(f"✅ Analysis: {analysis[:200]}..." if len(analysis) > 200 else f"✅ Analysis: {analysis}")
    print("-" * 30)

    # Demo 3: Configure Feature
    print("3️⃣ Testing Configuration Suggestions")
    print("❓ Configuring: ipsec tunnel between sites")
    print("🤖 Generating configuration...")
    config = agent.suggest_configuration("ipsec tunnel between two sites")
    print(f"✅ Configuration: {config[:200]}..." if len(config) > 200 else f"✅ Configuration: {config}")
    print("-" * 30)

    # Demo 4: VPP Commands (will show connection error)
    print("4️⃣ Testing VPP Commands")
    print("❓ Running: show version")
    stdout, stderr = agent.execute_vppctl("show version", timeout=3)
    if stderr:
        print(f"ℹ️ Expected (VPP not running): {stderr.strip()}")
    else:
        print(f"✅ VPP Response: {stdout.strip()}")
    print("-" * 30)

    print("🎉 Demo Complete!")
    print()
    print("To use interactively:")
    print("  ./run_agent.sh")
    print("  Type questions like:")
    print("  - What is VPP?")
    print("  - analyze network issue")
    print("  - configure ipsec")
    print("  - show interfaces (if VPP running)")

if __name__ == "__main__":
    demo()