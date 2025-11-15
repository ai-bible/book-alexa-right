#!/usr/bin/env python3
"""
Unit tests for Planning State utilities (FEAT-0003)

Tests cover:
- SQLite database initialization and schema
- Version hash calculation
- Entity CRUD operations
- Hierarchy queries and cascade operations
- JSON fallback mechanisms
- Sync operations between SQLite and JSON

Run with: pytest test_planning_state.py -v
"""

import pytest
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from planning_state_utils import (
    calculate_version_hash,
    get_entity_state,
    update_entity_state,
    get_all_descendants,
    cascade_invalidate,
    get_children_status,
    sync_from_json_to_sqlite,
    sync_from_sqlite_to_json,
    WORKSPACE_PATH,
    PLANNING_STATE_DB_PATH,
    PLANNING_STATE_JSON_DIR,
    STATUS_DRAFT,
    STATUS_APPROVED,
    STATUS_REQUIRES_REVALIDATION
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_workspace(monkeypatch):
    """Create temporary workspace for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_workspace_path = Path(temp_dir) / "workspace"
    temp_workspace_path.mkdir(parents=True, exist_ok=True)

    # Monkey patch workspace paths
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace_path)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace_path / "planning-state.db")
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_JSON_DIR', temp_workspace_path / "planning-state")

    yield temp_workspace_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_plan_file(temp_workspace):
    """Create a sample plan file for hash testing."""
    plan_file = temp_workspace / "test-plan.md"
    content = """# Chapter 02 Plan

## Objective
Introduce main character to the vertical city structure.

## Scenes
- Scene 0201: Character arrives at city
- Scene 0202: First encounter with time cascades
"""
    plan_file.write_text(content, encoding='utf-8')
    return plan_file


# =============================================================================
# Tests: Version Hash Calculation
# =============================================================================

def test_calculate_version_hash_success(sample_plan_file):
    """Test that hash calculation works and returns 64-char hex string."""
    hash_value = calculate_version_hash(sample_plan_file)

    assert len(hash_value) == 64  # SHA-256 is 64 hex chars
    assert all(c in '0123456789abcdef' for c in hash_value)


def test_calculate_version_hash_deterministic(sample_plan_file):
    """Test that same file produces same hash."""
    hash1 = calculate_version_hash(sample_plan_file)
    hash2 = calculate_version_hash(sample_plan_file)

    assert hash1 == hash2


def test_calculate_version_hash_different_content(temp_workspace):
    """Test that different files produce different hashes."""
    file1 = temp_workspace / "file1.md"
    file2 = temp_workspace / "file2.md"

    file1.write_text("Content A", encoding='utf-8')
    file2.write_text("Content B", encoding='utf-8')

    hash1 = calculate_version_hash(file1)
    hash2 = calculate_version_hash(file2)

    assert hash1 != hash2


def test_calculate_version_hash_file_not_found():
    """Test that FileNotFoundError is raised for missing file."""
    with pytest.raises(FileNotFoundError):
        calculate_version_hash("/nonexistent/file.md")


# =============================================================================
# Tests: Entity CRUD Operations
# =============================================================================

def test_update_and_get_entity_state_sqlite(temp_workspace, monkeypatch, sample_plan_file):
    """Test creating and retrieving entity state via SQLite."""
    # Patch workspace paths
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")

    # Create entity
    version_hash = calculate_version_hash(sample_plan_file)

    success = update_entity_state(
        entity_type='chapter',
        entity_id='chapter-02',
        status=STATUS_DRAFT,
        version_hash=version_hash,
        file_path=str(sample_plan_file),
        parent_id='act-1',
        metadata={'word_count': 250}
    )

    assert success is True

    # Retrieve entity
    state = get_entity_state('chapter', 'chapter-02')

    assert state is not None
    assert state['entity_id'] == 'chapter-02'
    assert state['status'] == STATUS_DRAFT
    assert state['version_hash'] == version_hash
    assert state['parent_id'] == 'act-1'
    assert state['metadata']['word_count'] == 250


def test_get_entity_state_not_found(temp_workspace, monkeypatch):
    """Test that None is returned for non-existent entity."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")

    state = get_entity_state('chapter', 'nonexistent')

    assert state is None


def test_update_entity_state_idempotent(temp_workspace, monkeypatch, sample_plan_file):
    """Test that updating same entity twice works (idempotent)."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")

    version_hash = calculate_version_hash(sample_plan_file)

    # First update
    success1 = update_entity_state(
        entity_type='chapter',
        entity_id='chapter-02',
        status=STATUS_DRAFT,
        version_hash=version_hash,
        file_path=str(sample_plan_file),
        parent_id='act-1'
    )

    # Second update (should update, not error)
    success2 = update_entity_state(
        entity_type='chapter',
        entity_id='chapter-02',
        status=STATUS_APPROVED,
        version_hash=version_hash,
        file_path=str(sample_plan_file),
        parent_id='act-1'
    )

    assert success1 is True
    assert success2 is True

    # Check final state
    state = get_entity_state('chapter', 'chapter-02')
    assert state['status'] == STATUS_APPROVED
    assert state['previous_version_hash'] == version_hash  # Previous should be set


# =============================================================================
# Tests: Hierarchy Operations
# =============================================================================

def test_get_all_descendants(temp_workspace, monkeypatch, sample_plan_file):
    """Test recursive descendant retrieval."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")

    version_hash = calculate_version_hash(sample_plan_file)

    # Create hierarchy: chapter-02 -> scene-0201, scene-0202
    update_entity_state('chapter', 'chapter-02', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='act-1')

    update_entity_state('scene', 'scene-0201', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='chapter-02')

    update_entity_state('scene', 'scene-0202', STATUS_DRAFT, version_hash,
                        str(sample_plan_file), parent_id='chapter-02')

    # Get descendants
    descendants = get_all_descendants('chapter', 'chapter-02')

    assert len(descendants) == 2
    descendant_ids = [d['entity_id'] for d in descendants]
    assert 'scene-0201' in descendant_ids
    assert 'scene-0202' in descendant_ids


def test_cascade_invalidate(temp_workspace, monkeypatch, sample_plan_file):
    """Test cascade invalidation marks all descendants as requires-revalidation."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")

    version_hash = calculate_version_hash(sample_plan_file)

    # Create hierarchy with approved scenes
    update_entity_state('chapter', 'chapter-02', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='act-1')

    update_entity_state('scene', 'scene-0201', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='chapter-02')

    update_entity_state('scene', 'scene-0202', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='chapter-02')

    # Cascade invalidate
    result = cascade_invalidate('chapter', 'chapter-02', 'parent_chapter_regenerated')

    assert result['success'] is True
    assert len(result['invalidated_entities']) == 2

    # Check scenes are now requires-revalidation
    scene1 = get_entity_state('scene', 'scene-0201')
    scene2 = get_entity_state('scene', 'scene-0202')

    assert scene1['status'] == STATUS_REQUIRES_REVALIDATION
    assert scene2['status'] == STATUS_REQUIRES_REVALIDATION
    assert scene1['invalidation_reason'] == 'parent_chapter_regenerated'
    assert scene2['invalidation_reason'] == 'parent_chapter_regenerated'


def test_get_children_status(temp_workspace, monkeypatch, sample_plan_file):
    """Test children status summary."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")

    version_hash = calculate_version_hash(sample_plan_file)

    # Create chapter with mixed-status scenes
    update_entity_state('chapter', 'chapter-02', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='act-1')

    update_entity_state('scene', 'scene-0201', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='chapter-02')

    update_entity_state('scene', 'scene-0202', STATUS_DRAFT, version_hash,
                        str(sample_plan_file), parent_id='chapter-02')

    update_entity_state('scene', 'scene-0203', STATUS_REQUIRES_REVALIDATION, version_hash,
                        str(sample_plan_file), parent_id='chapter-02',
                        invalidation_reason='test')

    # Get children status
    result = get_children_status('chapter', 'chapter-02')

    assert result['total_children'] == 3
    assert result['status_counts'][STATUS_APPROVED] == 1
    assert result['status_counts'][STATUS_DRAFT] == 1
    assert result['status_counts'][STATUS_REQUIRES_REVALIDATION] == 1


# =============================================================================
# Tests: JSON Fallback
# =============================================================================

def test_json_fallback_update_and_get(temp_workspace, monkeypatch, sample_plan_file):
    """Test that JSON fallback works when SQLite unavailable."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_JSON_DIR', temp_workspace / "planning-state")

    # Create bad DB path to force JSON fallback
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', Path("/invalid/path/db.sqlite"))

    version_hash = calculate_version_hash(sample_plan_file)

    # Update should use JSON fallback
    success = update_entity_state(
        entity_type='scene',
        entity_id='scene-0201',
        status=STATUS_DRAFT,
        version_hash=version_hash,
        file_path=str(sample_plan_file),
        parent_id='chapter-02'
    )

    assert success is True

    # Get should also use JSON fallback
    state = get_entity_state('scene', 'scene-0201')

    assert state is not None
    assert state['entity_id'] == 'scene-0201'
    assert state['status'] == STATUS_DRAFT
    assert state['version_hash'] == version_hash


# =============================================================================
# Tests: Sync Operations
# =============================================================================

def test_sync_from_json_to_sqlite(temp_workspace, monkeypatch, sample_plan_file):
    """Test syncing planning state from JSON files to SQLite."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_JSON_DIR', temp_workspace / "planning-state")

    version_hash = calculate_version_hash(sample_plan_file)

    # Create JSON files manually
    json_dir = temp_workspace / "planning-state" / "chapters"
    json_dir.mkdir(parents=True, exist_ok=True)

    json_file = json_dir / "chapter-02.json"
    json_data = {
        "entity_type": "chapter",
        "entity_id": "chapter-02",
        "status": STATUS_DRAFT,
        "version_hash": version_hash,
        "file_path": str(sample_plan_file),
        "parent_id": "act-1",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "metadata": {}
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f)

    # Sync to SQLite
    result = sync_from_json_to_sqlite()

    assert result['success'] is True
    assert result['entities_synced'] == 1

    # Verify entity in SQLite
    state = get_entity_state('chapter', 'chapter-02')
    assert state is not None
    assert state['entity_id'] == 'chapter-02'


def test_sync_from_sqlite_to_json(temp_workspace, monkeypatch, sample_plan_file):
    """Test syncing planning state from SQLite to JSON files."""
    monkeypatch.setattr('planning_state_utils.WORKSPACE_PATH', temp_workspace)
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_DB_PATH', temp_workspace / "planning-state.db")
    monkeypatch.setattr('planning_state_utils.PLANNING_STATE_JSON_DIR', temp_workspace / "planning-state")

    version_hash = calculate_version_hash(sample_plan_file)

    # Create entity in SQLite
    update_entity_state('scene', 'scene-0201', STATUS_APPROVED, version_hash,
                        str(sample_plan_file), parent_id='chapter-02')

    # Sync to JSON
    result = sync_from_sqlite_to_json()

    assert result['success'] is True
    assert result['entities_synced'] == 1

    # Verify JSON file exists
    json_file = temp_workspace / "planning-state" / "scenes" / "scene-0201.json"
    assert json_file.exists()

    # Verify content
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data['entity_id'] == 'scene-0201'
    assert data['status'] == STATUS_APPROVED


# =============================================================================
# Tests: Validation
# =============================================================================

def test_update_entity_invalid_type():
    """Test that invalid entity_type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid entity_type"):
        update_entity_state(
            entity_type='invalid',
            entity_id='test',
            status=STATUS_DRAFT,
            version_hash='a' * 64,
            file_path='/test'
        )


def test_update_entity_invalid_status():
    """Test that invalid status raises ValueError."""
    with pytest.raises(ValueError, match="Invalid status"):
        update_entity_state(
            entity_type='scene',
            entity_id='test',
            status='invalid_status',
            version_hash='a' * 64,
            file_path='/test'
        )


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
