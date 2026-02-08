#!/usr/bin/env python
"""
PreToolUse Hook: Integration Guard

RESPONSIBILITY: Block session commit if there are pending context integrations

ARCHITECTURE: Single-responsibility validation hook
- Checks for scenes that were generated but not integrated
- Blocks commit_session MCP call if pending integrations exist
- Provides actionable error messages with scene list
- Graceful degradation: Only blocks critical operations

TRIGGERS: Before mcp__session_management__commit_session
FAILURE MODE: Graceful - logs error, exits with code 1 to block operation
"""

import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

# Configure logging for error tracking
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
    PreToolUse validation: Ensure no pending context integrations before commit.

    Blocks commit if:
    1. integration-status.json exists
    2. Any scene has generated=true but integrated=false and skipped=false

    Allows:
    - Scenes with integrated=true (already done)
    - Scenes with skipped=true (user explicitly skipped)
    - Scenes with generated=false (not yet generated)
    """
    try:
        # Read event data from stdin
        event_data = json.load(sys.stdin)

        tool_name = event_data.get("tool_name", "")

        # Only guard commit_session
        if tool_name != "mcp__session_management__commit_session":
            sys.exit(0)  # Allow other operations

        # Check for integration-status.json
        # Look in session first (CoW), then global
        status_file = _find_integration_status()

        if not status_file:
            # No integration tracking - allow commit
            # (User might not be using FEAT-0005)
            sys.exit(0)

        # Load integration status
        try:
            with open(status_file, 'r') as f:
                status = json.load(f)
        except json.JSONDecodeError:
            # Corrupted file - warn but allow
            print(
                "⚠️ [Integration Guard] integration-status.json corrupted, skipping check",
                file=sys.stderr
            )
            sys.exit(0)

        # Check for pending integrations
        scenes = status.get("scenes", {})
        pending = []

        for scene_id, scene_status in scenes.items():
            generated = scene_status.get("generated", False)
            integrated = scene_status.get("integrated", False)
            skipped = scene_status.get("skipped", False)

            # Pending = generated but not integrated and not skipped
            if generated and not integrated and not skipped:
                pending.append(scene_id)

        if pending:
            _block_commit(pending)

        # All checks passed - allow commit
        sys.exit(0)

    except Exception as e:
        # Graceful degradation: Log error but allow operation
        # (Don't break workflow due to hook failure)
        print(
            f"⚠️ [Integration Guard] Error (non-blocking): {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)  # Exit successfully to not block workflow


def _find_integration_status() -> Path | None:
    """Find integration-status.json (session or global)."""
    # Check session first
    lock_file = Path("workspace/session.lock")
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                lock = json.load(f)
            session_name = lock.get("active")
            if session_name:
                session_status = Path(f"workspace/sessions/{session_name}/workspace/integration-status.json")
                if session_status.exists():
                    return session_status
        except Exception:
            pass

    # Fall back to global
    global_status = Path("workspace/integration-status.json")
    if global_status.exists():
        return global_status

    return None


def _block_commit(pending_scenes: list[str]):
    """Block commit with clear error message."""
    print(f"\n❌ BLOCKED: Commit has pending context integrations", file=sys.stderr)
    print(f"\nThe following scenes were generated but not integrated:", file=sys.stderr)

    for scene_id in pending_scenes[:5]:  # Show first 5
        print(f"  • Scene {scene_id}", file=sys.stderr)

    if len(pending_scenes) > 5:
        print(f"  ... and {len(pending_scenes) - 5} more", file=sys.stderr)

    print(f"\n💡 Options:", file=sys.stderr)
    print(f"   1. Integrate contexts: /integrate-context <scene_id>", file=sys.stderr)
    print(f"   2. Skip integration: Mark as skipped in integration-status.json", file=sys.stderr)
    print(f"   3. Force commit: /session commit --force", file=sys.stderr)
    print(f"\n", file=sys.stderr)

    sys.exit(1)  # Exit with error code to block operation


if __name__ == "__main__":
    main()
