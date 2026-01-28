#!/usr/bin/env python3
"""
Test VPPctl AI Agent with various questions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.main import VPPctlAgent

def test_ai_questions():
    """Test AI assistance with various VPP-related questions"""
    
    agent = VPPctlAgent()
    
    if not agent.ai_available:
        print("AI not available - Ollama not running or not installed")
        return
    
    questions = [
        "What is VPP and what does it do?",
        "How do I configure an IPsec tunnel in VPP?",
        "What are the different interface types in VPP?",
        "How do I troubleshoot packet loss in VPP?",
        "Explain the difference between LCP and native interfaces",
        "How do I set up VLAN interfaces in VPP?",
        "What are the performance tuning options for VPP?",
        "How do I configure BGP in VPP?",
    ]
    
    print("Testing VPPctl AI Agent with questions...\n")
    
    for i, question in enumerate(questions, 1):
        print(f"{i}. {question}")
        try:
            response = agent.get_ai_assistance(question)
            # Show first 200 characters to keep output manageable
            print(f"   → {response[:200]}{'...' if len(response) > 200 else ''}\n")
        except Exception as e:
            print(f"   → Error: {e}\n")

if __name__ == "__main__":
    test_ai_questions()
