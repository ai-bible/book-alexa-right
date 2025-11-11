#!/usr/bin/env python3
"""
Invalidation Cascade Hook (FEAT-0003)
PostToolUse hook that cascades invalidation when parent plan changes.

PURPOSE: Automatically mark all descendants as requires-revalidation when parent modified.

Trigger: After Write/Edit operations on planning files
Action: Cascade invalidate all children if version_hash changed
Reason: "parent_{entity_type}_modified"
Transaction: All-or-nothing operation

Examples:
  ✓ Edit act-1/strategic-plan.md → cascade_invalidate all chapters + scenes
  ✓ Edit chapter-02/plan.md → cascade_invalidate all scenes in chapter
  ℹ️ Edit scene-0201-blueprint.md → no cascade (scenes have no children)

Integration: Uses MCP cascade_invalidate tool
"""

import sys
import json
import os
import re

# MCP tool available?
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mcp-servers'))
    from planning_state_utils import (
        get_entity_state,
        cascade_invalidate as _cascade_invalidate
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def extract_entity_info_from_path(file_path: str) -> dict | None:
    """Extract entity type and ID from file path."""
    # Act planning
    if match := re.search(r'acts/(act-\d+)/strategic-plan\.md', file_path):
        return {
            'entity_type': 'act',
            'entity_id': match.group(1)
        }

    # Chapter planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/plan\.md', file_path):
        return {
            'entity_type': 'chapter',
            'entity_id': match.group(2)
        }

    # Scene planning (no children, skip)
    if re.search(r'scenes/scene-\d+-blueprint\.md', file_path):
        return None

    return None


def should_cascade_invalidate(entity_info: dict) -> tuple[bool, str, str]:
    """
    Determine if cascade invalidation should be performed.

    Args:
        entity_info: Dict with entity_type, entity_id

    Returns:
        Tuple of (should_cascade: bool, previous_version: str, reason: str)
    """
    if not MCP_AVAILABLE:
        return False, "", "MCP unavailable"

    try:
        # Get current entity state
        entity_state = get_entity_state(entity_info['entity_type'], entity_info['entity_id'])

        if not entity_state:
            # Entity not in state yet - no cascade needed (first creation)
            return False, "", "New entity"

        # Check if version changed
        previous_version = entity_state.get('previous_version_hash')
        current_version = entity_state.get('version_hash')

        if previous_version and previous_version != current_version:
            # Version changed - cascade needed
            reason = f"parent_{entity_info['entity_type']}_modified"
            return True, previous_version, reason

        # No version change - no cascade
        return False, "", "No version change"

    except Exception as e:
        return False, "", f"Error: {str(e)}"


def perform_cascade_invalidation(entity_info: dict, reason: str) -> tuple[bool, str, int]:
    """
    Perform cascade invalidation.

    Args:
        entity_info: Dict with entity_type, entity_id
        reason: Invalidation reason

    Returns:
        Tuple of (success: bool, message: str, num_invalidated: int)
    """
    if not MCP_AVAILABLE:
        return False, "MCP unavailable", 0

    try:
        result = _cascade_invalidate(
            entity_type=entity_info['entity_type'],
            entity_id=entity_info['entity_id'],
            reason=reason
        )

        if result['success']:
            num_invalidated = len(result['invalidated_entities'])
            entity_list = ", ".join(e['entity_id'] for e in result['invalidated_entities'][:5])
            if num_invalidated > 5:
                entity_list += f", ... and {num_invalidated - 5} more"

            return True, entity_list, num_invalidated
        else:
            error = result.get('error', 'Unknown error')
            return False, error, 0

    except Exception as e:
        return False, str(e), 0


def main():
    """Hook entry point."""
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})

    # Only process Write/Edit operations
    if not re.match(r'^(Write|Edit)$', tool_name):
        sys.exit(0)

    file_path = tool_input.get('file_path', '')
    if not file_path:
        sys.exit(0)

    # Check if planning file (exclude scenes - they have no children)
    planning_patterns = [
        r'acts/act-\d+/strategic-plan\.md',
        r'acts/act-\d+/chapters/chapter-\d+/plan\.md'
    ]

    is_planning_file = any(re.search(pattern, file_path) for pattern in planning_patterns)
    if not is_planning_file:
        sys.exit(0)

    # Extract entity info
    entity_info = extract_entity_info_from_path(file_path)
    if not entity_info:
        sys.exit(0)

    # Check if cascade needed
    should_cascade, prev_version, reason = should_cascade_invalidate(entity_info)

    if not should_cascade:
        # No cascade needed
        sys.exit(0)

    # Perform cascade invalidation
    success, message, num_invalidated = perform_cascade_invalidation(entity_info, reason)

    if success:
        if num_invalidated > 0:
            # Cascade performed - inform user
            result = {
                "allow": True,
                "message": f"🔄 CASCADE INVALIDATION: Parent plan modified\n\n"
                          f"**Modified**: {entity_info['entity_type']} '{entity_info['entity_id']}'\n"
                          f"**Invalidated**: {num_invalidated} descendant(s)\n"
                          f"**Entities**: {message}\n\n"
                          f"**Reason**: {reason}\n\n"
                          f"**Next steps**:\n"
                          f"  1. Review each invalidated entity\n"
                          f"  2. Update children to align with new parent plan\n"
                          f"  3. Revalidate: approve_entity() when ready\n\n"
                          f"**Rationale**: Children are marked requires-revalidation to ensure "
                          f"they remain consistent with the updated parent plan."
            }
            print(json.dumps(result), flush=True)
        else:
            # No children to invalidate (empty cascade)
            sys.exit(0)
    else:
        # Cascade failed - warn but allow operation
        result = {
            "allow": True,
            "message": f"⚠️  Warning: Cascade invalidation failed\n\n"
                      f"**Entity**: {entity_info['entity_type']} '{entity_info['entity_id']}'\n"
                      f"**Error**: {message}\n\n"
                      f"Parent plan was modified successfully, but cascade invalidation failed. "
                      f"You may need to manually invalidate children using:\n"
                      f"  cascade_invalidate(entity_type='{entity_info['entity_type']}', entity_id='{entity_info['entity_id']}', reason='{reason}')"
        }
        print(json.dumps(result), flush=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
