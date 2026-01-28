#!/usr/bin/env python3
"""
Enhanced VPP AI Agent with Hallucination Prevention

Integrates VPP command database for validating AI responses
and providing intelligent autocompletion.
"""

import re
from typing import List, Dict, Optional
from .vpp_cli_parser import VPPCommandDatabase, VPPCommandValidator

class EnhancedVPPctlAgent:
    """Enhanced VPP AI Agent with hallucination prevention"""

    def __init__(self, original_agent):
        self.original_agent = original_agent
        self.command_db = VPPCommandDatabase()
        self.validator = VPPCommandValidator(self.command_db)

    def get_validated_ai_response(self, user_query: str) -> str:
        """
        Get AI response with hallucination prevention

        1. Get AI response
        2. Validate any suggested commands
        3. Provide corrections/suggestions for invalid commands
        """
        # Get original AI response
        ai_response = self.original_agent.get_ai_assistance(user_query)

        # Validate for hallucinations
        validation = self.validator.validate_ai_response(ai_response)

        # Show warning if there are invalid commands OR low confidence
        if validation['invalid_commands'] or validation['confidence'] < 0.8:
            ai_response += "\n\n⚠️ **Command Validation Warning:**\n"
            
            if validation['invalid_commands']:
                # Show known hallucinations first with specific explanations
                known_hallucs = validation.get('known_hallucinations', {})
                if known_hallucs:
                    ai_response += f"🚫 **Known Incorrect Commands Detected:**\n"
                    for cmd, info in list(known_hallucs.items())[:3]:
                        ai_response += f"   - `{cmd}`\n"
                        ai_response += f"     ❌ {info['reason']}\n"
                        ai_response += f"     ✅ Correct syntax: `{info['correct']}`\n"
                    ai_response += "\n"
                
                # Show other invalid commands
                other_invalid = [c for c in validation['invalid_commands'] if c not in known_hallucs]
                if other_invalid:
                    ai_response += f"⚠️  The following commands may be incorrect or not exist in VPP:\n"
                    for cmd in other_invalid[:5]:  # Show first 5
                        ai_response += f"   - `{cmd}`\n"
                        if cmd in validation['suggestions'] and validation['suggestions'][cmd]:
                            suggestions = validation['suggestions'][cmd][:3]
                            ai_response += f"     💡 Did you mean: {', '.join(suggestions)}\n"
                    
                    if len(other_invalid) > 5:
                        ai_response += f"     ... and {len(other_invalid) - 5} more invalid commands\n"
            else:
                ai_response += "Some commands suggested above may not be accurate. Please verify before using.\n"
            
            ai_response += "\n💡 **Tip:** Use 'show [TAB]' for command completion or 'validate <command>' to check commands"

        return ai_response

    def get_command_suggestions(self, partial_command: str) -> List[str]:
        """Get command suggestions for autocompletion"""
        return self.command_db.get_command_completions(partial_command)

    def validate_and_correct_command(self, command: str) -> Dict:
        """Validate a command and provide corrections if invalid"""
        return self.command_db.validate_command(command)

    def get_commands_by_category(self, category: str) -> List[Dict]:
        """Get all commands in a category for exploration"""
        return self.command_db.get_commands_by_category(category)

class VPPAutocompleter:
    """Autocompletion system for VPP commands"""

    def __init__(self, command_db: VPPCommandDatabase):
        self.command_db = command_db

    def complete_command(self, partial: str) -> List[str]:
        """Complete a partial command"""
        return self.command_db.get_command_completions(partial)

    def get_help_for_command(self, command: str) -> Optional[str]:
        """Get help text for a specific command"""
        result = self.command_db.validate_command(command)
        if result['valid']:
            return result['help']
        return None

    def suggest_similar_commands(self, invalid_command: str) -> List[str]:
        """Suggest similar commands for typos or unknown commands"""
        result = self.command_db.validate_command(invalid_command)
        return result.get('suggestions', [])

def enhance_agent_with_knowledge(original_agent):
    """Add knowledge-based enhancements to existing agent"""
    enhanced_agent = EnhancedVPPctlAgent(original_agent)

    # Add new methods to original agent
    original_agent.get_validated_ai_response = enhanced_agent.get_validated_ai_response
    original_agent.get_command_suggestions = enhanced_agent.get_command_suggestions
    original_agent.validate_command = enhanced_agent.validate_and_correct_command
    original_agent.get_commands_by_category = enhanced_agent.get_commands_by_category

    # Add autocompleter
    original_agent.autocompleter = VPPAutocompleter(enhanced_agent.command_db)

    return original_agent

# Example usage and testing functions
def test_enhanced_agent():
    """Test the enhanced agent functionality"""
    print("🧠 Testing Enhanced VPP AI Agent")
    print("=" * 50)

    # Import the original agent (this would normally be done in main.py)
    import sys
    sys.path.append('.')
    from main import VPPctlAgent

    # Create original agent
    original_agent = VPPctlAgent()

    # Enhance it
    enhanced_agent = enhance_agent_with_knowledge(original_agent)

    print("✅ Agent enhanced with command database")

    # Test command validation
    print("\n🧪 Testing Command Validation:")
    test_commands = [
        'show version',      # Valid
        'show interfaces',   # Valid
        'show unicorns',     # Invalid
        'set magic on'       # Invalid
    ]

    for cmd in test_commands:
        result = enhanced_agent.validate_command(cmd)
        status = "✅ Valid" if result['valid'] else "❌ Invalid"
        print(f"  {status}: {cmd}")
        if not result['valid'] and result.get('suggestions'):
            print(f"    💡 Suggestions: {result['suggestions'][:2]}")

    # Test autocompletion
    print("\n🔍 Testing Autocompletion:")
    partial_commands = ['show i', 'set int', 'ip r']
    for partial in partial_commands:
        completions = enhanced_agent.get_command_suggestions(partial)
        print(f"  '{partial}' → {completions[:3]}")

    # Test category browsing
    print("\n📂 Testing Category Browsing:")
    categories = ['interfaces', 'routing', 'ipsec']
    for cat in categories:
        commands = enhanced_agent.get_commands_by_category(cat)
        print(f"  {cat}: {len(commands)} commands")

    print("\n🎉 Enhanced agent ready!")
    print("💡 AI responses now validated against real VPP commands")

if __name__ == "__main__":
    test_enhanced_agent()