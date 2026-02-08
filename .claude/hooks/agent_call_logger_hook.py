#!/usr/bin/env python
"""
PostToolUse Hook: Agent Call Logger

RESPONSIBILITY: Log all Task tool (agent) calls to file for analysis

ARCHITECTURE: Non-blocking logging hook
- Captures agent name (subagent_type)
- Logs timestamp, agent name, first 500 chars of prompt
- Appends to single log file (workspace/agent-calls.log)
- Never blocks operations

TRIGGERS: After Task tool
FAILURE MODE: Graceful - logs error, never blocks
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone


def main() -> None:
    """
    PostToolUse: Log Task tool (agent) calls to file.

    Logs: timestamp, agent_name, first 500 chars of prompt
    """
    try:
        # Read event data from stdin
        event_data = json.load(sys.stdin)

        tool_name = event_data.get("tool_name", "")

        # Only process Task tool calls (agent launches)
        if tool_name != "Task":
            sys.exit(0)  # Not our concern

        # Check if tool succeeded (optional - log both success/fail)
        # tool_result = event_data.get("tool_result", {})

        # Extract agent info from tool_input
        tool_input = event_data.get("tool_input", {})

        agent_type = tool_input.get("subagent_type", "unknown")
        prompt = tool_input.get("prompt", "")
        description = tool_input.get("description", "")

        # Truncate prompt to 500 chars
        prompt_truncated = prompt[:500]
        if len(prompt) > 500:
            prompt_truncated += "..."

        # Format log entry
        timestamp = datetime.now(timezone.utc).isoformat()

        log_entry = {
            "timestamp": timestamp,
            "agent": agent_type,
            "description": description,
            "prompt_preview": prompt_truncated
        }

        # Write to log file
        log_file = Path("workspace/agent-calls.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # Feedback to stderr (visible in Claude Code)
        print(
            f"📝 [Agent Logger] {agent_type}: {description}",
            file=sys.stderr
        )

        sys.exit(0)

    except Exception as e:
        # Graceful degradation: log error but don't block
        print(
            f"⚠️ [Agent Logger] Error: {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
