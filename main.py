#!/usr/bin/env python3
"""
VPPctl AI Agent - Intelligent VPP management assistant
"""

import subprocess
import sys
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path

# AI Integration - using Ollama (free local AI models)
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: ollama package not installed. Install with: pip install ollama")

@dataclass
class VPPCommand:
    """Represents a VPP command with metadata"""
    command: str
    description: str
    category: str
    requires_confirmation: bool = False

@dataclass
class VPPState:
    """Current VPP system state"""
    interfaces: List[Dict] = None
    routes: List[Dict] = None
    ipsec_sas: List[Dict] = None
    ipsec_policies: List[Dict] = None
    errors: List[Dict] = None

    def __post_init__(self):
        if self.interfaces is None:
            self.interfaces = []
        if self.routes is None:
            self.routes = []
        if self.ipsec_sas is None:
            self.ipsec_sas = []
        if self.ipsec_policies is None:
            self.ipsec_policies = []
        if self.errors is None:
            self.errors = []

class VPPctlAgent:
    """AI-powered VPP management agent"""

    def __init__(self, socket_path: str = "/run/vpp/cli.sock", ai_model: str = "mistral"):
        self.socket_path = socket_path
        self.ai_model = ai_model
        self.state = VPPState()
        self.command_history: List[Tuple[str, str]] = []
        self.logger = logging.getLogger(__name__)

        # Initialize AI client
        if OLLAMA_AVAILABLE:
            try:
                self.ai_client = ollama.Client()
                self.ai_available = True
                # Test connection asynchronously (don't block startup)
                try:
                    models = self.ai_client.list()
                    if not models:
                        self.logger.warning("No AI models available")
                except Exception as e:
                    self.logger.warning(f"AI model check failed: {e}")
            except Exception as e:
                self.logger.warning(f"AI client initialization failed: {e}")
                self.ai_available = False
        else:
            self.ai_available = False

        # VPP command patterns and categories
        self.command_patterns = {
            'show': [
                VPPCommand("show version", "Show VPP version information", "system"),
                VPPCommand("show interfaces", "Display interface information", "interfaces"),
                VPPCommand("show interface address", "Show interface IP addresses", "interfaces"),
                VPPCommand("show ip fib", "Display IP forwarding table", "routing"),
                VPPCommand("show ipsec sa", "Show IPsec Security Associations", "ipsec"),
                VPPCommand("show ipsec spd", "Show IPsec Security Policy Database", "ipsec"),
                VPPCommand("show ipsec tunnel", "Show IPsec tunnels", "ipsec"),
                VPPCommand("show lcp", "Show Linux Control Plane state", "lcp"),
                VPPCommand("show errors", "Display error counters", "monitoring"),
                VPPCommand("show run", "Show running configuration", "configuration"),
            ],
            'configure': [
                VPPCommand("set interface state <interface> <up|down>", "Change interface state", "interfaces", True),
                VPPCommand("set interface ip address <interface> <address>", "Set interface IP address", "interfaces", True),
                VPPCommand("ip route add <prefix> via <next-hop>", "Add IP route", "routing", True),
                VPPCommand("create ipsec tunnel", "Create IPsec tunnel", "ipsec", True),
                VPPCommand("lcp lcp-sync <on|off>", "Control LCP synchronization", "lcp", True),
            ]
        }

    def execute_vppctl(self, command: str, timeout: int = 30) -> Tuple[str, str]:
        """
        Execute a vppctl command and return (stdout, stderr)

        Args:
            command: VPP command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (stdout, stderr)
        """
        try:
            cmd = ["vppctl", "-s", self.socket_path, command]
            self.logger.info(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            # Store in history
            self.command_history.append((command, result.stdout))

            return result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            self.logger.error(error_msg)
            return "", error_msg
        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            self.logger.error(error_msg)
            return "", error_msg

    def update_state(self):
        """Update internal VPP state by querying current configuration"""
        self.logger.info("Updating VPP state...")

        # Get interfaces
        stdout, _ = self.execute_vppctl("show interfaces")
        self.state.interfaces = self._parse_interfaces(stdout)

        # Get routes
        stdout, _ = self.execute_vppctl("show ip fib")
        self.state.routes = self._parse_routes(stdout)

        # Get IPsec state
        stdout, _ = self.execute_vppctl("show ipsec sa")
        self.state.ipsec_sas = self._parse_ipsec_sas(stdout)

        # Get errors
        stdout, _ = self.execute_vppctl("show errors")
        self.state.errors = self._parse_errors(stdout)

    def _parse_interfaces(self, output: str) -> List[Dict]:
        """Parse interface information from 'show interfaces' output"""
        interfaces = []
        lines = output.strip().split('\n')

        for line in lines:
            # Skip header lines and empty lines
            if (line.strip() and
                not line.startswith('Name') and
                not line.startswith('interface') and
                'Idx' not in line and
                'State' not in line and
                not line.startswith(' ')):
                parts = line.split()
                if len(parts) >= 4:  # Ensure we have enough parts
                    try:
                        interface = {
                            'name': parts[0],
                            'idx': parts[1],
                            'state': parts[2],
                            'mtu': parts[3],
                            'flags': ' '.join(parts[4:]) if len(parts) > 4 else ''
                        }
                        interfaces.append(interface)
                    except (IndexError, ValueError):
                        continue

        return interfaces

    def _parse_routes(self, output: str) -> List[Dict]:
        """Parse route information from 'show ip fib' output"""
        routes = []
        lines = output.strip().split('\n')

        for line in lines:
            if line.strip() and '/' in line and not line.startswith(' ') and not line.startswith('Prefix'):
                parts = line.split()
                if len(parts) >= 4:
                    # Format: Prefix fib-idx Type Next Hop [Interface]
                    route = {
                        'prefix': parts[0],
                        'fib_idx': parts[1] if len(parts) > 1 else '',
                        'type': parts[2] if len(parts) > 2 else '',
                        'next_hop': parts[3] if len(parts) > 3 else '',
                        'interface': parts[4] if len(parts) > 4 else ''
                    }
                    routes.append(route)

        return routes

    def _parse_ipsec_sas(self, output: str) -> List[Dict]:
        """Parse IPsec SA information"""
        sas = []
        lines = output.strip().split('\n')

        for line in lines:
            if line.strip() and not line.startswith(' ') and not line.startswith('sa-id'):
                parts = line.split()
                if len(parts) >= 3:
                    sa = {
                        'id': parts[0],
                        'protocol': parts[1],
                        'state': parts[2]
                    }
                    sas.append(sa)

        return sas

    def _parse_errors(self, output: str) -> List[Dict]:
        """Parse error information"""
        errors = []
        lines = output.strip().split('\n')

        for line in lines:
            if line.strip() and not line.startswith(' ') and not line.startswith('Count') and not line.startswith('Node'):
                parts = line.split()
                if len(parts) >= 3:
                    # Format: Count Node Reason...
                    try:
                        count = int(parts[0])
                        node = parts[1]
                        reason = ' '.join(parts[2:])
                        error = {
                            'count': count,
                            'node': node,
                            'reason': reason
                        }
                        errors.append(error)
                    except (ValueError, IndexError):
                        continue

        return errors

    def get_ai_assistance(self, user_query: str, context: Optional[str] = None) -> str:
        """
        Get AI assistance for VPP-related queries

        Args:
            user_query: User's question or request
            context: Additional context (e.g., current VPP state)

        Returns:
            AI-generated response
        """
        if not self.ai_available:
            return "AI assistance not available. Please install ollama and ensure the model is running."

        # Prepare context - minimal prompt for speed
        system_prompt = """You are an AI assistant specializing in VPP (Vector Packet Processing) networking.
VPP is a high-performance packet processing stack for network functions.
Provide helpful, accurate information about VPP."""

        # Only add context for analyze/configure commands, not general questions
        if context and (user_query.lower().startswith('analyze') or user_query.lower().startswith('configure')):
            # Truncate context if too long
            if len(context) > 500:
                context = context[:500] + "..."
            system_prompt += f"\n\nCurrent VPP context:\n{context}"

        try:
            print("🤖 Thinking... (this may take 10-20 seconds)")
            # Simplify the prompt if it's too long
            if len(system_prompt) > 2000:
                system_prompt = system_prompt[:2000] + "\n\n[Context truncated for brevity]"

            response = self.ai_client.chat(
                model=self.ai_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_query}
                ]
            )

            result = response['message']['content']
            if not result.strip():
                return "AI returned empty response. Try rephrasing your question."
            return result

        except Exception as e:
            return f"AI assistance failed: {str(e)}. Try again or check if Ollama is running."

    def analyze_issue(self, issue_description: str) -> str:
        """
        Analyze a described network issue using VPP state and AI

        Args:
            issue_description: Description of the problem

        Returns:
            Analysis and recommended actions
        """
        # Update state first
        self.update_state()

        # Prepare context from current state
        context = f"""
        Current VPP State:
        Interfaces: {len(self.state.interfaces)} configured
        Routes: {len(self.state.routes)} in FIB
        IPsec SAs: {len(self.state.ipsec_sas)} active
        Errors: {len(self.state.errors)} detected

        Recent commands: {self.command_history[-5:] if self.command_history else 'None'}
        """

        ai_query = f"""
        User reported issue: {issue_description}

        Please analyze this issue based on VPP networking knowledge and suggest:
        1. Likely causes
        2. Diagnostic commands to run
        3. Potential solutions
        4. Commands to verify the fix

        Be specific and actionable.
        """

        return self.get_ai_assistance(ai_query, context)

    def suggest_configuration(self, requirement: str) -> str:
        """
        Suggest VPP configuration for a given requirement

        Args:
            requirement: What the user wants to configure

        Returns:
            Configuration suggestions
        """
        ai_query = f"""
        The user wants to configure VPP for: {requirement}

        Please provide:
        1. Step-by-step configuration commands
        2. Explanation of each command
        3. Verification commands
        4. Any prerequisites or dependencies
        5. Potential issues to watch for

        Make sure the commands are syntactically correct for vppctl.
        """

        return self.get_ai_assistance(ai_query)

    def interactive_mode(self):
        """Run the agent in interactive mode"""
        print("VPPctl AI Agent - Interactive Mode")
        print("Type 'help' for assistance, 'quit' to exit")
        print("-" * 50)

        while True:
            try:
                user_input = input("vpp-ai> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    break

                if user_input.lower() == 'help':
                    self._show_help()
                    continue

                if user_input.lower().startswith('analyze'):
                    issue = user_input[7:].strip()
                    if issue:
                        print(self.analyze_issue(issue))
                    else:
                        print("Usage: analyze <issue description>")
                    continue

                if user_input.lower().startswith('configure'):
                    req = user_input[10:].strip()
                    if req:
                        print(self.suggest_configuration(req))
                    else:
                        print("Usage: configure <requirement>")
                    continue

                # Smart detection: distinguish between VPP commands and natural language
                if self._is_likely_vpp_command(user_input):
                    stdout, stderr = self.execute_vppctl(user_input)
                    if stdout:
                        print(stdout)
                    if stderr:
                        print(f"Error: {stderr}")
                else:
                    # Treat as natural language query
                    print(self.get_ai_assistance(user_input))

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"Error: {str(e)}")

    def _is_likely_vpp_command(self, input_text: str) -> bool:
        """
        Determine if input is likely a VPP command or natural language query.

        Returns True if it looks like a VPP command, False if natural language.
        """
        input_lower = input_text.lower().strip()

        # Direct VPP command patterns (exact syntax)
        vpp_patterns = [
            r'^show\s+(version|interfaces?|int|interface\s+address|ip\s+fib|ipsec\s+(sa|spd|tunnel)|lcp|errors|run)$',
            r'^set\s+interface\s+(state|ip\s+address)\s+',
            r'^ip\s+route\s+add\s+',
            r'^create\s+ipsec\s+tunnel',
            r'^lcp\s+lcp-sync\s+(on|off)$',
            r'^delete\s+',
        ]

        for pattern in vpp_patterns:
            if re.match(pattern, input_lower):
                return True

        # Natural language indicators (words that suggest it's not a command)
        natural_words = [
            'what', 'how', 'why', 'explain', 'tell', 'show me', 'can you',
            'please', 'help me', 'i need', 'i want', 'give me', 'let me',
            'could you', 'would you', 'do you', 'are there', 'is there'
        ]

        # Check if input contains natural language indicators
        for word in natural_words:
            if word in input_lower:
                return False

        # If it starts with common VPP verbs but has natural language elements
        vpp_verbs = ['show', 'set', 'create', 'delete', 'ip', 'lcp']
        has_vpp_verb = any(input_lower.startswith(verb) for verb in vpp_verbs)

        if has_vpp_verb:
            # Additional check: if it has many words or articles, likely natural language
            words = input_lower.split()
            if len(words) > 3 or any(word in ['the', 'a', 'an', 'and', 'or'] for word in words):
                return False
            # If it's a short, exact command, treat as VPP command
            return True

        # Default to natural language for anything unclear
        return False

    def _show_help(self):
        """Show help information"""
        help_text = """
VPPctl AI Agent Commands:

Direct VPP commands:
  show interfaces                    - Display interfaces
  show ip fib                       - Show routing table
  show ipsec sa                     - Show IPsec SAs
  set interface state <if> <up|down> - Change interface state
  ... (any vppctl command)

AI-powered commands:
  analyze <issue>                   - Analyze a network issue
  configure <requirement>           - Get configuration suggestions
  <natural language query>          - Ask anything about VPP

Smart Detection:
  ✅ show interfaces                 - Direct VPP command
  ✅ show me interfaces              - Natural language → AI response
  ✅ what are VPP interfaces?        - Natural language → AI explanation

Special commands:
  help                              - Show this help
  quit                              - Exit the agent

Examples:
  vpp-ai> analyze packet loss between interfaces
  vpp-ai> configure ipsec tunnel between two sites
  vpp-ai> how do I set up VLAN interfaces?
  vpp-ai> show me interfaces and routing tables
  vpp-ai> what is VPP?
  vpp-ai> show interfaces  (direct VPP command)
        """
        print(help_text)

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="VPPctl AI Agent")
    parser.add_argument("-s", "--socket", default="/run/vpp/cli.sock",
                       help="VPP socket path")
    parser.add_argument("-m", "--model", default="mistral",
                       help="AI model to use (requires Ollama)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

    # Create agent
    agent = VPPctlAgent(socket_path=args.socket, ai_model=args.model)

    # Check VPP connectivity (quick test)
    print(f"Connecting to VPP at {args.socket}...")
    stdout, stderr = agent.execute_vppctl("show version", timeout=5)  # Quick 5-second test
    if stderr and "Connection refused" in stderr:
        print("Warning: VPP not running or socket not accessible.")
        print("AI features will work, but VPP commands will fail.")
    elif stderr:
        print(f"Warning: {stderr}")
    elif stdout:
        print("VPP connection successful!")
        print(stdout.split('\n')[0])  # Show version line
    else:
        print("Warning: Could not verify VPP connection. Some features may not work.")

    # Start interactive mode
    agent.interactive_mode()

if __name__ == "__main__":
    main()