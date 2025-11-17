#!/usr/bin/env python3
"""
Consistency Check Hook (FEAT-0003)
PostToolUse hook that checks consistency with parent plan.

PURPOSE: Warn user about potential inconsistencies without blocking workflow.

Trigger: After Write/Edit operations on planning files
Action: Check for consistency issues with parent
Warning: Show warning if issues detected (non-blocking)
Checks:
  - Parent version changed (parent_version_hash mismatch)
  - Parent requires revalidation
  - Entity marked as requires-revalidation

Examples:
  ⚠️  Parent chapter version changed since scene blueprint created
  ⚠️  Parent act requires revalidation - chapter may be outdated
  ℹ️  No consistency issues detected

Integration: Uses MCP tools to check parent state
"""

import sys
import json
import os
import re
from pathlib import Path

# Import shared path parsing utilities
from planning_path_utils import extract_entity_info_from_path, is_planning_file

# MCP tool available?
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mcp-servers'))
    from planning_state_utils import (
        get_entity_state,
        STATUS_REQUIRES_REVALIDATION,
        STATUS_INVALID
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def check_consistency(entity_info: dict) -> list[str]:
    """
    Check consistency with parent plan.

    Args:
        entity_info: Dict with entity_type, entity_id, parent_type, parent_id

    Returns:
        List of warning messages (empty if no issues)
    """
    if not MCP_AVAILABLE:
        return []

    warnings = []

    try:
        # Get entity state
        entity_state = get_entity_state(entity_info['entity_type'], entity_info['entity_id'])

        if not entity_state:
            # Entity not in state yet (might be first write) - no warnings
            return []

        # Check if entity itself requires revalidation
        if entity_state['status'] == STATUS_REQUIRES_REVALIDATION:
            reason = entity_state.get('invalidation_reason', 'Unknown reason')
            warnings.append(
                f"This {entity_info['entity_type']} is marked as requires-revalidation.\n"
                f"  Reason: {reason}\n"
                f"  You should review and revalidate this plan before proceeding."
            )

        # Check if entity is invalid
        if entity_state['status'] == STATUS_INVALID:
            warnings.append(
                f"This {entity_info['entity_type']} is marked as INVALID.\n"
                f"  This plan should not be used. Consider creating a new version."
            )

        # Check parent (if exists)
        if entity_info['parent_id'] and entity_info['parent_type']:
            parent_state = get_entity_state(entity_info['parent_type'], entity_info['parent_id'])

            if not parent_state:
                warnings.append(
                    f"Parent {entity_info['parent_type']} '{entity_info['parent_id']}' not found in planning state.\n"
                    f"  This indicates state corruption. Run /rebuild-state to fix."
                )
                return warnings

            # Check parent version mismatch
            entity_parent_version = entity_state.get('parent_version_hash')
            parent_current_version = parent_state['version_hash']

            if entity_parent_version and entity_parent_version != parent_current_version:
                warnings.append(
                    f"Parent {entity_info['parent_type']} version has changed since this plan was created.\n"
                    f"  Parent version when created: {entity_parent_version[:8]}...\n"
                    f"  Parent current version: {parent_current_version[:8]}...\n"
                    f"  You should review the parent plan and update this plan accordingly."
                )

            # Check parent requires revalidation
            if parent_state['status'] == STATUS_REQUIRES_REVALIDATION:
                warnings.append(
                    f"Parent {entity_info['parent_type']} '{entity_info['parent_id']}' requires revalidation.\n"
                    f"  This child plan may be based on outdated parent information.\n"
                    f"  Consider revalidating the parent first."
                )

            # Check parent is invalid
            if parent_state['status'] == STATUS_INVALID:
                warnings.append(
                    f"Parent {entity_info['parent_type']} '{entity_info['parent_id']}' is marked as INVALID.\n"
                    f"  This child plan should probably not be developed further.\n"
                    f"  Wait for a new parent plan to be created."
                )

    except Exception as e:
        # On error, return no warnings (graceful degradation)
        pass

    return warnings


def main():
    """Hook entry point."""
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)  # Allow operation

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})

    # Only check Write/Edit operations
    if not re.match(r'^(Write|Edit)$', tool_name):
        sys.exit(0)

    file_path = tool_input.get('file_path', '')
    if not file_path:
        sys.exit(0)

    # Check if planning file
    if not is_planning_file(file_path):
        sys.exit(0)

    # Extract entity info
    entity_info = extract_entity_info_from_path(file_path)
    if not entity_info:
        sys.exit(0)

    # Check consistency
    if warnings := check_consistency(entity_info):
        # Show warnings (non-blocking)
        warning_text = "\n\n".join(f"  • {w}" for w in warnings)

        result = {
            "allow": True,
            "message": f"⚠️  CONSISTENCY CHECK: Potential issues detected\n\n"
                      f"**Entity**: {entity_info['entity_type']} '{entity_info['entity_id']}'\n\n"
                      f"**Warnings**:\n{warning_text}\n\n"
                      f"**Action**: Review these warnings and decide if updates are needed.\n"
                      f"The operation was allowed to complete, but you should address these issues."
        }

        print(json.dumps(result), flush=True)

    # Always allow operation (non-blocking hook)
    sys.exit(0)


if __name__ == "__main__":
    main()
