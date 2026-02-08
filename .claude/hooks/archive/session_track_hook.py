#!/usr/bin/env python
"""
PostToolUse Hook: Session File Change Tracker

RESPONSIBILITY: Auto-track file changes in session CoW system

ARCHITECTURE: Non-blocking automation hook
- Calls track_file_change MCP tool after Write/Edit/NotebookEdit
- Extracts relative path from absolute session path
- Determines change_type (created vs modified)
- Provides observability feedback to AI

TRIGGERS: After Write, Edit, NotebookEdit (successful)
FAILURE MODE: Graceful - logs warning, allows operation to complete
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone

# Add path for importing session utilities
from pathlib import Path as PathLib
mcp_servers_path = str(PathLib(__file__).parent.parent.parent / "mcp-servers")
if mcp_servers_path not in sys.path:
    sys.path.insert(0, mcp_servers_path)

from session_utils import _add_cow_file


def main() -> None:
    """
    PostToolUse: Auto-track file writes in active session.

    Reads tool event from stdin, extracts file path,
    and updates session tracking via direct session.json update.
    """
    try:
        # Read event data from stdin
        event_data = json.load(sys.stdin)

        tool_name = event_data.get("tool_name", "")

        # Only process write operations
        write_tools = ["Write", "Edit", "NotebookEdit"]
        if tool_name not in write_tools:
            sys.exit(0)  # Not our concern

        # Check if tool succeeded
        tool_result = event_data.get("tool_result", {})
        if tool_result.get("is_error", False):
            sys.exit(0)  # Failed write, nothing to track

        # Get file path from tool input
        tool_input = event_data.get("tool_input", {})
        file_path_str = tool_input.get("file_path", "")

        if not file_path_str:
            sys.exit(0)  # No file path

        file_path = Path(file_path_str)

        # Check for active session
        lock_file = Path("workspace/session.lock")
        if not lock_file.exists():
            sys.exit(0)  # No session, no tracking needed

        try:
            with open(lock_file, 'r') as f:
                lock = json.load(f)
        except Exception:
            sys.exit(0)  # Corrupted lock

        session_name = lock.get("active")
        if not session_name:
            sys.exit(0)  # No active session

        # Get session path
        session_path = Path(f"workspace/sessions/{session_name}")
        if not session_path.exists():
            sys.exit(0)  # Session directory missing

        # Check if file is within session directory
        try:
            file_path_resolved = file_path.resolve()
            session_path_resolved = session_path.resolve()

            if not str(file_path_resolved).startswith(str(session_path_resolved)):
                sys.exit(0)  # File not in session directory (global file)
        except Exception:
            sys.exit(0)  # Path resolution failed

        # Calculate relative path
        try:
            rel_path = file_path_resolved.relative_to(session_path_resolved)
            rel_path_str = str(rel_path.as_posix())  # Cross-platform
        except ValueError:
            sys.exit(0)  # Not relative to session

        # Determine change type by checking if already tracked
        change_type = "modified"  # Default assumption

        # Check session.json to see if file already tracked
        session_file = session_path / "session.json"
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # If file not in cow_files, it's being created
            is_tracked = any(
                cow["path"] == rel_path_str
                for cow in session_data.get("cow_files", [])
            )
            if not is_tracked:
                change_type = "created"
        except Exception:
            pass  # On error, keep default "modified"

        # Update session.json via utility function
        try:
            _add_cow_file(session_name, rel_path_str, change_type)
        except Exception as e:
            print(f"⚠️ [Session Track] Failed to track via utility: {e}", file=sys.stderr)
            sys.exit(0)

        # Show feedback to AI
        print(
            f"✅ [Session Track] Auto-tracked: {rel_path_str} ({change_type})",
            file=sys.stderr
        )

        sys.exit(0)  # Success

    except Exception as e:
        # Graceful degradation: Log error but don't block
        print(
            f"⚠️ [Session Track] Error (non-blocking): {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)  # Always exit 0 to not block operation


if __name__ == "__main__":
    main()
