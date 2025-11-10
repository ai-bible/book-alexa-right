#!/usr/bin/env python3
"""
PostToolUse Hook: Path Interceptor

RESPONSIBILITY: Guide AI to use correct paths (session vs global)

ARCHITECTURE: Observability hook (non-blocking)
- Shows AI which paths are active (session or global)
- Displays CoW status for transparency
- Helps AI understand file resolution
- Never blocks operations

TRIGGERS: After Read, Write, Edit, Glob operations
FAILURE MODE: Graceful - errors logged, never blocks
"""

import sys
import json
from pathlib import Path
from typing import Optional


def _print_file_status(header: str, details: dict[str, Optional[str]]) -> None:
    """
    Print file status information to stderr in consistent format.

    Args:
        header: Header line (e.g., "💡 [CoW Active] Reading from session: file.txt")
        details: Dictionary of detail lines to print
                Keys become labels, None values are printed as-is
    """
    print(f"\n{header}", file=sys.stderr)
    for key, value in details.items():
        if value is None:
            # Print key as-is (for lines without labels)
            print(f"   {key}", file=sys.stderr)
        else:
            print(f"   {key}: {value}", file=sys.stderr)


def main():
    """
    PostToolUse observability: Show AI path resolution info.

    Displays to AI:
    - Active session name
    - Whether files are in session (modified) or global (original)
    - CoW status for transparency

    Never blocks - purely informational.
    """
    try:
        # Read event data from stdin
        event_data = json.load(sys.stdin)

        tool_name = event_data.get("tool_name", "")

        # Only monitor file operations
        file_tools = ["Read", "Write", "Edit", "Glob"]
        if tool_name not in file_tools:
            sys.exit(0)

        # Check if session active
        lock_file = Path("workspace/session.lock")
        if not lock_file.exists():
            # No session - no guidance needed
            sys.exit(0)

        # Load session info
        try:
            with open(lock_file, 'r') as f:
                lock = json.load(f)
        except Exception:
            sys.exit(0)  # Skip on error

        session_name = lock.get("active")
        if not session_name:
            sys.exit(0)

        session_path = Path(f"workspace/sessions/{session_name}")
        if not session_path.exists():
            sys.exit(0)

        # Extract file path from tool input (best effort)
        tool_input = event_data.get("tool_input", {})
        file_path = tool_input.get("file_path") or tool_input.get("path")

        if not file_path:
            # No specific file path - show general session info
            _print_file_status(
                f"💡 [Active Session] All file operations use session: {session_name}",
                {"Session path": f"workspace/sessions/{session_name}/"}
            )
            sys.exit(0)

        # Check file location (session vs global)
        session_file = session_path / file_path
        global_file = Path(file_path)

        # Check when both files exist (session takes precedence)
        if session_file.exists() and global_file.exists():
            # File exists in both locations - session file takes precedence
            _print_file_status(
                f"💡 [CoW Active] Reading from session: {file_path}",
                {
                    "Source": f"workspace/sessions/{session_name}/{file_path}",
                    "Status": "Modified in session (CoW copy)",
                    "Note": "Global file is shadowed - session version takes precedence"
                }
            )
        elif session_file.exists():
            # File exists only in session (modified via CoW)
            _print_file_status(
                f"💡 [CoW Active] Reading from session: {file_path}",
                {
                    "Source": f"workspace/sessions/{session_name}/{file_path}",
                    "Status": "Modified in session (CoW copy)"
                }
            )
        elif global_file.exists():
            # File not in session, reading from global
            details = {
                "Source": file_path,
                "Status": "Not yet modified in session"
            }
            # If this is a Write operation, CoW will trigger
            if tool_name in ["Write", "Edit"]:
                details["⚡ CoW will trigger"] = "File will be copied to session on write"

            _print_file_status(
                f"💡 [Global] Reading from global: {file_path}",
                details
            )
        elif tool_name in ["Write", "Edit"]:
            # New file (doesn't exist anywhere)
            _print_file_status(
                f"✨ [New File] Creating in session: {file_path}",
                {"Destination": f"workspace/sessions/{session_name}/{file_path}"}
            )

        # Always exit successfully (non-blocking)
        sys.exit(0)

    except Exception as e:
        # Graceful degradation: Log error but don't block
        print(
            f"⚠️ [Path Interceptor] Error (non-blocking): {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
