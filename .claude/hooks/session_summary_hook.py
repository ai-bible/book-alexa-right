#!/usr/bin/env python3
"""
Stop Hook: Session Summary

RESPONSIBILITY: Show active session summary on conversation end

ARCHITECTURE: Observability hook (conversation cleanup)
- Displays active session status when Claude Code stops
- Reminds user to commit or cancel
- Shows uncommitted changes count
- Lists human retries
- Never blocks

TRIGGERS: When conversation ends (Stop event)
FAILURE MODE: Graceful - errors logged, never affects shutdown
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone


def main():
    """
    Stop event handler: Show session summary.

    Displays:
    - Active session name and status
    - Uncommitted changes count
    - Human retries count
    - Actionable next steps (commit/cancel)

    Never blocks conversation end.
    """
    try:
        # Check for session.lock
        lock_file = Path("workspace/session.lock")

        if not lock_file.exists():
            # No active session - nothing to show
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

        # Load session.json
        session_file = session_path / "session.json"
        if not session_file.exists():
            sys.exit(0)

        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
        except Exception:
            sys.exit(0)

        # Extract session info
        status = session_data.get("status", "UNKNOWN")
        created_at = session_data.get("created_at", "unknown")
        description = session_data.get("description", "")

        changes = session_data.get("changes", {})
        modified_count = len(changes.get("modified", []))
        created_count = len(changes.get("created", []))
        deleted_count = len(changes.get("deleted", []))

        human_retries = session_data.get("human_retries", [])
        retry_count = len(human_retries)

        stats = session_data.get("stats", {})
        session_size = stats.get("session_size_bytes", 0)

        # Format created time
        try:
            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            elapsed = now - created_dt
            elapsed_str = _format_elapsed(elapsed.total_seconds())
        except Exception:
            elapsed_str = "unknown"

        # Print summary
        print("\n" + "="*60, file=sys.stderr)
        print("📂 ACTIVE SESSION", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print(f"\nSession: {session_name}", file=sys.stderr)
        print(f"Status: {status}", file=sys.stderr)
        print(f"Created: {elapsed_str} ago", file=sys.stderr)

        if description:
            print(f"Description: {description}", file=sys.stderr)

        print(f"\nUncommitted changes:", file=sys.stderr)
        print(f"  • Modified: {modified_count} files", file=sys.stderr)
        print(f"  • Created: {created_count} files", file=sys.stderr)
        if deleted_count > 0:
            print(f"  • Deleted: {deleted_count} files", file=sys.stderr)

        if retry_count > 0:
            print(f"\nHuman retries: {retry_count}", file=sys.stderr)
            # Show last 2 retries
            for retry in human_retries[-2:]:
                file_name = retry.get("file", "unknown")
                reason = retry.get("reason", "")[:50]
                print(f"  • {file_name}: {reason}...", file=sys.stderr)

        print(f"\nSession size: {_format_size(session_size)}", file=sys.stderr)

        print("\n💡 Don't forget to:", file=sys.stderr)
        print("  - Commit changes: /session commit", file=sys.stderr)
        print("  - Or cancel: /session cancel", file=sys.stderr)

        print("\n" + "="*60 + "\n", file=sys.stderr)

        # Always exit successfully
        sys.exit(0)

    except Exception as e:
        # Graceful degradation: Log error but don't block shutdown
        print(
            f"⚠️ [Session Summary] Error (non-blocking): {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)


def _format_elapsed(seconds: float) -> str:
    """Format elapsed time in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


if __name__ == "__main__":
    main()
