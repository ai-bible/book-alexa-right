#!/usr/bin/env python3
"""
Shared Utilities for Planning File Path Parsing

This module provides common path parsing functions used by multiple hooks
to ensure consistent entity extraction logic across the system.
"""

import re
from typing import Dict, Optional


# Planning file path patterns
PLANNING_FILE_PATTERNS = [
    r'acts/act-\d+/strategic-plan\.md',
    r'acts/act-\d+/chapters/chapter-\d+/plan\.md',
    r'acts/act-\d+/chapters/chapter-\d+/scenes/scene-\d+-blueprint\.md'
]


def is_planning_file(file_path: str) -> bool:
    """
    Check if file path matches any planning file pattern.

    Args:
        file_path: File path to check

    Returns:
        True if path matches planning file pattern, False otherwise

    Examples:
        >>> is_planning_file('acts/act-1/strategic-plan.md')
        True
        >>> is_planning_file('some/other/file.md')
        False
    """
    return any(re.search(pattern, file_path) for pattern in PLANNING_FILE_PATTERNS)


def extract_entity_info_from_path(file_path: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Extract entity type, ID, and parent information from file path.

    This is the canonical path parsing function used across all hooks
    to ensure consistent entity extraction logic.

    Args:
        file_path: Path to planning file

    Returns:
        Dict with entity_type, entity_id, parent_type, parent_id or None if not a planning file

    Examples:
        >>> extract_entity_info_from_path('acts/act-1/strategic-plan.md')
        {'entity_type': 'act', 'entity_id': 'act-1', 'parent_type': None, 'parent_id': None}

        >>> extract_entity_info_from_path('acts/act-1/chapters/chapter-02/plan.md')
        {'entity_type': 'chapter', 'entity_id': 'chapter-02', 'parent_type': 'act', 'parent_id': 'act-1'}

        >>> extract_entity_info_from_path('acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md')
        {'entity_type': 'scene', 'entity_id': 'scene-0204', 'parent_type': 'chapter', 'parent_id': 'chapter-02'}
    """
    # Act planning
    if match := re.search(r'acts/(act-\d+)/strategic-plan\.md', file_path):
        return {
            'entity_type': 'act',
            'entity_id': match[1],
            'parent_type': None,
            'parent_id': None
        }

    # Chapter planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/plan\.md', file_path):
        return {
            'entity_type': 'chapter',
            'entity_id': match[2],
            'parent_type': 'act',
            'parent_id': match[1]
        }

    # Scene planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/scenes/(scene-\d+)-blueprint\.md', file_path):
        return {
            'entity_type': 'scene',
            'entity_id': match[3],
            'parent_type': 'chapter',
            'parent_id': match[2]
        }

    return None


def extract_entity_info_for_cascade(file_path: str) -> Optional[Dict[str, str]]:
    """
    Extract entity info for cascade invalidation (only acts and chapters).

    Scenes are leaf nodes and don't trigger cascades, so they return None.

    Args:
        file_path: Path to planning file

    Returns:
        Dict with entity_type and entity_id for acts/chapters, None for scenes or non-planning files

    Examples:
        >>> extract_entity_info_for_cascade('acts/act-1/strategic-plan.md')
        {'entity_type': 'act', 'entity_id': 'act-1'}

        >>> extract_entity_info_for_cascade('acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md')
        None  # Scenes don't cascade
    """
    # Act planning
    if match := re.search(r'acts/(act-\d+)/strategic-plan\.md', file_path):
        return {
            'entity_type': 'act',
            'entity_id': match[1]
        }

    # Chapter planning
    if match := re.search(r'acts/(act-\d+)/chapters/(chapter-\d+)/plan\.md', file_path):
        return {
            'entity_type': 'chapter',
            'entity_id': match[2]
        }

    # Scene planning (no children, skip cascade)
    if re.search(r'scenes/scene-\d+-blueprint\.md', file_path):
        return None

    return None
