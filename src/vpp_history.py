#!/usr/bin/env python3
"""
VPP Command History Database

Stores and retrieves command history for vppctl-ai sessions.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path


class VPPHistoryDatabase:
    """Database for storing VPP command history"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Use absolute path in project directory or current working directory
            import os
            # Try to find project root (where .git or setup files are)
            current_dir = os.getcwd()
            project_root = current_dir
            # Look for project root by checking for .git or common project files
            for _ in range(5):  # Check up to 5 levels up
                if os.path.exists(os.path.join(project_root, '.git')) or \
                   os.path.exists(os.path.join(project_root, 'setup.py')) or \
                   os.path.exists(os.path.join(project_root, 'pyproject.toml')):
                    break
                parent = os.path.dirname(project_root)
                if parent == project_root:  # Reached root
                    break
                project_root = parent
            
            db_path = os.path.join(project_root, "vpp_history.db")
        
        # Ensure absolute path
        self.db_path = os.path.abspath(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    output TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for fast lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON command_history(timestamp DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_session ON command_history(session_id)')
            
            conn.commit()

    def add_command(self, command: str, output: Optional[str] = None, session_id: Optional[str] = None):
        """Add a command to history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO command_history (command, output, session_id, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (command, output, session_id, datetime.now()))
            conn.commit()

    def get_recent_commands(self, limit: int = 100, session_id: Optional[str] = None, distinct: bool = True) -> List[str]:
        """Get recent commands from history
        
        Args:
            limit: Maximum number of commands to return
            session_id: Filter by session ID (None for all sessions)
            distinct: If True, return only unique commands (default). If False, return all commands in order.
        """
        with sqlite3.connect(self.db_path) as conn:
            if distinct:
                if session_id:
                    cursor = conn.execute('''
                        SELECT DISTINCT command FROM command_history
                        WHERE session_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (session_id, limit))
                else:
                    cursor = conn.execute('''
                        SELECT DISTINCT command FROM command_history
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
            else:
                # Return all commands in chronological order (for full history navigation)
                if session_id:
                    cursor = conn.execute('''
                        SELECT command FROM command_history
                        WHERE session_id = ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                    ''', (session_id, limit))
                else:
                    cursor = conn.execute('''
                        SELECT command FROM command_history
                        ORDER BY timestamp ASC
                        LIMIT ?
                    ''', (limit,))
            
            return [row[0] for row in cursor.fetchall()]

    def get_all_commands(self, session_id: Optional[str] = None) -> List[tuple]:
        """Get all commands with timestamps"""
        with sqlite3.connect(self.db_path) as conn:
            if session_id:
                cursor = conn.execute('''
                    SELECT command, output, timestamp FROM command_history
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                ''', (session_id,))
            else:
                cursor = conn.execute('''
                    SELECT command, output, timestamp FROM command_history
                    ORDER BY timestamp DESC
                ''')
            
            return cursor.fetchall()

    def clear_history(self, session_id: Optional[str] = None):
        """Clear command history"""
        with sqlite3.connect(self.db_path) as conn:
            if session_id:
                conn.execute('DELETE FROM command_history WHERE session_id = ?', (session_id,))
            else:
                conn.execute('DELETE FROM command_history')
            conn.commit()

    def get_session_id(self) -> str:
        """Generate a unique session ID"""
        import time
        return f"session_{int(time.time())}"
