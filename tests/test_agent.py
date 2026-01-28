#!/usr/bin/env python3
"""
Test script for VPPctl AI Agent
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.main import VPPctlAgent, VPPState
from src.vpp_ai_library import VPPCommandParser, VPPStateAnalyzer, VPPKnowledgeBase

class TestVPPCommandParser(unittest.TestCase):
    """Test VPP command parsing functionality"""

    def setUp(self):
        self.parser = VPPCommandParser()

    def test_parse_show_interfaces(self):
        """Test parsing show interfaces command"""
        cmd = self.parser.parse("show interfaces")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.action, "show")
        self.assertEqual(cmd.target, "interfaces")

    def test_parse_show_ip_fib(self):
        """Test parsing show ip fib command"""
        cmd = self.parser.parse("show ip fib")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.action, "show")
        self.assertEqual(cmd.target, "ip_fib")

    def test_parse_show_ipsec_sa(self):
        """Test parsing show ipsec sa command"""
        cmd = self.parser.parse("show ipsec sa")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.action, "show")
        self.assertEqual(cmd.target, "ipsec_sa")

    def test_parse_set_interface_state(self):
        """Test parsing set interface state command"""
        cmd = self.parser.parse("set interface state GigabitEthernet0/0/0 up")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.action, "set")
        self.assertEqual(cmd.target, "interface")
        self.assertEqual(cmd.parameters["interface"], "GigabitEthernet0/0/0")
        self.assertEqual(cmd.parameters["type"], "state")
        self.assertEqual(cmd.parameters["value"], "up")

    def test_parse_ip_route_add(self):
        """Test parsing ip route add command"""
        cmd = self.parser.parse("ip route add 192.168.1.0/24 via 10.0.0.1")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.action, "add")
        self.assertEqual(cmd.target, "route")
        self.assertEqual(cmd.parameters["prefix"], "192.168.1.0/24")
        self.assertEqual(cmd.parameters["next_hop"], "10.0.0.1")

    def test_parse_unknown_command(self):
        """Test parsing unknown command"""
        cmd = self.parser.parse("unknown command xyz")
        self.assertIsNone(cmd)

class TestVPPStateAnalyzer(unittest.TestCase):
    """Test VPP state analysis functionality"""

    def setUp(self):
        self.analyzer = VPPStateAnalyzer()

    def test_analyze_interfaces_up_down(self):
        """Test interface analysis with mixed states"""
        data = {
            "interfaces": [
                {"name": "GigabitEthernet0/0/0", "state": "up", "mtu": "9000"},
                {"name": "GigabitEthernet0/0/1", "state": "down", "mtu": "1500"},
                {"name": "GigabitEthernet0/0/2", "state": "up", "mtu": "1500"},
            ]
        }

        result = self.analyzer.analyze("interfaces", data)
        self.assertIn("3 total interfaces", result)
        self.assertIn("2 interfaces are UP", result)
        self.assertIn("1 interfaces are DOWN", result)
        self.assertIn("GigabitEthernet0/0/1 is administratively down", result)

    def test_analyze_interfaces_empty(self):
        """Test interface analysis with no interfaces"""
        data = {"interfaces": []}
        result = self.analyzer.analyze("interfaces", data)
        self.assertEqual(result, "No interfaces configured")

    def test_analyze_routing(self):
        """Test routing analysis"""
        data = {
            "routes": [
                {"prefix": "192.168.1.0/24", "type": "connected", "next_hop": "", "interface": "GigabitEthernet0/0/0"},
                {"prefix": "10.0.0.0/24", "type": "static", "next_hop": "192.168.1.1", "interface": "GigabitEthernet0/0/0"},
                {"prefix": "0.0.0.0/0", "type": "static", "next_hop": "10.0.0.1", "interface": "GigabitEthernet0/0/1"},
            ]
        }

        result = self.analyzer.analyze("routing", data)
        self.assertIn("3 routes in FIB", result)
        self.assertIn("Connected routes: 1", result)
        self.assertIn("Static routes: 2", result)
        self.assertIn("Default route: Present", result)

    def test_analyze_ipsec(self):
        """Test IPsec analysis"""
        data = {
            "ipsec_sas": [
                {"id": "1", "protocol": "esp", "state": "active"},
                {"id": "2", "protocol": "esp", "state": "inactive"},
                {"id": "3", "protocol": "ah", "state": "active"},
            ]
        }

        result = self.analyzer.analyze("ipsec", data)
        self.assertIn("3 Security Associations", result)
        self.assertIn("Active SAs: 2", result)
        self.assertIn("Inactive SAs: 1", result)
        self.assertIn("ESP SAs: 2", result)
        self.assertIn("AH SAs: 1", result)

    def test_analyze_errors(self):
        """Test error analysis"""
        data = {
            "errors": [
                {"description": "IPv4 checksum errors", "count": 5},
                {"description": "IPsec decrypt errors", "count": 1500},
                {"description": "Interface drops", "count": 50},
            ]
        }

        result = self.analyzer.analyze("errors", data)
        self.assertIn("3 error types", result)
        self.assertIn("1555 total errors", result)
        self.assertIn("Critical Errors", result)
        self.assertIn("IPsec decrypt errors: 1500", result)

class TestVPPKnowledgeBase(unittest.TestCase):
    """Test VPP knowledge base functionality"""

    def setUp(self):
        self.kb = VPPKnowledgeBase()

    def test_get_issue_info(self):
        """Test getting issue information"""
        info = self.kb.get_issue_info("packet_loss")
        self.assertIsNotNone(info)
        self.assertIn("symptoms", info)
        self.assertIn("possible_causes", info)
        self.assertIn("diagnostic_commands", info)

    def test_get_unknown_issue_info(self):
        """Test getting information for unknown issue"""
        info = self.kb.get_issue_info("unknown_issue")
        self.assertIsNone(info)

    def test_suggest_diagnostics(self):
        """Test diagnostic command suggestions"""
        symptoms = ["packets not reaching destination", "VPN tunnel not establishing"]
        commands = self.kb.suggest_diagnostics(symptoms)

        self.assertIsInstance(commands, list)
        self.assertGreater(len(commands), 0)
        # Should include commands from both packet_loss and ipsec_problems
        self.assertTrue(any("interfaces" in cmd for cmd in commands) or any("ipsec" in cmd for cmd in commands))

class TestVPPctlAgent(unittest.TestCase):
    """Test VPPctlAgent functionality"""

    def setUp(self):
        self.agent = VPPctlAgent(socket_path="/tmp/test.sock")

    @patch('subprocess.run')
    def test_execute_vppctl_success(self, mock_run):
        """Test successful vppctl command execution"""
        mock_run.return_value = Mock(stdout="Version: 22.06\n", stderr="", returncode=0)

        stdout, stderr = self.agent.execute_vppctl("show version")

        self.assertEqual(stdout, "Version: 22.06\n")
        self.assertEqual(stderr, "")
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_execute_vppctl_timeout(self, mock_run):
        """Test vppctl command timeout"""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("vppctl", 30)

        stdout, stderr = self.agent.execute_vppctl("show version", timeout=30)

        self.assertEqual(stdout, "")
        self.assertIn("timed out", stderr)

    def test_parse_interfaces(self):
        """Test interface parsing"""
        output = """Name              Idx    State  MTU (L3/IP4/IP6/MPLS)  Counter          Count
GigabitEthernet0/0/0  1      up     9000/0/0/0         rx packets         100
GigabitEthernet0/0/1  2      down   1500/0/0/0         rx packets         50
"""

        interfaces = self.agent._parse_interfaces(output)

        self.assertEqual(len(interfaces), 2)
        self.assertEqual(interfaces[0]["name"], "GigabitEthernet0/0/0")
        self.assertEqual(interfaces[0]["idx"], "1")
        self.assertEqual(interfaces[0]["state"], "up")
        self.assertEqual(interfaces[0]["mtu"], "9000/0/0/0")
        self.assertEqual(interfaces[1]["name"], "GigabitEthernet0/0/1")
        self.assertEqual(interfaces[1]["idx"], "2")
        self.assertEqual(interfaces[1]["state"], "down")

    def test_parse_routes(self):
        """Test route parsing"""
        output = """Prefix               fib-idx  Type    Next Hop
192.168.1.0/24         0        connected  GigabitEthernet0/0/0
10.0.0.0/24            0        static    192.168.1.1
0.0.0.0/0              0        static    10.0.0.1
"""

        routes = self.agent._parse_routes(output)

        self.assertEqual(len(routes), 3)
        self.assertEqual(routes[0]["prefix"], "192.168.1.0/24")
        self.assertEqual(routes[0]["fib_idx"], "0")
        self.assertEqual(routes[0]["type"], "connected")
        self.assertEqual(routes[0]["next_hop"], "GigabitEthernet0/0/0")
        self.assertEqual(routes[1]["prefix"], "10.0.0.0/24")
        self.assertEqual(routes[1]["fib_idx"], "0")
        self.assertEqual(routes[1]["type"], "static")
        self.assertEqual(routes[1]["next_hop"], "192.168.1.1")

    def test_parse_ipsec_sas(self):
        """Test IPsec SA parsing"""
        output = """sa-id  protocol  state
1       esp       active
2       esp       inactive
3       ah        active
"""

        sas = self.agent._parse_ipsec_sas(output)

        self.assertEqual(len(sas), 3)
        self.assertEqual(sas[0]["id"], "1")
        self.assertEqual(sas[0]["protocol"], "esp")
        self.assertEqual(sas[0]["state"], "active")

    def test_parse_errors(self):
        """Test error parsing"""
        output = """Count Node Reason
5 ip4-input IPv4 checksum errors
1500 ipsec-decrypt decrypt errors
50 ethernet-input interface drops
"""

        errors = self.agent._parse_errors(output)

        self.assertEqual(len(errors), 3)
        self.assertEqual(errors[0]["count"], 5)
        self.assertEqual(errors[0]["node"], "ip4-input")
        self.assertEqual(errors[0]["reason"], "IPv4 checksum errors")
        self.assertEqual(errors[1]["count"], 1500)
        self.assertEqual(errors[1]["node"], "ipsec-decrypt")
        self.assertEqual(errors[1]["reason"], "decrypt errors")

    @patch('ollama.Client')
    def test_get_ai_assistance_available(self, mock_client_class):
        """Test AI assistance when available"""
        mock_client = Mock()
        mock_client.list.return_value = [{"name": "llama2"}]
        mock_client.chat.return_value = {"message": {"content": "This is AI help"}}
        mock_client_class.return_value = mock_client

        agent = VPPctlAgent()
        agent.ai_available = True

        response = agent.get_ai_assistance("How do I configure an interface?")

        self.assertEqual(response, "This is AI help")
        mock_client.chat.assert_called_once()

    def test_get_ai_assistance_unavailable(self):
        """Test AI assistance when unavailable"""
        agent = VPPctlAgent()
        agent.ai_available = False

        response = agent.get_ai_assistance("How do I configure an interface?")

        self.assertIn("AI assistance not available", response)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = VPPctlAgent(socket_path="/tmp/test.sock", ai_model="llama2")

        self.assertEqual(agent.socket_path, "/tmp/test.sock")
        self.assertEqual(agent.ai_model, "llama2")
        self.assertIsInstance(agent.state, VPPState)
        self.assertIsInstance(agent.command_history, list)

    def test_state_update_flow(self):
        """Test the complete state update flow"""
        agent = VPPctlAgent()

        # Mock the execute_vppctl method
        with patch.object(agent, 'execute_vppctl') as mock_execute:
            mock_execute.side_effect = [
                ("Name Idx State MTU\nGigabitEthernet0/0/0 1 up 9000\n", ""),
                ("Prefix fib-idx Type NextHop\n192.168.1.0/24 0 connected GigabitEthernet0/0/0\n", ""),
                ("sa-id protocol state\n1 esp active\n2 esp inactive\n", ""),
                ("Count Node Reason\n5 ip4-input IPv4 checksum errors\n", "")
            ]

            agent.update_state()

            # Verify state was updated
            self.assertEqual(len(agent.state.interfaces), 1)
            self.assertEqual(len(agent.state.routes), 1)
            self.assertEqual(len(agent.state.ipsec_sas), 2)
            self.assertEqual(len(agent.state.errors), 1)

def run_basic_functionality_test():
    """Run basic functionality test without VPP"""
    print("Running basic functionality tests...")

    agent = VPPctlAgent()

    # Test command execution (will fail without VPP, but tests the wrapper)
    print("Testing vppctl command execution...")
    stdout, stderr = agent.execute_vppctl("show version")
    print(f"Command output: {stdout[:100] if stdout else 'No output'}")
    if stderr:
        print(f"Command error: {stderr}")

    # Test command parsing
    print("\nTesting command parsing...")
    parser = VPPCommandParser()

    test_commands = [
        "show interfaces",
        "show ip fib",
        "set interface state GigabitEthernet0/0/0 up",
        "ip route add 192.168.1.0/24 via 10.0.0.1"
    ]

    for cmd in test_commands:
        parsed = parser.parse(cmd)
        if parsed:
            print(f"  {cmd} -> action: {parsed.action}, target: {parsed.target}")
        else:
            print(f"  {cmd} -> could not parse")

    # Test AI functionality (if available)
    if agent.ai_available:
        print("\nTesting AI functionality...")
        response = agent.get_ai_assistance("What is VPP?")
        print(f"AI Response: {response[:200]}...")
    else:
        print("\nAI not available - install Ollama to enable AI features")

    print("\nBasic functionality test completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--basic":
        run_basic_functionality_test()
    else:
        # Run unit tests
        unittest.main(verbosity=2)