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
import os

# Add src directory to path for imports when running as script
# This allows imports to work both as module and as standalone script
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# Readline for TAB completion
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

# AI Integration - using OpenRouter (free cloud AI models)
try:
    import openai
    import os
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not installed. Install with: pip install openai")

# Enhanced AI with hallucination prevention
try:
    from vpp_ai_enhanced import enhance_agent_with_knowledge
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False
    print("Warning: Enhanced AI features not available")

# ANSI color codes for terminal output
GREY = "\033[90m"
RED = "\033[91m"
RESET = "\033[0m"

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

    def __init__(self, socket_path: str = "/run/vpp/cli.sock", ai_model: str = "anthropic/claude-3-haiku"):
        self.socket_path = socket_path
        self.ai_model = ai_model
        self.state = VPPState()
        self.command_history: List[Tuple[str, str]] = []
        self.last_output: Optional[str] = None  # Store last command output for "explain output" queries
        self.last_command: Optional[str] = None  # Store last command for context
        self.logger = logging.getLogger(__name__)
        
        # Initialize command history database
        try:
            # Try relative import first (when used as module), then absolute (when run as script)
            try:
                from .vpp_history import VPPHistoryDatabase
            except (ImportError, ValueError):
                # When run as script, use absolute import
                from vpp_history import VPPHistoryDatabase
            self.history_db = VPPHistoryDatabase()
            self.session_id = self.history_db.get_session_id()
            self.logger.debug(f"Command history database initialized (session: {self.session_id})")
        except Exception as e:
            self.logger.warning(f"Failed to initialize history database: {e}")
            self.history_db = None
            self.session_id = None

        # Initialize AI client (OpenRouter)
        self.ai_available = False
        self.ai_client = None

        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

            if not api_key:
                self.logger.warning("OPENROUTER_API_KEY not set - AI features disabled")
            else:
                try:
                    # OpenRouter uses OpenAI-compatible API
                    self.ai_client = openai.OpenAI(
                        api_key=api_key,
                        base_url="https://openrouter.ai/api/v1"
                    )

                    # Validate API key with a minimal test call
                    self.ai_client.models.list()
                    self.ai_available = True
                    self.logger.debug("AI client initialized with OpenRouter")

                    # Enhance with knowledge base if available
                    if ENHANCED_AVAILABLE:
                        try:
                            self = enhance_agent_with_knowledge(self)
                            self.logger.debug("Agent enhanced with VPP command database")
                        except Exception as e:
                            self.logger.warning(f"Failed to enhance agent: {e}")

                except Exception as e:
                    error_str = str(e)
                    if "401" in error_str or "Unauthorized" in error_str:
                        self.logger.warning("Invalid OPENROUTER_API_KEY - AI features disabled")
                    else:
                        self.logger.warning(f"AI client initialization failed: {e}")
                    self.ai_available = False
                    self.ai_client = None

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
            self.logger.debug(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            # Store in history
            self.command_history.append((command, result.stdout))
            
            # Store last command and output for "explain output" queries
            self.last_command = command
            self.last_output = result.stdout if result.stdout else result.stderr
            
            # Save to database
            if self.history_db:
                try:
                    self.history_db.add_command(command, result.stdout, self.session_id)
                except Exception as e:
                    self.logger.debug(f"Failed to save command to history database: {e}")

            return result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            self.logger.error(error_msg)
            return "", error_msg
        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            self.logger.error(error_msg)
            return "", error_msg

    def get_vpp_completions(self, partial_command: str) -> List[str]:
        """
        Get command completions from VPP for a partial command.

        Uses VPP's built-in '?' completion feature to get available options.

        Args:
            partial_command: The partial command to complete

        Returns:
            List of possible completions
        """
        try:
            completions = []

            # Query vppctl with '?' to get completions
            # VPP shows available options when command ends with '?'
            query_cmd = partial_command.strip()
            if query_cmd and not query_cmd.endswith('?'):
                query_cmd = query_cmd + ' ?'
            elif not query_cmd:
                query_cmd = '?'

            stdout, stderr = self.execute_vppctl(query_cmd, timeout=5)

            # Parse VPP completion output
            if stdout:
                lines = stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # Skip empty lines and prompts
                    if not line or line.startswith('DBGvpp') or line.startswith('vpp#'):
                        continue

                    # VPP completions are shown as space-separated words
                    # Example output: "acl api buffers cli clock errors event-logger ..."
                    words = line.split()
                    for word in words:
                        # Only add valid completion words (alphanumeric with - and _)
                        if word and re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', word):
                            completions.append(word)

            # If we got completions from VPP, return them
            if completions:
                return sorted(list(set(completions)))
            
            # Use command database to get completions
            try:
                try:
                    from .vpp_cli_parser import VPPCommandDatabase
                except (ImportError, ValueError):
                    from vpp_cli_parser import VPPCommandDatabase
                import sqlite3
                db = VPPCommandDatabase()
                
                # Split the partial command into parts
                parts = partial_command.strip().split()
                if not parts:
                    return []
                
                # Normalize abbreviations (e.g., "int" -> "interface")
                normalized_parts = []
                for part in parts:
                    if part == "int":
                        normalized_parts.append("interface")
                    elif part == "addr":
                        normalized_parts.append("address")
                    else:
                        normalized_parts.append(part)
                
                # Find commands that start with the (normalized) partial command
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.cursor()
                    # Try both original and normalized versions
                    search_patterns = [
                        ' '.join(parts) + ' %',      # Original: "show int %"
                        ' '.join(normalized_parts) + ' %'  # Normalized: "show interface %"
                    ]
                    
                    matching_commands = []
                    for pattern in search_patterns:
                        cursor.execute(
                            'SELECT DISTINCT path FROM commands WHERE path LIKE ? ORDER BY path LIMIT 50',
                            (pattern,)
                        )
                        matching_commands.extend([row[0] for row in cursor.fetchall()])
                    
                    # Remove duplicates
                    matching_commands = list(set(matching_commands))
                
                # Extract the next token(s) from matching commands
                if matching_commands:
                    next_tokens = set()
                    # Use normalized parts to determine where we are in the command
                    target_len = len(normalized_parts)
                    
                    for cmd in matching_commands:
                        cmd_parts = cmd.split()
                        if len(cmd_parts) > target_len:
                            # Get the next token after the partial command
                            next_token = cmd_parts[target_len]
                            # Check if we're still completing the last word
                            if len(parts) > 0 and len(parts) == len(normalized_parts):
                                last_part = parts[-1]
                                # If last_part is a complete word (not being completed), add next_token
                                # If last_part is being completed, check if next_token starts with it
                                if not last_part or next_token.startswith(last_part) or last_part in ['int', 'interface', 'addr', 'address']:
                                    next_tokens.add(next_token)
                            else:
                                next_tokens.add(next_token)
                    
                    completions = sorted(list(next_tokens))
                    
                    # If we got completions from database, use them
                    if completions:
                        return completions
                
                # Fallback: try direct database query
                db_completions = db.get_command_completions(partial_command)
                if db_completions:
                    # Extract next token from these completions
                    parts = partial_command.split()
                    next_tokens = set()
                    for comp in db_completions[:30]:
                        comp_parts = comp.split()
                        if len(comp_parts) > len(parts):
                            next_token = comp_parts[len(parts)]
                            next_tokens.add(next_token)
                    if next_tokens:
                        return sorted(list(next_tokens))
                        
            except Exception as e:
                self.logger.debug(f"Error using command database for completions: {e}")
            
            # Remove duplicates, sort, and return
            completions = sorted(list(set(completions)))
            return completions
            
        except Exception as e:
            self.logger.debug(f"Error getting VPP completions: {e}")
            return []

    def update_state(self):
        """Update internal VPP state by querying current configuration"""
        self.logger.debug("Updating VPP state...")

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

    def _get_interface_names(self) -> List[str]:
        """Get list of current VPP interface names"""
        stdout, _ = self.execute_vppctl("show interfaces")
        interfaces = self._parse_interfaces(stdout)
        return [iface['name'] for iface in interfaces if iface.get('name')]

    def _substitute_placeholders(self, command: str) -> str:
        """
        Substitute placeholders like <interface-name> with actual VPP entity names.

        Args:
            command: Command with potential placeholders

        Returns:
            Command with placeholders replaced by actual entity names
        """
        import re

        # Common placeholder patterns
        interface_placeholders = [
            r'<interface[_-]?name>',
            r'<interface>',
            r'<iface>',
            r'<if[_-]?name>',
            r'\[interface[_-]?name\]',
            r'\[interface\]',
        ]

        # Check if command contains interface placeholders
        for pattern in interface_placeholders:
            if re.search(pattern, command, re.IGNORECASE):
                # Get available interfaces
                interfaces = self._get_interface_names()
                if interfaces:
                    # Filter out local0 if there are other interfaces
                    non_local = [i for i in interfaces if i != 'local0']
                    if non_local:
                        replacement = non_local[0]
                    else:
                        replacement = interfaces[0]
                    command = re.sub(pattern, replacement, command, flags=re.IGNORECASE)
                    break

        return command

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

    def get_automatic_explanation(self, command_output: str, command: str = "") -> str:
        """
        Get automatic explanation of command output - direct and concise, no questions.
        
        Args:
            command_output: The VPP command output to explain
            command: The command that produced this output (optional)
        
        Returns:
            Direct, concise explanation without questions
        """
        if not self.ai_available:
            return ""
        
        system_prompt = """You are a VPP network debugging assistant. The user will provide VPP command output in their message. You MUST explain it immediately.

CRITICAL: The command output is ALREADY PROVIDED in the user's message. Do NOT ask for it. Explain it directly.

Your response format:
- ipv4-VRF:0 - [explanation of what this means]
- fib_index:0 - [explanation]
- flow hash - [explanation]
- etc.

RULES:
1. The output is in the user message - explain it immediately
2. NO questions like "Please provide the output" or "Would you like me to explain"
3. NO phrases like "Let me explain" or "I'll help you understand"
4. Start directly with: "- Field: explanation"
5. Be technical and specific
6. Use bullet points for each field/line

Example response format:
- ipv4-VRF:0 - IPv4 Virtual Routing and Forwarding table ID 0 (default VRF)
- fib_index:0 - Forwarding Information Base index 0
- flow hash:[src dst sport dport proto flowlabel] - Hash function parameters

Begin immediately with the explanation - the output is provided below."""
        
        # Format the output clearly in the user prompt
        user_prompt = f"""EXPLAIN THIS VPP COMMAND OUTPUT:

{command_output}

Provide a direct explanation of each field and value. Start immediately - do not ask for the output, it is provided above."""
        
        try:
            # Don't show "Thinking..." for automatic explanations - they should be seamless
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more focused, direct responses
                max_tokens=1000   # Limit length for concise explanations
            )
            
            explanation = response.choices[0].message.content.strip()
            
            # Enhance explanation with related VPP commands
            enhanced_explanation = self._enhance_explanation_with_commands(explanation, command_output)
            
            return enhanced_explanation
        except Exception as e:
            self.logger.error(f"Failed to get automatic explanation: {e}")
            return ""
    
    def _enhance_explanation_with_commands(self, explanation: str, original_output: str) -> str:
        """
        Enhance explanation by running related VPP commands for each entry.
        
        Args:
            explanation: The AI-generated explanation
            original_output: The original command output
        
        Returns:
            Enhanced explanation with command results appended
        """
        import re
        
        # Patterns to extract VPP objects and their indices
        # Format: (pattern, command_template, group_index)
        # Based on VPP source code: show fib path-lists <index>, show fib paths <index>, show fib entry <index>
        patterns = [
            (r'path-list:\[(\d+)\]', 'show fib path-lists {}', 1),
            (r'path:\[(\d+)\]', 'show fib paths {}', 1),
            (r'pl-index:(\d+)', 'show fib path-lists {}', 1),  # path-list index
            (r'fib:(\d+)\s+index:(\d+)', 'show fib entry {}', 2),  # fib:0 index:4 -> show fib entry 4
            (r'index:(\d+)\s+locks:', 'show fib entry {}', 1),  # index:4 locks: -> show fib entry 4
            # Note: DPO and uRPF commands may not have direct show commands, skip for now
            # (r'dpo-load-balance:.*index:(\d+)', 'show dpo {}', 1),
            # (r'uRPF:(\d+)', 'show urpf {}', 1),
            # (r'uPRF-list:(\d+)', 'show urpf {}', 1),
        ]
        
        executed_commands = {}  # Track executed commands to avoid duplicates
        command_results = []
        attempted_commands = []  # Track all attempted commands for debugging
        max_commands = 5  # Limit number of related commands to avoid excessive output
        
        # Extract all matches from both explanation and original output
        all_text = explanation + "\n" + original_output
        
        for pattern, command_template, group_index in patterns:
            if len(command_results) >= max_commands:
                break  # Stop if we've reached the limit
            
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                if len(command_results) >= max_commands:
                    break
                    
                if match.groups():
                    index = match.group(group_index)
                else:
                    index = match.group(0)
                vpp_command = command_template.format(index)
                
                # Avoid duplicate commands
                if vpp_command not in executed_commands:
                    executed_commands[vpp_command] = True
                    attempted_commands.append(vpp_command)
                    try:
                        stdout, stderr = self.execute_vppctl(vpp_command)
                        
                        # Check if command was successful
                        has_output = stdout and stdout.strip()
                        has_error = stderr and any(err in stderr.lower() for err in ['unknown', 'invalid', 'error', 'failed'])
                        
                        if has_output:
                            # Check for common error indicators in stdout
                            stdout_lower = stdout.lower()
                            if ('unknown' not in stdout_lower and 
                                'invalid' not in stdout_lower and
                                'error' not in stdout_lower):
                                # Include the output (even if short)
                                result_text = stdout.strip()
                                # If there's stderr but it's not an error, include it as a note
                                if stderr and not has_error:
                                    result_text += f"\n(Note: {stderr.strip()})"
                                command_results.append(f"\n📋 Related command: `{vpp_command}`\n{result_text}")
                            else:
                                # Command returned error message in stdout
                                command_results.append(f"\n📋 Related command: `{vpp_command}`\n❌ {stdout.strip()}")
                        elif has_error:
                            # Command failed with error - show it
                            command_results.append(f"\n📋 Related command: `{vpp_command}`\n❌ Error: {stderr.strip()}")
                        elif stderr and stderr.strip():
                            # Has stderr - might be warning/info or error
                            stderr_lower = stderr.lower()
                            if any(err in stderr_lower for err in ['unknown', 'invalid', 'not found', 'does not exist']):
                                # It's an error - show it
                                command_results.append(f"\n📋 Related command: `{vpp_command}`\n❌ {stderr.strip()}")
                            # Otherwise, it might be a warning/info - we'll skip it to avoid clutter
                        # If no output and no error, skip showing it (command might not exist or returned empty)
                    except Exception as e:
                        command_results.append(f"\n📋 Related command: `{vpp_command}`\n❌ Exception: {str(e)}")
        
        # Append command results to explanation
        if command_results:
            explanation += "\n\n" + "=" * 60
            explanation += "\n📊 **Related Command Details:**"
            explanation += "\n" + "=" * 60
            explanation += "".join(command_results)
        
        return explanation

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
            return "AI assistance not available. Set OPENROUTER_API_KEY environment variable with a valid API key."

        # Prepare context - focused on debugging network issues only
        system_prompt = """You are a VPP network debugging assistant. Your ONLY purpose is to help debug network issues using vppctl commands.

STRICT RULES:
1. ONLY answer questions about debugging network problems, troubleshooting VPP issues, or interpreting vppctl command output
2. DO NOT provide general information about VPP features, architecture, or capabilities
3. DO NOT explain what VPP is or how it works in general
4. DO NOT provide tutorials or general documentation
5. If asked a general question, respond: "I only help with debugging network issues using vppctl. Please ask about specific network problems, command output interpretation, or troubleshooting steps."
6. Focus on: analyzing command output, diagnosing network issues, suggesting vppctl commands for troubleshooting, interpreting error messages
7. CRITICAL: Use EXACT vppctl command syntax. DO NOT make up command parameters or syntax. If unsure about a command, say "I'm not certain about the exact syntax for this command. Please check the vppctl help or use TAB completion."
8. IMPORTANT: For trace commands, use "trace add <input-graph-node>" NOT "trace add <interface_name>". VPP traces packets at graph nodes, not interfaces directly.
9. When explaining command output: Provide DETAILED explanations of EACH field, line, and value. Explain what each part means, what it indicates about the network state, and what actions might be needed if there are issues.

Examples of what to answer:
- "Why is my interface down?" → Help debug
- "What does this error mean?" → Explain the error
- "How to troubleshoot packet loss?" → Provide debugging steps with vppctl commands
- "Explain output above" → Provide detailed line-by-line explanation of the previous command output
- "Explain each detail" → Explain every field and value in the output

Examples of what to REJECT:
- "What is VPP?" → Reject (general info)
- "Show me VPP features" → Reject (general info)
- "Tell me about VPP" → Reject (general info)"""

        # Check if user is asking to explain output
        output_explanation_keywords = ['explain output', 'explain result', 'explain above', 'explain previous', 
                                       'what output mean', 'what result mean', 'interpret output', 'explain detail', 'explain each']
        is_output_explanation = any(keyword in user_query.lower() for keyword in output_explanation_keywords)
        
        # Add last command output if user is asking to explain it
        if is_output_explanation and self.last_output:
            output_context = f"\n\nPrevious command: {self.last_command}\nCommand output to explain:\n{self.last_output}"
            # Truncate if too long (keep important parts)
            if len(output_context) > 3000:
                # Keep first 2000 chars and last 1000 chars
                output_context = output_context[:2000] + "\n\n[... output truncated ...]\n\n" + output_context[-1000:]
            system_prompt += output_context
            system_prompt += "\n\nPlease provide a DETAILED explanation of this output, explaining each field, value, and what it means for the network state."
        
        # Only add context for analyze/configure commands, not general questions
        if context and (user_query.lower().startswith('analyze') or user_query.lower().startswith('configure')):
            # Truncate context if too long
            if len(context) > 500:
                context = context[:500] + "..."
            system_prompt += f"\n\nCurrent VPP context:\n{context}"

        try:
            print("🤖 Thinking... (this may take a few seconds)")
            # Simplify the prompt if it's too long
            if len(system_prompt) > 4000:  # OpenRouter has higher limits
                system_prompt = system_prompt[:4000] + "\n\n[Context truncated for brevity]"

            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_query}
                ],
                max_tokens=2000,
                temperature=0.7
            )

            result = response.choices[0].message.content
            if not result.strip():
                return "AI returned empty response. Try rephrasing your question."
            return result

        except Exception as e:
            return f"AI assistance failed: {str(e)}. Please check your OPENROUTER_API_KEY environment variable."

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

    class VPPCompleter:
        """Readline completer for VPP commands"""
        def __init__(self, agent):
            self.agent = agent
            self.matches = []
        
        def complete(self, text, state):
            """Complete function for readline"""
            # On first call (state == 0), get the current line and find completions
            if state == 0:
                line_buffer = readline.get_line_buffer()
                begidx = readline.get_begidx()
                endidx = readline.get_endidx()
                
                # Get the partial command up to the cursor
                partial = line_buffer[:endidx].rstrip()
                
                # Get completions from VPP for the partial command
                all_completions = self.agent.get_vpp_completions(partial)
                
                # The 'text' parameter is the word fragment being completed
                # If text is empty, we're completing after a space - show all options
                if text:
                    # Filter completions that start with the text being completed
                    self.matches = [m for m in all_completions if m.startswith(text)]
                else:
                    # No text fragment - we're at the start of a new word
                    # Use all completions
                    self.matches = all_completions
                
                # If no matches, return None to indicate no completion
                if not self.matches:
                    return None
                
                # If multiple matches, configure readline to show them all
                if len(self.matches) > 1:
                    try:
                        readline.set_completion_display_matches_hook(self._display_matches)
                    except AttributeError:
                        # Older Python versions might not have this
                        pass
                    # Also print completions directly (fallback if readline doesn't display them)
                    if partial:  # Only if we have a partial command
                        print()  # New line
                        cols = 5
                        col_width = max(len(m) for m in self.matches) + 2
                        for i in range(0, len(self.matches), cols):
                            row = self.matches[i:i+cols]
                            print(' '.join(f"{m:<{col_width}}" for m in row))
                        # Re-print prompt and current input
                        print(f"vpp-ai> {line_buffer}", end='', flush=True)
            
            # Return the match for this state
            try:
                if state < len(self.matches):
                    return self.matches[state]
                else:
                    return None
            except (IndexError, AttributeError):
                return None
        
        def _display_matches(self, substitution, matches, longest_match_length):
            """Display all matches in columns like vppctl"""
            if not matches:
                return
            
            # Format in columns (similar to vppctl)
            cols = 5
            col_width = max(len(m) for m in matches) + 2
            
            print()  # New line before showing completions
            for i in range(0, len(matches), cols):
                row = matches[i:i+cols]
                print(' '.join(f"{m:<{col_width}}" for m in row))
            
            # Re-print the prompt and current input
            line_buffer = readline.get_line_buffer()
            print(f"vpp-ai> {line_buffer}", end='', flush=True)

    def interactive_mode(self):
        """Run the agent in interactive mode"""
        print("VPPctl AI Agent - Interactive Mode")
        print("Type 'help' for assistance, 'quit' to exit")
        print("-" * 50)

        # Set up readline for TAB completion
        if READLINE_AVAILABLE:
            try:
                completer = self.VPPCompleter(self)
                readline.set_completer(completer.complete)
                # Use tab for completion
                readline.parse_and_bind("tab: complete")
                # Set completion delimiters (space, tab, newline)
                readline.set_completer_delims(' \t\n')
                # Enable completion in the middle of a word
                try:
                    readline.parse_and_bind("set completion-ignore-case on")
                except:
                    pass  # Some readline versions don't support this
                # Show all matches when multiple completions available
                try:
                    readline.parse_and_bind("set show-all-if-ambiguous on")
                except:
                    pass  # Some readline versions don't support this
                # Show all matches on first TAB
                try:
                    readline.parse_and_bind("set show-all-if-unmodified on")
                except:
                    pass  # Some readline versions don't support this
                self.logger.debug("Readline TAB completion enabled")
                
                # Load command history into readline for UP arrow navigation
                if self.history_db:
                    try:
                        # Load commands from all previous sessions (persistent history)
                        # Use distinct=False to get all commands in order, limit to most recent 1000
                        all_recent = self.history_db.get_recent_commands(limit=1000, distinct=False)
                        if all_recent:
                            # Readline expects oldest first, so newest appears when pressing UP
                            # Commands are already in chronological order (oldest first) from database
                            for cmd in all_recent:
                                if cmd and cmd.strip() and cmd not in ['quit', 'exit', 'help', 'q']:
                                    try:
                                        readline.add_history(cmd)
                                    except:
                                        pass  # Skip if already in history or error
                            # Show user that history was loaded (only if significant number of commands)
                            if len(all_recent) > 0:
                                print(f"📜 Loaded {len(all_recent)} commands from persistent history")
                            self.logger.debug(f"History database: {self.history_db.db_path}")
                        else:
                            self.logger.debug("No previous command history found")
                    except Exception as e:
                        self.logger.warning(f"Failed to load history into readline: {e}")
            except Exception as e:
                self.logger.warning(f"Failed to set up readline completion: {e}")
                # Note: Can't modify module-level READLINE_AVAILABLE here, but that's OK

        while True:
            try:
                # Use custom input that handles TAB for vppctl completions
                user_input = self._get_input_with_tab_completion("vpp-ai> ").strip()

                if not user_input:
                    continue

                # Add command to readline history immediately for UP arrow navigation
                if READLINE_AVAILABLE and user_input and user_input.lower() not in ['quit', 'exit', 'q', 'help']:
                    try:
                        readline.add_history(user_input)
                    except:
                        pass
                
                # Save non-VPP commands to database (VPP commands are saved in execute_vppctl with output)
                if self.history_db and user_input:
                    try:
                        # Don't save internal commands
                        # VPP commands are saved in execute_vppctl() with their output
                        if (user_input.lower() not in ['quit', 'exit', 'q', 'help'] and 
                            not self._is_likely_vpp_command(user_input)):
                            self.history_db.add_command(user_input, None, self.session_id)
                    except Exception as e:
                        self.logger.debug(f"Failed to save command to history: {e}")

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

                if user_input.lower().startswith('commands'):
                    # Show commands by category
                    parts = user_input.split()
                    if len(parts) >= 2:
                        category = parts[1]
                        if hasattr(self, 'get_commands_by_category'):
                            commands = self.get_commands_by_category(category)
                            if commands:
                                print(f"📋 {category.upper()} Commands:")
                                for cmd in commands[:10]:  # Show first 10
                                    print(f"  {cmd['path']}")
                                if len(commands) > 10:
                                    print(f"  ... and {len(commands) - 10} more")
                            else:
                                print(f"No commands found in category: {category}")
                        else:
                            print("Command database not available")
                    else:
                        print("Usage: commands <category>")
                        print("Categories: interfaces, routing, ipsec, system, configuration, show, other")
                    continue

                if user_input.lower().startswith('complete') or user_input.lower().startswith('comp'):
                    # Show completions for a partial command
                    cmd = user_input.split(None, 1)[1] if len(user_input.split()) > 1 else ""
                    if cmd:
                        # Ensure command ends with space to indicate we want completions, not execution
                        if not cmd.endswith(' '):
                            cmd = cmd + ' '
                        completions = self.get_vpp_completions(cmd)
                        if completions:
                            print(f"💡 Completions for `{cmd.strip()}`:")
                            cols = 5
                            col_width = max(len(m) for m in completions) + 2
                            for i in range(0, len(completions), cols):
                                row = completions[i:i+cols]
                                print(' '.join(f"{m:<{col_width}}" for m in row))
                        else:
                            print(f"No completions found for `{cmd.strip()}`")
                    else:
                        print("Usage: complete <partial_command>")
                        print("Example: complete show int")
                    continue

                if user_input.lower().startswith('validate'):
                    # Validate a command
                    cmd = user_input[9:].strip()
                    if cmd:
                        if hasattr(self, 'validate_command'):
                            result = self.validate_command(cmd)
                            if result['valid']:
                                print(f"✅ Valid command: {result['path']}")
                                print(f"   Help: {result['help']}")
                            else:
                                print(f"❌ Invalid command: {cmd}")
                                if result.get('suggestions'):
                                    print("   Suggestions:")
                                for sug in result['suggestions'][:3]:
                                    print(f"     - {sug}")
                        else:
                            print("Command validation not available")
                    else:
                        print("Usage: validate <command>")
                    continue

                # Smart detection: distinguish between VPP commands and natural language
                if self._is_likely_vpp_command(user_input):
                    stdout, stderr = self.execute_vppctl(user_input)
                    if stdout:
                        # Check if output is an error and print in red if so
                        is_error = self._is_vpp_error(stdout)
                        if is_error:
                            print(f"{RED}❌ {stdout}{RESET}")
                        else:
                            print(stdout)
                            # Automatically explain the output (only for substantial output)
                            # Skip explanation for simple confirmations like "OK", empty output, or very short responses
                            output_lines = stdout.strip().split('\n')
                            output_length = len(stdout.strip())
                            # Only explain if output has multiple lines or is substantial (>20 chars)
                            # Skip simple confirmations
                            simple_confirmations = ['ok', 'done', 'success', 'failed', 'error']
                            is_simple_confirmation = stdout.strip().lower() in simple_confirmations
                            # Explain if: not a simple confirmation AND (multiple lines OR substantial single line)
                            should_explain = not is_simple_confirmation and (len(output_lines) > 1 or output_length > 20)

                            if stdout.strip() and self.ai_available and should_explain:
                                print(f"\n{GREY}💡 Automatic Explanation:")
                                try:
                                    explanation = self.get_automatic_explanation(stdout, user_input)
                                    if explanation:
                                        print(f"{explanation}{RESET}")
                                except AttributeError:
                                    # Fallback if method doesn't exist (shouldn't happen, but safety check)
                                    self.logger.warning("get_automatic_explanation not available, skipping auto-explanation")
                                except Exception as e:
                                    self.logger.error(f"Failed to get automatic explanation: {e}")
                    if stderr:
                        print(f"{RED}❌ Error: {stderr}{RESET}")
                        # If command failed with "unknown input", try to get AI suggestion and offer to execute
                        # DO NOT show automatic explanation for errors - show correction instead
                        if 'unknown input' in stderr.lower() and self.ai_available:
                            self._handle_command_failure(user_input, stderr)
                            # Always continue after handling errors (don't fall through to other paths)
                            continue
                else:
                    # Check if it's a VPP command with a typo (before checking general questions)
                    corrected_command = self._try_correct_typo(user_input)
                    if corrected_command and corrected_command != user_input:
                        # Found a correction - show suggestion and try original
                        print(f"💡 Did you mean: `{corrected_command}`?")
                        print(f"   (Trying your command first, use the suggestion if it fails)")
                        stdout, stderr = self.execute_vppctl(user_input)
                        if stdout:
                            is_error = self._is_vpp_error(stdout)
                            if is_error:
                                print(f"{RED}❌ {stdout}{RESET}")
                            else:
                                print(stdout)
                                # Automatically explain the output (only for substantial output)
                                output_lines = stdout.strip().split('\n')
                                output_length = len(stdout.strip())
                                simple_confirmations = ['ok', 'done', 'success', 'failed', 'error']
                                is_simple_confirmation = stdout.strip().lower() in simple_confirmations
                                should_explain = not is_simple_confirmation and (len(output_lines) > 1 or output_length > 20)

                                if stdout.strip() and self.ai_available and should_explain:
                                    print(f"\n{GREY}💡 Automatic Explanation:")
                                    explanation = self.get_automatic_explanation(stdout, user_input)
                                    if explanation:
                                        print(f"{explanation}{RESET}")
                        if stderr and 'unknown' in stderr.lower():
                            # Command failed - suggest trying the correction
                            print(f"\n   💡 Command failed. Try: `{corrected_command}`")
                            # Also offer to execute the correction
                            if self.ai_available:
                                print(f"   Execute corrected command? (y/n): ", end='', flush=True)
                                try:
                                    response = input().strip().lower()
                                    if response in ['y', 'yes', '']:
                                        print(f"\n🔄 Executing: `{corrected_command}`")
                                        stdout2, stderr2 = self.execute_vppctl(corrected_command)
                                        if stdout2:
                                            print(stdout2)
                                        if stderr2:
                                            print(f"{RED}❌ Error: {stderr2}{RESET}")
                                        else:
                                            print("✅ Command executed successfully!")
                                except (EOFError, KeyboardInterrupt):
                                    pass
                        elif stderr:
                            print(f"{RED}❌ Error: {stderr}{RESET}")
                            # Try to get AI suggestion for other errors too
                            if 'unknown input' in stderr.lower() and self.ai_available:
                                self._handle_command_failure(user_input, stderr)
                        continue
                    
                    # Before treating as natural language, check if it starts with a VPP verb
                    # If so, try executing it first (might be a valid command with unusual syntax)
                    vpp_verbs = ['show', 'set', 'create', 'delete', 'ip', 'lcp', 'trace', 'clear', 'pcap']
                    starts_with_vpp_verb = any(user_input.lower().startswith(verb) for verb in vpp_verbs)
                    
                    if starts_with_vpp_verb:
                        # Try executing as VPP command first
                        stdout, stderr = self.execute_vppctl(user_input)
                        if stdout:
                            is_error = self._is_vpp_error(stdout)
                            if is_error:
                                print(f"{RED}❌ {stdout}{RESET}")
                            else:
                                print(stdout)
                                # Automatically explain the output if substantial
                                output_lines = stdout.strip().split('\n')
                                output_length = len(stdout.strip())
                                simple_confirmations = ['ok', 'done', 'success', 'failed', 'error']
                                is_simple_confirmation = stdout.strip().lower() in simple_confirmations
                                should_explain = not is_simple_confirmation and (len(output_lines) > 1 or output_length > 20)

                                if stdout.strip() and self.ai_available and should_explain:
                                    print(f"\n{GREY}💡 Automatic Explanation:")
                                    try:
                                        explanation = self.get_automatic_explanation(stdout, user_input)
                                        if explanation:
                                            print(f"{explanation}{RESET}")
                                    except Exception as e:
                                        self.logger.debug(f"Failed to get automatic explanation: {e}")
                        if stderr:
                            print(f"{RED}❌ Error: {stderr}{RESET}")
                            # If command failed with "unknown input", try to get AI suggestion
                            # DO NOT show automatic explanation for errors - show correction instead
                            if 'unknown input' in stderr.lower() and self.ai_available:
                                self._handle_command_failure(user_input, stderr)
                            # Always continue after handling errors (don't fall through to natural language)
                            continue
                    
                    # Check if it's a general question (not debugging-related)
                    if self._is_general_question(user_input):
                        print("⚠️  I only help with debugging network issues using vppctl.")
                        print("   Please ask about:")
                        print("   - Specific network problems or errors")
                        print("   - Interpreting vppctl command output")
                        print("   - Troubleshooting steps with vppctl commands")
                        print("   - Diagnosing connectivity or performance issues")
                        continue
                    
                    # Treat as natural language query (debugging-related)
                    # First, try to extract the correct VPP command from the request
                    if self.ai_available:
                        suggested_command = self._extract_command_from_natural_language(user_input)
                        if suggested_command:
                            print(f"💡 **Suggested VPP command:** `{suggested_command}`")
                            print(f"   Would you like me to execute this command? (y/n): ", end='', flush=True)
                            try:
                                response = input().strip().lower()
                                if response in ['y', 'yes', '']:
                                    print(f"\n🔄 Executing: `{suggested_command}`")
                                    stdout, stderr = self.execute_vppctl(suggested_command)
                                    # Check for errors in both stdout and stderr
                                    has_error = stderr or (stdout and ('unknown' in stdout.lower() or 'error' in stdout.lower() or 'failed' in stdout.lower()))
                                    if stdout:
                                        print(stdout)
                                        # Auto-explain if substantial output and no error
                                        if not has_error:
                                            output_lines = stdout.strip().split('\n')
                                            output_length = len(stdout.strip())
                                            simple_confirmations = ['ok', 'done', 'success', 'failed', 'error']
                                            is_simple_confirmation = stdout.strip().lower() in simple_confirmations
                                            should_explain = not is_simple_confirmation and (len(output_lines) > 1 or output_length > 20)

                                            if stdout.strip() and should_explain:
                                                print(f"\n{GREY}💡 Automatic Explanation:")
                                                try:
                                                    explanation = self.get_automatic_explanation(stdout, suggested_command)
                                                    if explanation:
                                                        print(f"{explanation}{RESET}")
                                                except Exception as e:
                                                    self.logger.debug(f"Failed to get automatic explanation: {e}")
                                    if stderr:
                                        print(f"{RED}❌ Error: {stderr}{RESET}")
                                    if has_error:
                                        # Try to get correction for errors
                                        error_msg = stderr if stderr else stdout
                                        if 'unknown' in error_msg.lower():
                                            self._handle_command_failure(suggested_command, error_msg)
                                    else:
                                        print("✅ Command executed successfully!")
                                    continue
                                else:
                                    print("   (Skipped - showing AI explanation instead)")
                            except (EOFError, KeyboardInterrupt):
                                print("\n   (Skipped - showing AI explanation instead)")
                    
                    # If user skipped or no command extracted, show regular AI explanation
                    if hasattr(self, 'get_validated_ai_response'):
                        print(self.get_validated_ai_response(user_input))
                    else:
                        print(self.get_ai_assistance(user_input))

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"{RED}❌ Error: {str(e)}{RESET}")

        # Add autocompletion hints
        if hasattr(self, 'autocompleter'):
            print(f"\n💡 Pro tip: Type 'show [TAB]' or use command suggestions for autocompletion")
            print(f"   Available categories: interfaces, routing, ipsec, system, configuration")

    def _extract_command_from_natural_language(self, user_request: str) -> Optional[str]:
        """
        Extract the correct VPP command from a natural language request.

        Args:
            user_request: The user's natural language request

        Returns:
            The suggested VPP command, or None if extraction failed
        """
        import re

        if not self.ai_available:
            return None

        try:
            # Get available interfaces to provide context
            interfaces = self._get_interface_names()
            interface_list = ', '.join(interfaces) if interfaces else 'local0'

            # Use direct API call with focused prompt (no "Thinking..." message)
            system_prompt = """You are a VPP command translator. Convert natural language requests to exact VPP commands.
ONLY output the command in backticks. No explanations, no questions, no refusals.
If unsure, make your best guess using the available interfaces."""

            user_prompt = f"""Convert to VPP command: "{user_request}"

Available interfaces: {interface_list}

Examples:
- "bring up interface" → `set interface state local0 up`
- "bring up int" → `set interface state local0 up`
- "show int" → `show interfaces`
- "add ip" → `set interface ip address local0 10.0.0.1/24`
- "set 1.1.1.1/24" → `set interface ip address local0 1.1.1.1/24`
- "set ip 10.0.0.1/24" → `set interface ip address local0 10.0.0.1/24`
- "set ip address 192.168.1.1/24" → `set interface ip address local0 192.168.1.1/24`

Command:"""

            response_obj = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent output
                max_tokens=100    # Short response expected
            )
            response = response_obj.choices[0].message.content.strip()

            def is_valid_command(cmd: str) -> bool:
                """Check if command looks valid (no garbage like colons in wrong places)"""
                # Reject commands with obvious issues
                if ':' in cmd and 'state' in cmd:  # "set interface state show: up" is invalid
                    return False
                if cmd.count('<') > 0 or cmd.count('>') > 0:  # Still has placeholders
                    return False
                # Must have at least verb + argument
                parts = cmd.split()
                if len(parts) < 2:
                    return False
                return True

            # Extract the command from backticks (most reliable)
            backtick_pattern = r'`([^`]+)`'
            matches = re.findall(backtick_pattern, response)
            for match in matches:
                cmd = match.strip()
                # Verify it looks like a VPP command
                if cmd.startswith(('show', 'set', 'create', 'delete', 'ip', 'clear', 'trace', 'lcp')):
                    # Substitute any remaining placeholders
                    cmd = self._substitute_placeholders(cmd)
                    if is_valid_command(cmd):
                        return cmd

            # If no backticks, try to extract from quotes
            quoted_pattern = r'["\']([^"\']+)["\']'
            matches = re.findall(quoted_pattern, response)
            for match in matches:
                cmd = match.strip()
                if cmd.startswith(('show', 'set', 'create', 'delete', 'ip', 'clear', 'trace', 'lcp')):
                    cmd = self._substitute_placeholders(cmd)
                    if is_valid_command(cmd):
                        return cmd

            # Try to find command-like text (starts with VPP verb)
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('show', 'set', 'create', 'delete', 'ip', 'clear', 'trace', 'lcp')):
                    # Take the first word sequence that looks like a command
                    words = line.split()
                    if len(words) >= 2:  # At least verb + one argument
                        cmd = ' '.join(words[:10])  # Limit to reasonable length
                        cmd = self._substitute_placeholders(cmd)
                        if is_valid_command(cmd):
                            return cmd

            return None
        except Exception as e:
            self.logger.debug(f"Failed to extract command from natural language: {e}")
            return None

    def _handle_command_failure(self, failed_command: str, error: str):
        """
        Handle command failure by asking AI for correct syntax and offering to execute it.
        
        Args:
            failed_command: The command that failed
            error: The error message
        """
        import re
        
        try:
            # Get available interfaces to provide context
            interfaces = self._get_interface_names()
            interface_context = ""
            if interfaces:
                interface_context = f" Available interfaces: {', '.join(interfaces)}."

            # Ask AI for the correct command syntax
            query = f"The command '{failed_command}' failed with error: {error}.{interface_context} What is the correct VPP command syntax to achieve the same goal? Provide ONLY the exact command with actual interface names, no placeholders."

            if hasattr(self, 'get_validated_ai_response'):
                response = self.get_validated_ai_response(query)
            else:
                response = self.get_ai_assistance(query)
            
            # Extract the suggested command from the response
            # Look for commands in backticks or after "correct syntax:" or similar
            suggested_commands = []
            
            # Pattern 1: Commands in backticks
            backtick_pattern = r'`([^`]+)`'
            matches = re.findall(backtick_pattern, response)
            for match in matches:
                # Filter out non-command text
                if match.strip().startswith(('show', 'set', 'create', 'delete', 'ip', 'clear', 'trace')):
                    suggested_commands.append(match.strip())
            
            # Pattern 2: Commands after "correct syntax:" or similar phrases
            syntax_patterns = [
                r'correct syntax[:\s]+([^\n]+)',
                r'correct command[:\s]+([^\n]+)',
                r'use[:\s]+([^\n]+)',
                r'command[:\s]+([^\n]+)',
            ]
            for pattern in syntax_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                for match in matches:
                    cmd = match.strip().strip('"\'`')
                    if cmd.startswith(('show', 'set', 'create', 'delete', 'ip', 'clear', 'trace')):
                        suggested_commands.append(cmd)
            
            # Pattern 3: Look for quoted commands
            quoted_pattern = r'["\']([^"\']+)["\']'
            matches = re.findall(quoted_pattern, response)
            for match in matches:
                if match.strip().startswith(('show', 'set', 'create', 'delete', 'ip', 'clear', 'trace')):
                    suggested_commands.append(match.strip())
            
            # Remove duplicates while preserving order
            seen = set()
            unique_commands = []
            for cmd in suggested_commands:
                if cmd not in seen:
                    seen.add(cmd)
                    unique_commands.append(cmd)
            
            if unique_commands:
                # Take the first (most likely) suggestion and substitute placeholders
                suggested_command = self._substitute_placeholders(unique_commands[0])

                print(f"\n💡 **Suggested correction:** `{suggested_command}`")
                print(f"   Would you like me to execute this command? (y/n): ", end='', flush=True)
                
                try:
                    response = input().strip().lower()
                    if response in ['y', 'yes', '']:
                        print(f"\n🔄 Executing: `{suggested_command}`")
                        stdout, stderr = self.execute_vppctl(suggested_command)
                        if stdout:
                            print(stdout)
                        if stderr:
                            print(f"{RED}❌ Error: {stderr}{RESET}")
                        else:
                            print("✅ Command executed successfully!")
                    else:
                        print("   (Skipped - you can run it manually)")
                except (EOFError, KeyboardInterrupt):
                    print("\n   (Skipped)")
            else:
                # Couldn't extract a clear command, show the AI response
                print(f"\n💡 **AI Suggestion:**")
                # Extract just the command part if possible
                lines = response.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['set interface', 'show', 'create', 'delete']):
                        print(f"   {line.strip()}")
                        break
                else:
                    # Show first few lines of response
                    print(f"   {response[:200]}...")
        except Exception as e:
            self.logger.debug(f"Failed to get command suggestion: {e}")

    def _get_input_with_tab_completion(self, prompt: str) -> str:
        """
        Get input with TAB completion support.
        Uses readline if available, otherwise falls back to regular input.
        """
        # Use readline - it should handle TAB automatically
        return input(prompt)

    def _is_general_question(self, input_text: str) -> bool:
        """
        Detect if a query is asking for general VPP information (not debugging).
        
        Returns True if it's a general question that should be rejected.
        """
        input_lower = input_text.lower().strip()
        
        # Patterns that indicate queries about command output interpretation (debugging-related - ALLOW)
        output_interpretation_patterns = [
            r'explain.*output',
            r'explain.*result',
            r'explain.*above',
            r'explain.*previous',
            r'what.*output.*mean',
            r'what.*result.*mean',
            r'what.*this.*mean',
            r'interpret.*output',
            r'interpret.*result',
            r'help.*understand.*output',
            r'help.*understand.*result',
            r'what.*mean',
            r'explain.*detail',
            r'explain.*each',
        ]
        
        # If it's about interpreting command output, it's debugging-related - ALLOW
        for pattern in output_interpretation_patterns:
            if re.search(pattern, input_lower):
                return False  # Not a general question, it's debugging-related
        
        # Patterns that indicate general questions (not debugging)
        general_patterns = [
            r'^what is vpp',
            r'^what.*vpp$',  # "what is vpp" but not "what does this vpp output mean"
            r'^tell me.*vpp',
            r'^explain.*vpp$',  # "explain vpp" but not "explain vpp output"
            r'^show me.*vpp.*feature',
            r'^what.*vpp.*capabilit',
            r'^what.*vpp.*do$',  # "what does vpp do" but not "what does this vpp output mean"
            r'^how.*vpp.*work$',  # "how does vpp work" but not "how does this vpp output work"
            r'^describe.*vpp',
            r'^vpp.*feature$',
            r'^vpp.*capabilit$',
            r'^vpp.*architecture$',
            r'^vpp.*overview$',
        ]
        
        for pattern in general_patterns:
            if re.search(pattern, input_lower):
                return True
        
        # Check for very short or vague questions
        # BUT: Don't treat VPP commands (even with typos) as general questions
        vpp_verbs = ['show', 'set', 'create', 'delete', 'ip', 'lcp', 'trace', 'clear', 'pcap']
        is_vpp_command = any(input_lower.startswith(verb) for verb in vpp_verbs)
        
        # Keywords that indicate debugging/interpretation (ALLOW these)
        debugging_keywords = ['output', 'result', 'above', 'previous', 'this', 'that', 'mean', 'interpret', 'detail', 'each']
        has_debugging_context = any(keyword in input_lower for keyword in debugging_keywords)
        
        if len(input_text.split()) <= 3 and any(word in input_lower for word in ['what', 'tell', 'explain', 'show']):
            # If it's very short and contains these words, likely general
            # BUT: If it starts with a VPP verb, it's probably a command (maybe with typo)
            # BUT: If it has debugging context (output, result, etc.), it's debugging-related
            if not is_vpp_command and not has_debugging_context and 'debug' not in input_lower and 'troubleshoot' not in input_lower and 'error' not in input_lower:
                return True
        
        return False

    def _is_vpp_error(self, output: str) -> bool:
        """
        Check if VPP output contains an error message.
        VPP often returns errors in stdout, not stderr.
        """
        if not output:
            return False
        output_lower = output.lower()
        error_patterns = [
            'unknown input',
            'unknown command',
            'invalid',
            'failed',
            'error:',
            'not found',
            'does not exist',
            'no such',
        ]
        return any(pattern in output_lower for pattern in error_patterns)

    def _is_complete_command(self, command: str) -> bool:
        """
        Check if a command looks complete (not needing completion).
        Returns True if command appears complete, False if it might need completion.
        """
        # Commands that are typically complete on their own
        complete_patterns = [
            r'^show\s+(version|interfaces?|errors?|run)$',
            r'^show\s+int\s+(addr|address|rx|tx|span)',
            r'^show\s+interface\s+(addr|address|rx|tx|span)',
        ]
        
        for pattern in complete_patterns:
            if re.match(pattern, command.lower()):
                return True
        
        # If command ends with certain keywords, it's likely complete
        if any(command.lower().endswith(word) for word in ['version', 'errors', 'run', 'addr', 'address']):
            return True
        
        # Commands with 3+ words are usually complete
        if len(command.split()) >= 3:
            return True
        
        return False

    def _try_correct_typo(self, input_text: str) -> Optional[str]:
        """
        Try to correct typos in VPP commands.
        
        Returns the corrected command if a good match is found, None otherwise.
        """
        input_lower = input_text.lower().strip()
        
        # Only try to correct if it looks like a VPP command (starts with VPP verb)
        vpp_verbs = ['show', 'set', 'create', 'delete', 'ip', 'lcp', 'trace', 'clear', 'pcap']
        if not any(input_lower.startswith(verb) for verb in vpp_verbs):
            return None
        
        # Common abbreviation/typo mappings
        abbrev_map = {
            'adr': 'addr',
            'adress': 'address',
            'interfaces': 'interface',
            'interaces': 'interface',
            'int': 'interface',  # But only in certain contexts
            'ver': 'version',
            'verson': 'version',
        }
        
        # Try to normalize common typos first
        words = input_lower.split()
        normalized_words = []
        for word in words:
            if word in abbrev_map:
                normalized_words.append(abbrev_map[word])
            else:
                normalized_words.append(word)
        normalized_input = ' '.join(normalized_words)
        
        # Try to use command database for typo correction
        try:
            try:
                from .vpp_cli_parser import VPPCommandDatabase
            except (ImportError, ValueError):
                from vpp_cli_parser import VPPCommandDatabase
            db = VPPCommandDatabase()
            
            # First try with normalized input
            result = db.validate_command(normalized_input)
            if result['valid']:
                return normalized_input
            
            # Try original input
            result = db.validate_command(input_text)
            if result['valid']:
                return input_text
            
            # If not valid, check suggestions
            if result.get('suggestions'):
                suggestions = result['suggestions']
                if suggestions:
                    # Check if any suggestion is very similar
                    input_words = input_lower.split()
                    for suggestion in suggestions:
                        sugg_words = suggestion.lower().split()
                        # If they share the same first word and have similar structure
                        if input_words and sugg_words and input_words[0] == sugg_words[0]:
                            # Check word-by-word similarity
                            matches = sum(1 for i, w in enumerate(input_words) 
                                        if i < len(sugg_words) and (w == sugg_words[i] or w in sugg_words[i] or sugg_words[i] in w))
                            # If at least half the words match, it's likely a good correction
                            if matches >= len(input_words) / 2:
                                return suggestion
                    
                    # If no good match found, but we have suggestions, try the first one
                    # if it starts with the same verb
                    first_suggestion = suggestions[0]
                    if input_words and first_suggestion.lower().startswith(input_words[0]):
                        return first_suggestion
            
            # Also try searching for commands that match the pattern
            # e.g., "show int adr" → search for "show interface" or "show int addr"
            if len(words) >= 2:
                search_pattern = f"{words[0]} {words[1]}"
                similar = db.search_commands(search_pattern)
                if similar:
                    # Check if any result is very close
                    for cmd_info in similar[:3]:
                        cmd = cmd_info['path']
                        cmd_words = cmd.lower().split()
                        # If command starts with same words and is close in structure
                        if (len(cmd_words) >= len(words) and 
                            cmd_words[:len(words)-1] == words[:len(words)-1]):
                            # Last word might be a typo - check if it's close
                            if len(words) == len(cmd_words):
                                # Same number of words - likely a typo correction
                                return cmd
        except Exception as e:
            self.logger.debug(f"Error in typo correction: {e}")
        
        return None

    def _is_likely_vpp_command(self, input_text: str) -> bool:
        """
        Determine if input is likely a VPP command or natural language query.

        Returns True if it looks like a VPP command, False if natural language.
        """
        input_lower = input_text.lower().strip()

        # Direct VPP command patterns (exact syntax)
        # Patterns that match base commands, allowing parameters after
        vpp_patterns = [
            r'^show\s+(version|interfaces?|int(\s+addr|\s+address)?|interface\s+address|ip\s+fib|ipsec\s+(sa|spd|tunnel)|lcp|errors|run)(\s|$)',  # Allow params after
            r'^show\s+ip\s+fib\s+',  # show ip fib with parameters (IP addresses, etc.)
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

        # If it starts with common VPP verbs, check if it's a valid command
        vpp_verbs = ['show', 'set', 'create', 'delete', 'ip', 'lcp', 'trace', 'clear', 'pcap']
        has_vpp_verb = any(input_lower.startswith(verb) for verb in vpp_verbs)

        if has_vpp_verb:
            words = input_lower.split()
            
            # Check for natural language articles/words that indicate it's not a command
            natural_language_words = ['the', 'a', 'an', 'and', 'or', 'me', 'you', 'please', 'can', 'could', 'would']
            if any(word in natural_language_words for word in words):
                return False
            
            # Check if it looks like a command with parameters (IP addresses, interface names, etc.)
            # IP address pattern: digits and dots
            ip_pattern = r'\d+\.\d+\.\d+\.\d+'
            # Interface name pattern: common interface prefixes
            interface_pattern = r'\b(eth|gigabit|ge|tun|tap|vpp|local|bond|vlan|vxlan)\d+'
            # Numbers (for counts, indices, etc.)
            number_pattern = r'\b\d+\b'
            
            # If it contains IP addresses, interface names, or numbers, likely a command with params
            if re.search(ip_pattern, input_lower) or re.search(interface_pattern, input_lower):
                return True
            
            # If it's a short command (<= 4 words), likely a VPP command
            # Longer commands might still be valid if they match patterns above
            if len(words) <= 4:
                return True
            
            # For longer commands, check if they look like natural language
            # Commands typically don't have articles or conversational words
            if not any(word in natural_language_words for word in words):
                # Could be a command with many parameters - be permissive
                return True
            
            return False

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
  commands <category>               - List commands by category
  validate <command>                - Check if command is valid
  complete <partial>                - Show command completions (use if TAB doesn't work)
  <natural language query>          - Ask anything about VPP

Smart Detection:
  ✅ show interfaces                 - Direct VPP command
  ✅ show me interfaces              - Natural language → AI response
  ✅ what are VPP interfaces?        - Natural language → AI explanation

Command Categories:
  interfaces, routing, ipsec, system, configuration, show, lcp, other

Special commands:
  help                              - Show this help
  quit                              - Exit the agent

TAB Completion:
  Press TAB after a partial command to see completions
  If TAB doesn't work, use: complete <partial_command>
  Example: complete show int

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
    parser.add_argument("-m", "--model", default="anthropic/claude-3-haiku",
                       help="AI model to use (requires OpenRouter API key)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

    # Suppress noisy HTTP request logs from openai/httpx unless verbose
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)

    # Create agent
    agent = VPPctlAgent(socket_path=args.socket, ai_model=args.model)

    # Check VPP connectivity (quick test)
    print(f"Connecting to VPP at {args.socket}...")
    stdout, stderr = agent.execute_vppctl("show version", timeout=5)  # Quick 5-second test
    if stderr and "Connection refused" in stderr:
        print("Warning: VPP not running or socket not accessible.")
        if agent.ai_available:
            print("AI features will work, but VPP commands will fail.")
        else:
            print("VPP commands will fail. AI features are also disabled.")
    elif stderr:
        print(f"Warning: {stderr}")
    elif stdout:
        print("VPP connection successful!")
        print(stdout.split('\n')[0])  # Show version line
    else:
        print("Warning: Could not verify VPP connection. Some features may not work.")

    # Show AI availability status
    if not agent.ai_available:
        print("Note: AI features disabled (set OPENROUTER_API_KEY for AI assistance)")

    # Start interactive mode
    agent.interactive_mode()

if __name__ == "__main__":
    main()