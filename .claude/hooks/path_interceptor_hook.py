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
            print(
                f"\n💡 [Active Session] All file operations use session: {session_name}",
                file=sys.stderr
            )
            print(
                f"   Session path: workspace/sessions/{session_name}/",
                file=sys.stderr
            )
            sys.exit(0)

        # Check file location (session vs global)
        session_file = session_path / file_path
        global_file = Path(file_path)

        # Comment 7: Clarify when both files exist (session takes precedence)
        if session_file.exists() and global_file.exists():
            # File exists in both locations - session file takes precedence
            print(
                f"\n💡 [CoW Active] Reading from session: {file_path}",
                file=sys.stderr
            )
            print(
                f"   Source: workspace/sessions/{session_name}/{file_path}",
                file=sys.stderr
            )
            print(
                "   Status: Modified in session (CoW copy)",
                file=sys.stderr
            )
            print(
                "   Note: Global file is shadowed - session version takes precedence",
                file=sys.stderr
            )
        elif session_file.exists():
            # File exists only in session (modified via CoW)
            print(
                f"\n💡 [CoW Active] Reading from session: {file_path}",
                file=sys.stderr
            )
            print(
                f"   Source: workspace/sessions/{session_name}/{file_path}",
                file=sys.stderr
            )
            print(
                "   Status: Modified in session (CoW copy)",
                file=sys.stderr
            )
        elif global_file.exists():
            # File not in session, reading from global
            print(
                f"\n💡 [Global] Reading from global: {file_path}",
                file=sys.stderr
            )
            print(
                f"   Source: {file_path}",
                file=sys.stderr
            )
            print(
                "   Status: Not yet modified in session",
                file=sys.stderr
            )

            # If this is a Write operation, CoW will trigger
            if tool_name in ["Write", "Edit"]:
                print(
                    "   ⚡ CoW will trigger: File will be copied to session on write",
                    file=sys.stderr
                )
        # Comment 8: merge else-if into elif
        elif tool_name in ["Write", "Edit"]:
            # New file (doesn't exist anywhere)
            print(
                f"\n✨ [New File] Creating in session: {file_path}",
                file=sys.stderr
            )
            print(
                f"   Destination: workspace/sessions/{session_name}/{file_path}",
                file=sys.stderr
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
