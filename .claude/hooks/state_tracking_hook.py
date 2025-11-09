#!/usr/bin/env python3
"""
PostToolUse Hook: State Tracking Guarantee Layer

This hook runs AFTER every tool call to ensure state files are being updated
during generation workflows. It acts as a safety net to catch missed MCP calls.

Hook Type: PostToolUse
Trigger: After any tool call
Mode: Non-blocking (observability, not enforcement)
"""

import sys
import json
import glob
from pathlib import Path
from datetime import datetime, timezone, timedelta


def main():
    """
    Check if state files are being updated during generation workflows.

    This hook provides observability - it warns when state might not be tracked,
    but never blocks workflow execution (graceful degradation).
    """
    try:
        # Read event data from stdin
        event_data = json.load(sys.stdin)

        # Extract tool information
        tool_name = event_data.get("tool_name", "")
        tool_input = event_data.get("tool_input", {})

        # Only monitor Task tool with generation-related agents
        if tool_name != "Task":
            sys.exit(0)  # Not relevant, skip silently

        # Check if this is a generation-related agent
        subagent_type = tool_input.get("subagent_type", "")
        generation_agents = [
            "generation-coordinator",
            "blueprint-validator",
            "prose-writer",
            "blueprint-compliance-fast-checker",
            "validation-aggregator"
        ]

        if not any(agent in subagent_type for agent in generation_agents):
            sys.exit(0)  # Not a generation agent, skip

        # Extract scene_id from prompt if possible (best effort)
        prompt = tool_input.get("prompt", "")
        scene_id = _extract_scene_id(prompt)

        if not scene_id:
            # Can't determine scene_id, skip check
            sys.exit(0)

        # Check if corresponding state file was updated recently
        state_file = Path(f"workspace/generation-state-{scene_id}.json")

        if not state_file.exists():
            # State file doesn't exist yet - might be legitimate if this is start_generation
            # Don't warn on first tool call
            sys.exit(0)

        # Check last modification time
        modified_time = datetime.fromtimestamp(state_file.stat().st_mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        seconds_since_update = (now - modified_time).total_seconds()

        # Warning threshold: 10 seconds
        if seconds_since_update > 10:
            # State file hasn't been updated recently
            print(
                f"⚠️ [State Tracking Hook] WARNING: State file for scene {scene_id} "
                f"not updated in {seconds_since_update:.1f}s",
                file=sys.stderr
            )
            print(
                f"   Agent: {subagent_type}",
                file=sys.stderr
            )
            print(
                f"   Last update: {modified_time.isoformat()}",
                file=sys.stderr
            )
            print(
                f"   💡 Check if MCP tools are being called correctly",
                file=sys.stderr
            )

        # Always exit successfully (non-blocking mode)
        sys.exit(0)

    except Exception as e:
        # Graceful degradation: Log error but don't block
        print(
            f"⚠️ [State Tracking Hook] Error (non-blocking): {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)  # Exit successfully to not block workflow


def _extract_scene_id(text: str) -> str:
    """
    Best-effort extraction of scene_id from text.

    Looks for patterns like:
    - "scene 0204"
    - "scene_id='0204'"
    - "scene-0204"

    Args:
        text: Text to search

    Returns:
        Scene ID if found, empty string otherwise
    """
    import re

    # Pattern: 4 digits that look like scene ID
    patterns = [
        r'scene[_\s-]+(\d{4})',  # scene 0204, scene_0204, scene-0204
        r'scene_id[=:\'"\s]+(\d{4})',  # scene_id='0204'
        r'(\d{4})-blueprint',  # 0204-blueprint
    ]

    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1)

    return ""


if __name__ == "__main__":
    main()
