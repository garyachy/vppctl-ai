#!/usr/bin/env python3
"""
VPP CLI Command Parser and Database Builder

Parses VPP source code to extract CLI commands and builds a database
for AI hallucination prevention and autocompletion.
"""

import os
import re
import json
import sqlite3
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class VPPCommand:
    """Represents a parsed VPP CLI command"""
    path: str
    short_help: str
    function_name: str
    file_path: str
    category: str = ""

class VPPCLIParser:
    """Parser for VPP CLI commands from source code"""

    def __init__(self, vpp_src_path: str = None):
        self.vpp_src_path = Path(vpp_src_path)
        self.commands: List[VPPCommand] = []

    def parse_all_commands(self) -> List[VPPCommand]:
        """Parse all CLI commands from VPP source code"""
        print("🔍 Scanning VPP source code for CLI commands...")

        # Find all C files
        c_files = list(self.vpp_src_path.rglob("*.c"))

        for c_file in c_files:
            try:
                commands = self._parse_file(str(c_file))
                self.commands.extend(commands)
            except Exception as e:
                print(f"⚠️  Error parsing {c_file}: {e}")

        print(f"✅ Found {len(self.commands)} CLI commands")
        return self.commands

    def _parse_file(self, file_path: str) -> List[VPPCommand]:
        """Parse CLI commands from a single C file"""
        commands = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip files with encoding issues
            return commands

        # Find VLIB_CLI_COMMAND blocks
        # Pattern: VLIB_CLI_COMMAND (command_name, static) = {\n  .path = "command",\n  .short_help = "help",\n  .function = func,\n};
        pattern = r'VLIB_CLI_COMMAND\s*\(\s*([^,]+)\s*,\s*[^)]+\)\s*=\s*\{[^}]*\.path\s*=\s*"([^"]+)"[^}]*\.short_help\s*=\s*"([^"]*)"[^}]*\.function\s*=\s*([^,\s}]+)'

        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            command_name, path, short_help, function_name = match
            commands.append(VPPCommand(
                path=path.strip(),
                short_help=short_help.strip(),
                function_name=function_name.strip(),
                file_path=file_path,
                category=self._categorize_command(path)
            ))

        return commands

    def _categorize_command(self, path: str) -> str:
        """Categorize a command based on its path"""
        path_lower = path.lower()

        if path_lower.startswith('show'):
            if 'interface' in path_lower:
                return 'interfaces'
            elif 'ip' in path_lower and 'fib' in path_lower:
                return 'routing'
            elif 'ipsec' in path_lower:
                return 'ipsec'
            elif 'version' in path_lower or 'build' in path_lower:
                return 'system'
            else:
                return 'show'
        elif path_lower.startswith('set'):
            if 'interface' in path_lower:
                return 'interfaces'
            else:
                return 'configuration'
        elif path_lower.startswith('create'):
            return 'configuration'
        elif path_lower.startswith('delete'):
            return 'configuration'
        elif path_lower.startswith('ip route'):
            return 'routing'
        elif path_lower.startswith('lcp'):
            return 'lcp'
        else:
            return 'other'

class VPPCommandDatabase:
    """Database for storing and querying VPP CLI commands"""

    def __init__(self, db_path: str = "vpp_commands.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    short_help TEXT,
                    function_name TEXT,
                    file_path TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes for fast lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_path ON commands(path)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_category ON commands(category)')

    def save_commands(self, commands: List[VPPCommand]):
        """Save commands to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany('''
                INSERT OR REPLACE INTO commands (path, short_help, function_name, file_path, category)
                VALUES (?, ?, ?, ?, ?)
            ''', [(cmd.path, cmd.short_help, cmd.function_name, cmd.file_path, cmd.category) for cmd in commands])

        print(f"💾 Saved {len(commands)} commands to database")

    def search_commands(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for commands matching query"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT path, short_help, category FROM commands
                WHERE path LIKE ? OR short_help LIKE ?
                ORDER BY path
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))

            return [{'path': row[0], 'help': row[1], 'category': row[2]} for row in cursor.fetchall()]

    def get_commands_by_category(self, category: str) -> List[Dict]:
        """Get all commands in a category"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT path, short_help FROM commands WHERE category = ? ORDER BY path', (category,))
            return [{'path': row[0], 'help': row[1]} for row in cursor.fetchall()]

    def validate_command(self, command: str) -> Dict:
        """Check if a command exists and return details"""
        command = command.strip()
        if not command:
            return {'valid': False, 'suggestions': [], 'reason': 'Empty command'}
        
        # Handle commands with placeholders - extract base command structure
        # Replace placeholders like <interface_name> with a placeholder token
        command_with_placeholders = re.sub(r'<[^>]+>', '<placeholder>', command)
        command_base = command_with_placeholders.split('<placeholder>')[0].strip()
        
        # First try exact match
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT path, short_help, category FROM commands WHERE path = ?', (command,))
            row = cursor.fetchone()

            if row:
                return {'valid': True, 'path': row[0], 'help': row[1], 'category': row[2]}

        # For commands with placeholders, check if the base structure exists
        if '<placeholder>' in command_with_placeholders or '<' in command:
            # Check if the base command (without placeholder) exists
            if command_base:
                # Extract the command structure: "trace add" from "trace add <interface> 10"
                cmd_parts = command_base.split()
                if len(cmd_parts) >= 2:
                    # Check if the exact base command exists (e.g., "trace add filter" but not "trace add <interface>")
                    base_cmd = ' '.join(cmd_parts[:2])  # First two words
                    with sqlite3.connect(self.db_path) as conn:
                        # Look for commands that start with the base
                        cursor = conn.execute(
                            'SELECT path, short_help, category FROM commands WHERE path LIKE ? ORDER BY path',
                            (f'{base_cmd}%',)
                        )
                        matches = cursor.fetchall()
                        if matches:
                            # Check if any match is an exact structural match
                            # "trace add filter" matches "trace add <interface>" structure? No - different word count
                            cmd_word_count = len(command.split())
                            for match in matches:
                                match_word_count = len(match[0].split())
                                # Only consider valid if word count is very close (same structure)
                                if match[0].startswith(base_cmd) and abs(match_word_count - cmd_word_count) <= 1:
                                    # Additional check: make sure it's not just a prefix match
                                    # "trace add filter" should NOT match "trace add <interface> 10"
                                    if match_word_count == cmd_word_count or (match_word_count == cmd_word_count - 1):
                                        return {'valid': True, 'path': match[0], 'help': match[1], 'category': match[2], 'similar': True}
                        # If no exact structural match, it's invalid
                        return {'valid': False, 'suggestions': [m[0] for m in matches[:3]], 'reason': 'Command structure with placeholder not found in database'}

        # Try fuzzy matching for common variations
        command_normalized = self._normalize_command(command)
        with sqlite3.connect(self.db_path) as conn:
            # Try with normalized command
            cursor = conn.execute('SELECT path, short_help, category FROM commands WHERE path = ?', (command_normalized,))
            row = cursor.fetchone()

            if row:
                return {'valid': True, 'path': row[0], 'help': row[1], 'category': row[2], 'normalized': True}

            # Try partial matches (but be more strict)
            if command.split():  # Only if command has words
                # Only match if the first word matches exactly
                first_word = command.split()[0]
                cursor = conn.execute('SELECT path, short_help, category FROM commands WHERE path LIKE ? ORDER BY path',
                                    (f'{first_word}%',))
                partial_matches = cursor.fetchall()
            else:
                partial_matches = []

            if partial_matches:
                # Check if any partial match is very similar (stricter check)
                for match in partial_matches:
                    if self._commands_similar(command, match[0]):
                        # Additional check: make sure it's not just matching the first word
                        match_words = match[0].split()
                        cmd_words = command.split()
                        if len(match_words) >= len(cmd_words) - 1:  # Allow one word difference
                            return {'valid': True, 'path': match[0], 'help': match[1], 'category': match[2], 'similar': True}

        return {'valid': False, 'suggestions': self._find_similar_commands(command)}

    def _find_similar_commands(self, command: str, limit: int = 5) -> List[str]:
        """Find similar commands for suggestions"""
        words = command.lower().split()
        suggestions = []

        with sqlite3.connect(self.db_path) as conn:
            for word in words:
                if len(word) > 2:  # Skip very short words
                    cursor = conn.execute('''
                        SELECT path FROM commands
                        WHERE path LIKE ?
                        ORDER BY path
                        LIMIT ?
                    ''', (f'%{word}%', limit))
                    suggestions.extend([row[0] for row in cursor.fetchall()])

        # Remove duplicates and limit
        return list(dict.fromkeys(suggestions))[:limit]

    def _normalize_command(self, command: str) -> str:
        """Normalize command for better matching"""
        # Handle common plural/singular variations
        normalizations = {
            'interfaces': 'interface',
            'routes': 'route',
            'tunnels': 'tunnel',
            'policies': 'policy',
            'associations': 'association',
            'addresses': 'address'
        }

        words = command.split()
        if len(words) >= 2:
            # Check if the second word needs normalization
            if words[1] in normalizations:
                words[1] = normalizations[words[1]]
                return ' '.join(words)
            # Also check if we have a partial match (e.g., "tunnels" -> "tun")
            for plural, singular in normalizations.items():
                if plural.startswith(words[1]) or words[1].startswith(plural[:len(words[1])]):
                    words[1] = singular
                    return ' '.join(words)

        return command

    def _commands_similar(self, cmd1: str, cmd2: str) -> bool:
        """Check if two commands are very similar"""
        words1 = cmd1.lower().split()
        words2 = cmd2.lower().split()

        # Exact match
        if words1 == words2:
            return True

        # Check if one is substring of the other
        cmd1_str = ' '.join(words1)
        cmd2_str = ' '.join(words2)

        if cmd1_str in cmd2_str or cmd2_str in cmd1_str:
            return True

        # Check word overlap
        intersection = set(words1).intersection(set(words2))
        union = set(words1).union(set(words2))

        # More lenient similarity - 50% overlap instead of 70%
        similarity = len(intersection) / len(union) if union else 0

        return similarity > 0.5

    def get_command_completions(self, partial_command: str) -> List[str]:
        """Get command completions for autocompletion"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT path FROM commands WHERE path LIKE ? ORDER BY path LIMIT 20',
                                (f'{partial_command}%',))
            return [row[0] for row in cursor.fetchall()]

class VPPCommandValidator:
    """Validates AI-generated commands against the database"""

    # Known hallucinations - commands that are commonly suggested but don't exist or are wrong
    KNOWN_HALLUCINATIONS = {
        # Trace commands with wrong syntax
        r'trace add <interface[^>]*>': {
            'correct': 'trace add <input-graph-node>',
            'reason': 'trace add requires input-graph-node, not interface name'
        },
        r'trace add <interface_name>': {
            'correct': 'trace add <input-graph-node>',
            'reason': 'trace add requires input-graph-node, not interface name'
        },
        r'trace add.*interface': {
            'correct': 'trace add <input-graph-node>',
            'reason': 'trace add requires input-graph-node, not interface name'
        },
        # Show trace with wrong parameters
        r'show trace max <number': {
            'correct': 'show trace [max COUNT]',
            'reason': 'show trace max takes COUNT directly, not <number_of_packets>'
        },
        r'show trace detail': {
            'correct': 'show trace [max COUNT]',
            'reason': 'show trace does not have a "detail" option'
        },
    }

    def __init__(self, db: VPPCommandDatabase):
        self.db = db

    def _check_known_hallucination(self, command: str) -> Optional[Dict]:
        """Check if a command matches a known hallucination pattern"""
        for pattern, info in self.KNOWN_HALLUCINATIONS.items():
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    'is_hallucination': True,
                    'pattern': pattern,
                    'correct': info['correct'],
                    'reason': info['reason']
                }
        return None

    def validate_ai_response(self, ai_response: str) -> Dict:
        """
        Validate AI response for potential hallucinations

        Returns:
            {
                'valid_commands': [...],
                'invalid_commands': [...],
                'suggestions': {...},
                'known_hallucinations': {...}
            }
        """
        # Extract potential VPP commands from AI response
        potential_commands = self._extract_commands_from_text(ai_response)

        valid_commands = []
        invalid_commands = []
        suggestions = {}
        known_hallucinations = {}

        for cmd in potential_commands:
            # First check for known hallucinations
            hallucination_check = self._check_known_hallucination(cmd)
            if hallucination_check:
                invalid_commands.append(cmd)
                known_hallucinations[cmd] = hallucination_check
                suggestions[cmd] = [hallucination_check['correct']]
                continue
            
            # Then check against database
            result = self.db.validate_command(cmd)
            if result['valid']:
                valid_commands.append(cmd)
            else:
                invalid_commands.append(cmd)
                if result['suggestions']:
                    suggestions[cmd] = result['suggestions']

        return {
            'valid_commands': valid_commands,
            'invalid_commands': invalid_commands,
            'suggestions': suggestions,
            'known_hallucinations': known_hallucinations,
            'confidence': len(valid_commands) / len(potential_commands) if potential_commands else 1.0
        }

    def _extract_commands_from_text(self, text: str) -> List[str]:
        """Extract potential VPP commands from text"""
        commands = []

        # Look for backtick-enclosed commands (most reliable)
        backtick_commands = re.findall(r'`([^`]+)`', text)
        for cmd in backtick_commands:
            cmd = cmd.strip()
            # Remove vppctl prefix if present
            if cmd.startswith('vppctl '):
                cmd = cmd[7:].strip()
            if cmd and len(cmd.split()) >= 1:  # At least one word
                commands.append(cmd)

        # Look for numbered list items that look like commands
        lines = text.split('\n')
        for line in lines:
            line = line.strip()

            # Look for numbered items like "1. command" or "- command"
            # Include trace, pcap, and other common VPP command prefixes
            if re.match(r'^[\d\.\-\*]\s*(show|set|create|delete|ip|lcp|trace|pcap|clear|save)', line.lower()):
                # Extract the command part
                parts = re.split(r'^[\d\.\-\*]\s*', line)
                if len(parts) > 1:
                    cmd_part = parts[1].strip()
                    # Remove vppctl prefix if present
                    if cmd_part.startswith('vppctl '):
                        cmd_part = cmd_part[7:].strip()
                    # Take only the command part (before any description)
                    cmd = cmd_part.split(' - ')[0].split(' to ')[0].split(' for ')[0].split(' This ')[0].strip()
                    # Remove placeholder patterns like <interface_name> but keep the base command
                    cmd_base = re.sub(r'<[^>]+>', '<placeholder>', cmd)
                    if cmd_base and len(cmd_base.split()) >= 1:
                        commands.append(cmd_base)

        # Look for standalone command patterns
        for line in lines:
            line = line.strip()
            # Simple pattern: word starting with common VPP verbs
            if (line.startswith(('show ', 'set ', 'create ', 'delete ', 'ip ', 'lcp ')) and
                len(line.split()) >= 2 and
                not any(word in line.lower() for word in ['the', 'this', 'these', 'command', 'use'])):
                cmd = line.split()[0] + ' ' + line.split()[1]  # Take first two words
                commands.append(cmd)

        # Remove duplicates and clean up
        seen = set()
        unique_commands = []
        for cmd in commands:
            cmd = cmd.strip()
            if cmd and cmd not in seen and len(cmd.split()) >= 1:
                seen.add(cmd)
                unique_commands.append(cmd)

        return unique_commands

def build_vpp_command_database():
    """Build the complete VPP command database"""
    print("🚀 Building VPP Command Database")
    print("=" * 50)

    # Parse commands
    parser = VPPCLIParser()
    commands = parser.parse_all_commands()

    # Save to database
    db = VPPCommandDatabase()
    db.save_commands(commands)

    # Show statistics
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.execute('SELECT category, COUNT(*) FROM commands GROUP BY category ORDER BY COUNT(*) DESC')
        print("\n📊 Command Categories:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} commands")

    print(f"\n✅ Database built successfully with {len(commands)} commands!")
    print(f"📁 Database saved to: {db.db_path}")

    return db

if __name__ == "__main__":
    # Build the database
    db = build_vpp_command_database()

    # Test some queries
    print("\n🧪 Testing Database:")
    print("Search 'show interface':", len(db.search_commands('show interface')))
    print("Category 'interfaces':", len(db.get_commands_by_category('interfaces')))
    print("Validate 'show version':", db.validate_command('show version')['valid'])
    print("Completions for 'show i':", db.get_command_completions('show i')[:3])