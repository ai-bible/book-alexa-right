#!/usr/bin/env python3
"""
Hierarchy Validation Hook (FEAT-0003)
PreToolUse hook that enforces hierarchical planning constraints.

CRITICAL RULE: Cannot plan/edit child entity if parent not approved.

Trigger: Before Write/Edit operations on planning files
Action: Block operation if parent entity status ≠ 'approved'
Bypass: Acts have no parent (always allowed)

Examples:
  ❌ BLOCK: Editing chapter-02/plan.md when act-1 status=draft
  ✅ ALLOW: Editing chapter-02/plan.md when act-1 status=approved
  ✅ ALLOW: Editing act-1/strategic-plan.md (no parent)

Integration: Works with MCP server to check parent status
"""

import sys
import json
import os
import re
from pathlib import Path

# Constants
TOOL_NAME_PATTERN = re.compile(r'^(Write|Edit)$')
PLANNING_FILE_PATTERNS = [
    r'acts/act-\d+/strategic-plan\.md',           # Act planning
    r'acts/act-\d+/chapters/chapter-\d+/plan\.md', # Chapter planning
    r'acts/act-\d+/chapters/chapter-\d+/scenes/scene-\d+-blueprint\.md'  # Scene planning
]

# MCP tool available?
try:
    # Import from sibling directory (mcp-servers)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mcp-servers'))
    from planning_state_utils import get_entity_state, STATUS_APPROVED
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def extract_entity_info_from_path(file_path: str) -> dict | None:
    """
    Extract entity type, ID, and parent from file path.

    Args:
        file_path: Path to planning file

    Returns:
        Dict with entity_type, entity_id, parent_type, parent_id or None

    Examples:
        >>> extract_entity_info_from_path('acts/act-1/strategic-plan.md')
        {'entity_type': 'act', 'entity_id': 'act-1', 'parent_type': None, 'parent_id': None}

        >>> extract_entity_info_from_path('acts/act-1/chapters/chapter-02/plan.md')
        {'entity_type': 'chapter', 'entity_id': 'chapter-02', 'parent_type': 'act', 'parent_id': 'act-1'}
    """
    # Act planning
    if match := re.search(r'acts/(act-\d+)/strategic-plan\.md', file_path):
        return {
            'entity_type': 'act',
            'entity_id': match.group(1),
            'parent_type': None,
            'parent_id': None
        }

    # Chapter planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/plan\.md', file_path):
        return {
            'entity_type': 'chapter',
            'entity_id': match.group(2),
            'parent_type': 'act',
            'parent_id': match.group(1)
        }

    # Scene planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/scenes/(scene-\d+)-blueprint\.md', file_path):
        return {
            'entity_type': 'scene',
            'entity_id': match.group(3),
            'parent_type': 'chapter',
            'parent_id': match.group(2)
        }

    return None


def check_parent_approved(parent_type: str, parent_id: str) -> tuple[bool, str]:
    """
    Check if parent entity is approved.

    Args:
        parent_type: 'act' or 'chapter'
        parent_id: Parent entity ID

    Returns:
        Tuple of (is_approved: bool, error_message: str)
    """
    if not MCP_AVAILABLE:
        # If MCP unavailable, allow (graceful degradation)
        return True, ""

    try:
        parent_state = get_entity_state(parent_type, parent_id)

        if parent_state is None:
            return False, f"Parent {parent_type} '{parent_id}' not found in planning state. " \
                         f"You must create and approve the parent plan first."

        if parent_state['status'] != STATUS_APPROVED:
            status = parent_state['status']
            return False, f"Parent {parent_type} '{parent_id}' is not approved (status: {status}). " \
                         f"You must approve the parent plan before planning children."

        return True, ""

    except Exception as e:
        # On error, allow (graceful degradation)
        print(f"Warning: Failed to check parent status: {e}", file=sys.stderr)
        return True, ""


def main():
    """Hook entry point."""
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})

    # Only validate Write/Edit operations
    if not TOOL_NAME_PATTERN.match(tool_name):
        # Allow - not a file write operation
        sys.exit(0)

    # Get file path from tool input
    file_path = tool_input.get('file_path', '')

    if not file_path:
        # No file path - allow (might be other tool)
        sys.exit(0)

    # Check if this is a planning file
    is_planning_file = any(
        re.search(pattern, file_path)
        for pattern in PLANNING_FILE_PATTERNS
    )

    if not is_planning_file:
        # Not a planning file - allow
        sys.exit(0)

    # Extract entity info
    entity_info = extract_entity_info_from_path(file_path)

    if not entity_info:
        # Couldn't parse - allow (graceful degradation)
        sys.exit(0)

    # Acts have no parent - always allow
    if entity_info['parent_type'] is None:
        sys.exit(0)

    # Check parent approved
    is_approved, error_message = check_parent_approved(
        entity_info['parent_type'],
        entity_info['parent_id']
    )

    if not is_approved:
        # BLOCK operation
        result = {
            "allow": False,
            "message": f"🚫 BLOCKED: Hierarchical planning constraint violation\n\n"
                      f"**File**: {file_path}\n"
                      f"**Entity**: {entity_info['entity_type']} '{entity_info['entity_id']}'\n"
                      f"**Parent**: {entity_info['parent_type']} '{entity_info['parent_id']}'\n\n"
                      f"**Reason**: {error_message}\n\n"
                      f"**Action Required**:\n"
                      f"  1. Approve parent plan first\n"
                      f"  2. Use MCP tool: approve_entity(entity_type='{entity_info['parent_type']}', entity_id='{entity_info['parent_id']}')\n"
                      f"  3. Then retry this operation\n\n"
                      f"**Rationale**: Hierarchical planning ensures children align with approved parent plans. "
                      f"This prevents inconsistencies and wasted work."
        }

        print(json.dumps(result), flush=True)
        sys.exit(0)

    # Parent approved - allow operation
    sys.exit(0)


if __name__ == "__main__":
    main()
