#!/usr/bin/env python3
"""
PreToolUse Hook: Session Guard

RESPONSIBILITY: Block file operations if no active session exists

ARCHITECTURE: Single-responsibility validation hook
- Checks for active session before Write/Edit operations
- Detects crashed sessions (stale lock)
- Provides actionable error messages
- Graceful degradation: Only blocks critical operations

TRIGGERS: Before Write, Edit, NotebookEdit
FAILURE MODE: Graceful - logs error, exits with code 1 to block operation
"""

import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

# Configure logging for error tracking (Comment 6)
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workspace/hooks-errors.log', mode='a'),
        logging.StreamHandler(sys.stderr)
    ]
)


def main():
    """
    PreToolUse validation: Ensure active session exists for file writes.

    Blocks operations if:
    1. No active session (session.lock missing)
    2. Session is CRASHED (process died)
    3. Session directory doesn't exist

    Graceful degradation: Only blocks critical write operations.
    """
    try:
        # Read event data from stdin
        event_data = json.load(sys.stdin)

        tool_name = event_data.get("tool_name", "")

        # Only guard write operations
        write_tools = ["Write", "Edit", "NotebookEdit"]
        if tool_name not in write_tools:
            sys.exit(0)  # Allow reads, other operations

        # Check for session.lock
        lock_file = Path("workspace/session.lock")

        if not lock_file.exists():
            _block_operation(
                "No active session",
                "Start session first: /session start <name>"
            )

        # Load session.lock
        try:
            with open(lock_file, 'r') as f:
                lock = json.load(f)
        except json.JSONDecodeError:
            _block_operation(
                "Corrupted session.lock",
                "Delete workspace/session.lock and start new session"
            )

        session_name = lock.get("active")
        if not session_name:
            _block_operation(
                "No active session in lock file",
                "Start session: /session start <name>"
            )

        # Check session directory exists
        session_dir = Path(f"workspace/sessions/{session_name}")
        if not session_dir.exists():
            _block_operation(
                f"Session directory not found: {session_name}",
                f"Session may be corrupted. Cancel it: /session cancel {session_name}"
            )

        # Check if session is CRASHED (process died)
        lock_pid = lock.get("pid")
        if lock_pid and not _is_process_alive(lock_pid):
            _mark_crashed(session_name)
            _block_operation(
                f"Session '{session_name}' process died (CRASHED)",
                f"Resume or cancel: /session cancel {session_name}"
            )

        # All checks passed - allow operation
        sys.exit(0)

    except Exception as e:
        # Graceful degradation: Log error but allow operation
        # (Don't break workflow due to hook failure)
        print(
            f"⚠️ [Session Guard] Error (non-blocking): {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)  # Exit successfully to not block workflow


def _block_operation(reason: str, suggestion: str):
    """Block operation with clear error message."""
    print(f"\n❌ BLOCKED BY SESSION GUARD", file=sys.stderr)
    print(f"\nReason: {reason}", file=sys.stderr)
    print(f"💡 {suggestion}\n", file=sys.stderr)
    sys.exit(1)  # Exit with error code to block operation


def _is_process_alive(pid: int) -> bool:
    """Check if process with PID is alive."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _mark_crashed(session_name: str):
    """Mark session as CRASHED in session.json (Comment 6: with logging)."""
    try:
        session_file = Path(f"workspace/sessions/{session_name}/session.json")
        if session_file.exists():
            with open(session_file, 'r') as f:
                session_data = json.load(f)

            session_data["status"] = "CRASHED"
            session_data["crashed_at"] = datetime.now(timezone.utc).isoformat()

            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
    except Exception as e:
        # Best effort - log error but don't fail hook (Comment 6)
        logging.error(f"Failed to mark session '{session_name}' as crashed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
