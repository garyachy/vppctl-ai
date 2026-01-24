#!/usr/bin/env python3
"""
Test script to verify launcher script functionality
"""

import subprocess
import sys
import os

def test_launcher():
    """Test the launcher script functionality"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_path = os.path.join(script_dir, 'run_agent.sh')

    print("Testing VPPctl AI Agent Launcher Script")
    print("=" * 50)

    # Test 1: Help command
    print("\n1. Testing help command...")
    try:
        result = subprocess.run([launcher_path, '--help'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'VPPctl AI Agent' in result.stdout:
            print("✅ Help command works!")
        else:
            print("❌ Help command failed")
    except Exception as e:
        print(f"❌ Help command error: {e}")

    # Test 2: Check if venv activation works
    print("\n2. Testing virtual environment activation...")
    try:
        # Run a Python command that imports ollama
        cmd = [launcher_path, '-c', 'import ollama; print("Ollama available")']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if 'Ollama available' in result.stdout:
            print("✅ Virtual environment and ollama import works!")
        elif 'Warning: ollama package not found' in result.stderr:
            print("⚠️  Ollama package not installed in venv")
        else:
            print(f"❌ Virtual environment issue: {result.stderr}")
    except Exception as e:
        print(f"❌ Virtual environment error: {e}")

    # Test 3: Check basic execution
    print("\n3. Testing basic execution...")
    try:
        # Test that the script can start and show the prompt
        env = os.environ.copy()
        env['PYTHONPATH'] = script_dir

        # Use timeout and echo quit to test startup
        cmd = f'echo "quit" | timeout 5 {launcher_path} 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=10, env=env)

        if 'VPPctl AI Agent - Interactive Mode' in result.stdout:
            print("✅ Agent starts successfully!")
        elif 'Could not connect to VPP' in result.stdout:
            print("✅ Agent starts (VPP not running)")
        else:
            print(f"Execution test result: stdout[:100]={result.stdout[:100]} stderr[:100]={result.stderr[:100]}")
    except subprocess.TimeoutExpired:
        print("⏱️  Execution test timed out")
    except Exception as e:
        print(f"❌ Execution test error: {e}")

    print("\n" + "=" * 50)
    print("Launcher script test completed!")
    print("\nTo run the agent interactively:")
    print("  ./run_agent.sh")
    print("  ./run_agent.sh -s /run/vpp/cli.sock")
    print("  ./run_agent.sh -m mistral -v")

if __name__ == "__main__":
    test_launcher()