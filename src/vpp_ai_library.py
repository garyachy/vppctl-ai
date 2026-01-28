"""
VPP AI Library - Advanced VPP command parsing and analysis
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class ParsedCommand:
    """Parsed VPP command structure"""
    action: str
    target: str
    parameters: Dict[str, Any]
    raw_command: str

class VPPCommandParser:
    """Parse and understand VPP commands"""

    def __init__(self):
        self.command_patterns = {
            r'show\s+(interfaces?|int)': self._parse_show_interfaces,
            r'show\s+ip\s+fib': self._parse_show_ip_fib,
            r'show\s+ipsec\s+sa': self._parse_show_ipsec_sa,
            r'show\s+ipsec\s+spd': self._parse_show_ipsec_spd,
            r'show\s+errors': self._parse_show_errors,
            r'set\s+interface\s+(state|ip\s+address)': self._parse_set_interface,
            r'ip\s+route\s+add': self._parse_ip_route_add,
            r'create\s+ipsec\s+tunnel': self._parse_create_ipsec_tunnel,
        }

    def parse(self, command: str) -> Optional[ParsedCommand]:
        """Parse a VPP command into structured data"""
        command_lower = command.strip().lower()
        command_original = command.strip()

        for pattern, parser_func in self.command_patterns.items():
            if re.match(pattern, command_lower, re.IGNORECASE):
                return parser_func(command_original)

        return None

    def _parse_show_interfaces(self, command: str) -> ParsedCommand:
        return ParsedCommand(
            action="show",
            target="interfaces",
            parameters={},
            raw_command=command
        )

    def _parse_show_ip_fib(self, command: str) -> ParsedCommand:
        return ParsedCommand(
            action="show",
            target="ip_fib",
            parameters={},
            raw_command=command
        )

    def _parse_show_ipsec_sa(self, command: str) -> ParsedCommand:
        return ParsedCommand(
            action="show",
            target="ipsec_sa",
            parameters={},
            raw_command=command
        )

    def _parse_show_ipsec_spd(self, command: str) -> ParsedCommand:
        return ParsedCommand(
            action="show",
            target="ipsec_spd",
            parameters={},
            raw_command=command
        )

    def _parse_show_errors(self, command: str) -> ParsedCommand:
        return ParsedCommand(
            action="show",
            target="errors",
            parameters={},
            raw_command=command
        )

    def _parse_set_interface(self, command: str) -> ParsedCommand:
        # Parse: set interface state|ip address <interface> <parameters>
        parts = command.split()
        if len(parts) >= 4:
            action_type = "state" if "state" in parts else "ip_address"
            interface = parts[3]
            value = " ".join(parts[4:]) if len(parts) > 4 else ""

            return ParsedCommand(
                action="set",
                target="interface",
                parameters={
                    "interface": interface,
                    "type": action_type,
                    "value": value
                },
                raw_command=command
            )
        return None

    def _parse_ip_route_add(self, command: str) -> ParsedCommand:
        # Parse: ip route add <prefix> via <next-hop>
        match = re.search(r'ip\s+route\s+add\s+(\S+)\s+via\s+(\S+)', command, re.IGNORECASE)
        if match:
            prefix, next_hop = match.groups()
            return ParsedCommand(
                action="add",
                target="route",
                parameters={
                    "prefix": prefix,
                    "next_hop": next_hop
                },
                raw_command=command
            )
        return None

    def _parse_create_ipsec_tunnel(self, command: str) -> ParsedCommand:
        return ParsedCommand(
            action="create",
            target="ipsec_tunnel",
            parameters={},
            raw_command=command
        )

class VPPStateAnalyzer:
    """Analyze VPP state and provide insights"""

    def __init__(self):
        self.analyzers = {
            "interfaces": self._analyze_interfaces,
            "routing": self._analyze_routing,
            "ipsec": self._analyze_ipsec,
            "errors": self._analyze_errors,
        }

    def analyze(self, component: str, data: Dict) -> str:
        """Analyze a VPP component and return insights"""
        if component in self.analyzers:
            return self.analyzers[component](data)
        return f"No analyzer available for {component}"

    def _analyze_interfaces(self, data: Dict) -> str:
        """Analyze interface configuration"""
        interfaces = data.get("interfaces", [])

        if not interfaces:
            return "No interfaces configured"

        up_count = sum(1 for iface in interfaces if iface.get("state", "").lower() == "up")
        down_count = len(interfaces) - up_count

        analysis = f"Interface Analysis: {len(interfaces)} total interfaces\n"
        analysis += f"  - {up_count} interfaces are UP\n"
        analysis += f"  - {down_count} interfaces are DOWN\n"

        # Check for common issues
        issues = []
        for iface in interfaces:
            if iface.get("state", "").lower() == "down":
                issues.append(f"Interface {iface.get('name')} is administratively down")

        if issues:
            analysis += "\nPotential Issues:\n" + "\n".join(f"  - {issue}" for issue in issues)

        return analysis

    def _analyze_routing(self, data: Dict) -> str:
        """Analyze routing configuration"""
        routes = data.get("routes", [])

        if not routes:
            return "No routes configured in FIB"

        analysis = f"Routing Analysis: {len(routes)} routes in FIB\n"

        # Count route types
        connected_routes = sum(1 for route in routes if route.get("type", "").lower() == "connected")
        static_routes = sum(1 for route in routes if route.get("type", "").lower() == "static")

        analysis += f"  - Connected routes: {connected_routes}\n"
        analysis += f"  - Static routes: {static_routes}\n"

        # Check for default route
        has_default = any(route.get("prefix", "").startswith("0.0.0.0/0") for route in routes)
        analysis += f"  - Default route: {'Present' if has_default else 'Missing'}\n"

        return analysis

    def _analyze_ipsec(self, data: Dict) -> str:
        """Analyze IPsec configuration"""
        sas = data.get("ipsec_sas", [])

        if not sas:
            return "No IPsec Security Associations configured"

        analysis = f"IPsec Analysis: {len(sas)} Security Associations\n"

        # Analyze SA states
        active_sas = sum(1 for sa in sas if sa.get("state", "").lower() in ["active", "installed"])
        inactive_sas = len(sas) - active_sas

        analysis += f"  - Active SAs: {active_sas}\n"
        analysis += f"  - Inactive SAs: {inactive_sas}\n"

        # Check protocols
        esp_count = sum(1 for sa in sas if sa.get("protocol", "").lower() == "esp")
        ah_count = sum(1 for sa in sas if sa.get("protocol", "").lower() == "ah")

        analysis += f"  - ESP SAs: {esp_count}\n"
        analysis += f"  - AH SAs: {ah_count}\n"

        return analysis

    def _analyze_errors(self, data: Dict) -> str:
        """Analyze error counters"""
        errors = data.get("errors", [])

        if not errors:
            return "No errors detected - system appears healthy"

        total_errors = sum(error.get("count", 0) for error in errors)
        critical_errors = [error for error in errors if error.get("count", 0) > 1000]

        analysis = f"Error Analysis: {len(errors)} error types, {total_errors} total errors\n"

        if critical_errors:
            analysis += "\nCritical Errors (>1000 occurrences):\n"
            for error in critical_errors[:5]:  # Show top 5
                analysis += f"  - {error.get('description', 'Unknown')}: {error.get('count', 0)}\n"

        return analysis

class VPPKnowledgeBase:
    """Knowledge base for VPP troubleshooting and configuration"""

    def __init__(self):
        self.common_issues = {
            "packet_loss": {
                "symptoms": ["packets not reaching destination", "low throughput", "connection timeouts"],
                "possible_causes": [
                    "Interface administratively down",
                    "Incorrect routing configuration",
                    "MTU mismatches",
                    "IPsec policy mismatches",
                    "LCP synchronization issues"
                ],
                "diagnostic_commands": [
                    "show interfaces",
                    "show ip fib",
                    "show errors",
                    "show lcp"
                ]
            },
            "routing_issues": {
                "symptoms": ["cannot reach remote networks", "default route missing", "asymmetric routing"],
                "possible_causes": [
                    "Missing default route",
                    "Incorrect next-hop configuration",
                    "Route recursion issues",
                    "LCP route synchronization disabled"
                ],
                "diagnostic_commands": [
                    "show ip fib",
                    "show lcp",
                    "show interface address"
                ]
            },
            "ipsec_problems": {
                "symptoms": ["VPN tunnel not establishing", "encrypted traffic not flowing", "authentication failures"],
                "possible_causes": [
                    "Incorrect crypto keys",
                    "Policy/SA mismatches",
                    "Protocol version issues",
                    "NAT traversal problems"
                ],
                "diagnostic_commands": [
                    "show ipsec sa",
                    "show ipsec spd",
                    "show ipsec tunnel",
                    "show errors"
                ]
            }
        }

    def get_issue_info(self, issue_type: str) -> Optional[Dict]:
        """Get information about a specific issue type"""
        return self.common_issues.get(issue_type.lower())

    def suggest_diagnostics(self, symptoms: List[str]) -> List[str]:
        """Suggest diagnostic commands based on symptoms"""
        suggested_commands = set()

        for symptom in symptoms:
            for issue_type, issue_info in self.common_issues.items():
                if any(symptom.lower() in s.lower() for s in issue_info["symptoms"]):
                    suggested_commands.update(issue_info["diagnostic_commands"])

        return list(suggested_commands)

    def get_common_solutions(self, issue_type: str) -> List[str]:
        """Get common solutions for an issue type"""
        issue_info = self.get_issue_info(issue_type)
        if not issue_info:
            return []

        solutions = []
        for cause in issue_info["possible_causes"]:
            solutions.append(f"Check for: {cause}")

        return solutions