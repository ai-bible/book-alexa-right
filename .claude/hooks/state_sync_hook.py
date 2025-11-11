#!/usr/bin/env python3
"""
State Sync Hook (FEAT-0003)
PostToolUse hook that syncs file changes to MCP planning state.

PURPOSE: Automatically update planning state when planning files are modified.

Trigger: After Write/Edit operations on planning files
Action: Calculate version_hash and update MCP state
Status: 'draft' for new entities, preserve existing status for updates
Graceful degradation: Warning if MCP unavailable

Examples:
  ✓ Write acts/act-1/strategic-plan.md → update_entity_state(act-1, status=draft)
  ✓ Edit chapter-02/plan.md → update_entity_state(chapter-02, preserve status)
  ✓ MCP unavailable → Show warning, allow operation

Integration: Uses MCP tools via planning_state_utils
"""

import sys
import json
import os
import re
from pathlib import Path

# Constants
TOOL_NAME_PATTERN = re.compile(r'^(Write|Edit)$')
PLANNING_FILE_PATTERNS = [
    r'acts/act-\d+/strategic-plan\.md',
    r'acts/act-\d+/chapters/chapter-\d+/plan\.md',
    r'acts/act-\d+/chapters/chapter-\d+/scenes/scene-\d+-blueprint\.md'
]

# MCP tool available?
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mcp-servers'))
    from planning_state_utils import (
        get_entity_state,
        update_entity_state,
        calculate_version_hash,
        STATUS_DRAFT
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def extract_entity_info_from_path(file_path: str) -> dict | None:
    """Extract entity type, ID, and parent from file path."""
    # Act planning
    if match := re.search(r'acts/(act-\d+)/strategic-plan\.md', file_path):
        return {
            'entity_type': 'act',
            'entity_id': match.group(1),
            'parent_id': None
        }

    # Chapter planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/plan\.md', file_path):
        return {
            'entity_type': 'chapter',
            'entity_id': match.group(2),
            'parent_id': match.group(1)
        }

    # Scene planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/scenes/(scene-\d+)-blueprint\.md', file_path):
        return {
            'entity_type': 'scene',
            'entity_id': match.group(3),
            'parent_id': match.group(2)
        }

    return None


def sync_entity_state(file_path: str, entity_info: dict) -> tuple[bool, str]:
    """
    Sync entity state to MCP after file modification.

    Args:
        file_path: Absolute path to modified file
        entity_info: Dict with entity_type, entity_id, parent_id

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not MCP_AVAILABLE:
        return False, "MCP planning state module unavailable"

    try:
        # Get absolute path
        abs_path = Path(file_path).resolve()

        if not abs_path.exists():
            return False, f"File does not exist: {file_path}"

        # Calculate version hash
        version_hash = calculate_version_hash(abs_path)

        # Check if entity already exists
        existing_state = get_entity_state(entity_info['entity_type'], entity_info['entity_id'])

        if existing_state:
            # Entity exists - preserve status
            status = existing_state['status']
            parent_version_hash = existing_state.get('parent_version_hash')
        else:
            # New entity - set to draft
            status = STATUS_DRAFT
            parent_version_hash = None

            # If has parent, get parent's version hash
            if entity_info['parent_id']:
                parent_type = 'act' if entity_info['entity_type'] == 'chapter' else 'chapter'
                parent_state = get_entity_state(parent_type, entity_info['parent_id'])
                if parent_state:
                    parent_version_hash = parent_state['version_hash']

        # Update state
        success = update_entity_state(
            entity_type=entity_info['entity_type'],
            entity_id=entity_info['entity_id'],
            status=status,
            version_hash=version_hash,
            file_path=str(abs_path),
            parent_id=entity_info['parent_id'],
            parent_version_hash=parent_version_hash
        )

        if success:
            return True, f"State updated: {entity_info['entity_id']} (status={status}, version={version_hash[:8]}...)"
        else:
            return False, f"Failed to update state for {entity_info['entity_id']}"

    except Exception as e:
        return False, f"Error syncing state: {str(e)}"


def main():
    """Hook entry point."""
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(0)  # Allow operation to proceed

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})

    # Only sync Write/Edit operations
    if not TOOL_NAME_PATTERN.match(tool_name):
        sys.exit(0)

    # Get file path from tool input
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    # Check if this is a planning file
    is_planning_file = any(
        re.search(pattern, file_path)
        for pattern in PLANNING_FILE_PATTERNS
    )

    if not is_planning_file:
        sys.exit(0)

    # Extract entity info
    entity_info = extract_entity_info_from_path(file_path)

    if not entity_info:
        sys.exit(0)

    # Sync state
    success, message = sync_entity_state(file_path, entity_info)

    if success:
        # Success - output info message
        result = {
            "allow": True,
            "message": f"✓ Planning state synced: {message}"
        }
        print(json.dumps(result), flush=True)
    else:
        # Failed - output warning but allow operation
        result = {
            "allow": True,
            "message": f"⚠️ Warning: Could not sync planning state\n\n"
                      f"**Reason**: {message}\n\n"
                      f"File was modified successfully, but state tracking failed. "
                      f"You can manually sync state using MCP tools if needed."
        }
        print(json.dumps(result), flush=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
