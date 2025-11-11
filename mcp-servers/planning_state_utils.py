#!/usr/bin/env python3
"""
Planning State Utilities for FEAT-0003
Hierarchical Planning Workflow (Act → Chapter → Scene)

This module provides utilities for managing planning state with SQLite + JSON fallback:
- SQLite database management (init, queries, transactions)
- JSON fallback for when SQLite unavailable
- Version hash calculation (SHA-256)
- Recursive hierarchy queries (cascade invalidation)
- Sync between SQLite and JSON

Design principles:
- SQLite primary, JSON fallback
- Graceful degradation
- Transaction safety
- Performance optimized
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Tuple
from contextlib import contextmanager

# Constants
WORKSPACE_PATH = Path("workspace")
PLANNING_STATE_DB_PATH = WORKSPACE_PATH / "planning-state.db"
PLANNING_STATE_JSON_DIR = WORKSPACE_PATH / "planning-state"
SCHEMA_FILE = Path(__file__).parent / "planning_state_schema.sql"

# Entity types
ENTITY_TYPES = ["act", "chapter", "scene"]

# Status values
STATUS_DRAFT = "draft"
STATUS_APPROVED = "approved"
STATUS_REQUIRES_REVALIDATION = "requires-revalidation"
STATUS_INVALID = "invalid"

VALID_STATUSES = [STATUS_DRAFT, STATUS_APPROVED, STATUS_REQUIRES_REVALIDATION, STATUS_INVALID]


# =============================================================================
# SQLite Database Management
# =============================================================================

def _init_database() -> sqlite3.Connection:
    """
    Initialize SQLite database with schema.

    Creates database file if doesn't exist, runs schema script.

    Returns:
        sqlite3.Connection: Database connection

    Raises:
        RuntimeError: If schema file missing or database init fails
    """
    # Ensure workspace exists
    WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)

    # Check schema file exists
    if not SCHEMA_FILE.exists():
        raise RuntimeError(f"Schema file not found: {SCHEMA_FILE}")

    # Connect to database (creates if doesn't exist)
    conn = sqlite3.connect(str(PLANNING_STATE_DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name

    # Load and execute schema
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()

    return conn


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)

    Handles connection lifecycle and cleanup.
    """
    conn = None
    try:
        conn = _init_database()
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise RuntimeError(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


# =============================================================================
# Version Hash Calculation
# =============================================================================

def calculate_version_hash(file_path: str | Path) -> str:
    """
    Calculate SHA-256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        64-character hex string (SHA-256 hash)

    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If file can't be read
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        hash_obj = hashlib.sha256(content)
        return hash_obj.hexdigest()
    except Exception as e:
        raise RuntimeError(f"Failed to hash file {file_path}: {e}")


# =============================================================================
# Entity CRUD Operations
# =============================================================================

def get_entity_state(
    entity_type: str,
    entity_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[Dict[str, Any]]:
    """
    Get current state of planning entity.

    Args:
        entity_type: 'act', 'chapter', or 'scene'
        entity_id: Entity ID (e.g., 'act-1', 'chapter-02', 'scene-0204')
        conn: Optional database connection (will create if not provided)

    Returns:
        Dict with entity state or None if not found

    Example:
        >>> state = get_entity_state('chapter', 'chapter-02')
        >>> print(state['status'])  # 'approved'
    """
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of: {ENTITY_TYPES}")

    close_conn = False
    if conn is None:
        try:
            conn = _init_database()
            close_conn = True
        except Exception:
            # SQLite unavailable, try JSON fallback
            return _get_entity_state_json(entity_type, entity_id)

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                entity_type,
                entity_id,
                status,
                version_hash,
                previous_version_hash,
                file_path,
                parent_id,
                parent_version_hash,
                invalidation_reason,
                invalidated_at,
                created_at,
                updated_at,
                metadata
            FROM planning_entities
            WHERE entity_type = ? AND entity_id = ?
        """, (entity_type, entity_id))

        row = cursor.fetchone()

        if row is None:
            return None

        # Convert to dict
        state = dict(row)

        # Parse JSON metadata if present
        if state['metadata']:
            try:
                state['metadata'] = json.loads(state['metadata'])
            except json.JSONDecodeError:
                state['metadata'] = {}

        # Get children count
        cursor.execute("""
            SELECT entity_id FROM planning_entities
            WHERE parent_id = ?
        """, (entity_id,))
        children_rows = cursor.fetchall()
        state['children'] = [row['entity_id'] for row in children_rows]

        return state

    except sqlite3.Error as e:
        # Fallback to JSON
        return _get_entity_state_json(entity_type, entity_id)
    finally:
        if close_conn and conn:
            conn.close()


def update_entity_state(
    entity_type: str,
    entity_id: str,
    status: str,
    version_hash: str,
    file_path: str,
    parent_id: Optional[str] = None,
    parent_version_hash: Optional[str] = None,
    invalidation_reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    conn: Optional[sqlite3.Connection] = None
) -> bool:
    """
    Update or create entity state.

    Args:
        entity_type: 'act', 'chapter', or 'scene'
        entity_id: Entity ID
        status: 'draft', 'approved', 'requires-revalidation', 'invalid'
        version_hash: SHA-256 hash of file content
        file_path: Absolute path to planning file
        parent_id: Parent entity_id (None for acts)
        parent_version_hash: Parent's version hash when created
        invalidation_reason: Why marked requires-revalidation
        metadata: Optional metadata dict
        conn: Optional database connection

    Returns:
        True if successful

    Raises:
        ValueError: If invalid parameters
        RuntimeError: If update fails
    """
    # Validation
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"Invalid entity_type: {entity_type}")
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    now = datetime.now(timezone.utc).isoformat()

    close_conn = False
    if conn is None:
        try:
            conn = _init_database()
            close_conn = True
        except Exception:
            # SQLite unavailable, use JSON fallback
            return _update_entity_state_json(
                entity_type, entity_id, status, version_hash,
                file_path, parent_id, parent_version_hash,
                invalidation_reason, metadata
            )

    try:
        cursor = conn.cursor()

        # Check if entity exists
        cursor.execute("""
            SELECT version_hash FROM planning_entities
            WHERE entity_type = ? AND entity_id = ?
        """, (entity_type, entity_id))
        existing = cursor.fetchone()

        if existing:
            # Update existing
            previous_hash = existing['version_hash']

            cursor.execute("""
                UPDATE planning_entities
                SET
                    status = ?,
                    version_hash = ?,
                    previous_version_hash = ?,
                    file_path = ?,
                    parent_id = ?,
                    parent_version_hash = ?,
                    invalidation_reason = ?,
                    invalidated_at = CASE WHEN ? = 'requires-revalidation' THEN ? ELSE invalidated_at END,
                    updated_at = ?,
                    metadata = ?
                WHERE entity_type = ? AND entity_id = ?
            """, (
                status,
                version_hash,
                previous_hash,
                file_path,
                parent_id,
                parent_version_hash,
                invalidation_reason,
                status,  # For CASE check
                now,     # Set invalidated_at if status is requires-revalidation
                now,     # updated_at
                json.dumps(metadata) if metadata else None,
                entity_type,
                entity_id
            ))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO planning_entities (
                    entity_type, entity_id, status, version_hash, previous_version_hash,
                    file_path, parent_id, parent_version_hash, invalidation_reason,
                    invalidated_at, created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_type,
                entity_id,
                status,
                version_hash,
                None,  # previous_version_hash (new entity)
                file_path,
                parent_id,
                parent_version_hash,
                invalidation_reason,
                now if status == STATUS_REQUIRES_REVALIDATION else None,
                now,  # created_at
                now,  # updated_at
                json.dumps(metadata) if metadata else None
            ))

        conn.commit()
        return True

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        # Fallback to JSON
        return _update_entity_state_json(
            entity_type, entity_id, status, version_hash,
            file_path, parent_id, parent_version_hash,
            invalidation_reason, metadata
        )
    finally:
        if close_conn and conn:
            conn.close()


# =============================================================================
# Hierarchy and Cascade Operations
# =============================================================================

def get_all_descendants(
    entity_type: str,
    entity_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Get all descendants of an entity (recursive).

    Uses recursive CTE for efficient traversal.

    Args:
        entity_type: Entity type
        entity_id: Entity ID
        conn: Optional database connection

    Returns:
        List of descendant entities (dicts)

    Example:
        >>> descendants = get_all_descendants('chapter', 'chapter-02')
        >>> print(len(descendants))  # 5 scenes
    """
    close_conn = False
    if conn is None:
        try:
            conn = _init_database()
            close_conn = True
        except Exception:
            # SQLite unavailable, JSON fallback
            return _get_all_descendants_json(entity_type, entity_id)

    try:
        cursor = conn.cursor()

        # Recursive CTE to get all descendants
        cursor.execute("""
            WITH RECURSIVE descendants AS (
                -- Base case: entity itself
                SELECT
                    entity_type, entity_id, status, version_hash, parent_id, file_path
                FROM planning_entities
                WHERE entity_type = ? AND entity_id = ?

                UNION ALL

                -- Recursive case: all children
                SELECT
                    e.entity_type, e.entity_id, e.status, e.version_hash, e.parent_id, e.file_path
                FROM planning_entities e
                INNER JOIN descendants d ON e.parent_id = d.entity_id
            )
            SELECT * FROM descendants
            WHERE NOT (entity_type = ? AND entity_id = ?)
        """, (entity_type, entity_id, entity_type, entity_id))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except sqlite3.Error:
        return _get_all_descendants_json(entity_type, entity_id)
    finally:
        if close_conn and conn:
            conn.close()


def cascade_invalidate(
    entity_type: str,
    entity_id: str,
    reason: str,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Mark entity and all descendants as requires-revalidation.

    Transaction-based: all-or-nothing.

    Args:
        entity_type: Entity type
        entity_id: Entity ID
        reason: Invalidation reason
        conn: Optional database connection

    Returns:
        Dict with:
            - success: bool
            - invalidated_entities: List of invalidated entities
            - error: Optional error message

    Example:
        >>> result = cascade_invalidate('chapter', 'chapter-02', 'parent_chapter_regenerated')
        >>> print(len(result['invalidated_entities']))  # 5 scenes
    """
    close_conn = False
    if conn is None:
        try:
            conn = _init_database()
            close_conn = True
        except Exception:
            # SQLite unavailable, JSON fallback
            return _cascade_invalidate_json(entity_type, entity_id, reason)

    try:
        # Get all descendants
        descendants = get_all_descendants(entity_type, entity_id, conn)

        if not descendants:
            return {
                "success": True,
                "invalidated_entities": []
            }

        # Start transaction
        cursor = conn.cursor()
        invalidated = []
        now = datetime.now(timezone.utc).isoformat()

        for desc in descendants:
            prev_status = desc['status']

            # Skip if already invalid or requires-revalidation
            if prev_status in [STATUS_INVALID, STATUS_REQUIRES_REVALIDATION]:
                continue

            # Update status
            cursor.execute("""
                UPDATE planning_entities
                SET
                    status = ?,
                    invalidation_reason = ?,
                    invalidated_at = ?,
                    updated_at = ?
                WHERE entity_type = ? AND entity_id = ?
            """, (
                STATUS_REQUIRES_REVALIDATION,
                reason,
                now,
                now,
                desc['entity_type'],
                desc['entity_id']
            ))

            invalidated.append({
                "entity_type": desc['entity_type'],
                "entity_id": desc['entity_id'],
                "previous_status": prev_status,
                "new_status": STATUS_REQUIRES_REVALIDATION
            })

        # Commit transaction
        conn.commit()

        return {
            "success": True,
            "invalidated_entities": invalidated
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {
            "success": False,
            "invalidated_entities": [],
            "error": str(e)
        }
    finally:
        if close_conn and conn:
            conn.close()


def get_children_status(
    entity_type: str,
    entity_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Get status summary of all children for an entity.

    Args:
        entity_type: 'act' or 'chapter' (scenes have no children)
        entity_id: Entity ID
        conn: Optional database connection

    Returns:
        Dict with:
            - total_children: int
            - status_counts: Dict[status -> count]
            - children: List of child entities with status

    Example:
        >>> summary = get_children_status('chapter', 'chapter-02')
        >>> print(summary['status_counts'])  # {'approved': 3, 'requires-revalidation': 2}
    """
    if entity_type not in ['act', 'chapter']:
        raise ValueError("Only acts and chapters have children")

    close_conn = False
    if conn is None:
        try:
            conn = _init_database()
            close_conn = True
        except Exception:
            return _get_children_status_json(entity_type, entity_id)

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT entity_type, entity_id, status, file_path
            FROM planning_entities
            WHERE parent_id = ?
            ORDER BY entity_id
        """, (entity_id,))

        rows = cursor.fetchall()
        children = [dict(row) for row in rows]

        # Count by status
        status_counts = {}
        for child in children:
            status = child['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_children": len(children),
            "status_counts": status_counts,
            "children": children
        }

    except sqlite3.Error:
        return _get_children_status_json(entity_type, entity_id)
    finally:
        if close_conn and conn:
            conn.close()


# =============================================================================
# JSON Fallback Functions
# =============================================================================

def _get_json_file_path(entity_type: str, entity_id: str) -> Path:
    """Get path to JSON state file for entity."""
    json_dir = PLANNING_STATE_JSON_DIR / f"{entity_type}s"
    json_dir.mkdir(parents=True, exist_ok=True)
    return json_dir / f"{entity_id}.json"


def _get_entity_state_json(entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
    """Get entity state from JSON file (fallback)."""
    json_path = _get_json_file_path(entity_type, entity_id)

    if not json_path.exists():
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        return state
    except Exception:
        return None


def _update_entity_state_json(
    entity_type: str,
    entity_id: str,
    status: str,
    version_hash: str,
    file_path: str,
    parent_id: Optional[str],
    parent_version_hash: Optional[str],
    invalidation_reason: Optional[str],
    metadata: Optional[Dict[str, Any]]
) -> bool:
    """Update entity state in JSON file (fallback)."""
    json_path = _get_json_file_path(entity_type, entity_id)
    now = datetime.now(timezone.utc).isoformat()

    # Load existing if present
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            previous_hash = state.get('version_hash')
        except Exception:
            previous_hash = None
    else:
        previous_hash = None

    # Build state
    state = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "status": status,
        "version_hash": version_hash,
        "previous_version_hash": previous_hash,
        "file_path": file_path,
        "parent_id": parent_id,
        "parent_version_hash": parent_version_hash,
        "invalidation_reason": invalidation_reason,
        "invalidated_at": now if status == STATUS_REQUIRES_REVALIDATION else None,
        "created_at": state.get('created_at', now) if json_path.exists() else now,
        "updated_at": now,
        "metadata": metadata or {}
    }

    # Write to file
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _get_all_descendants_json(entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
    """Get all descendants from JSON files (fallback) - recursive."""
    descendants = []

    # Determine child type
    if entity_type == 'act':
        child_type = 'chapter'
    elif entity_type == 'chapter':
        child_type = 'scene'
    else:
        return []  # Scenes have no children

    # Scan JSON files for children
    json_dir = PLANNING_STATE_JSON_DIR / f"{child_type}s"
    if not json_dir.exists():
        return []

    for json_file in json_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            if state.get('parent_id') == entity_id:
                descendants.append(state)
                # Recursively get descendants of this child
                child_descendants = _get_all_descendants_json(
                    state['entity_type'],
                    state['entity_id']
                )
                descendants.extend(child_descendants)
        except Exception:
            continue

    return descendants


def _cascade_invalidate_json(entity_type: str, entity_id: str, reason: str) -> Dict[str, Any]:
    """Cascade invalidate using JSON files (fallback)."""
    descendants = _get_all_descendants_json(entity_type, entity_id)
    invalidated = []

    for desc in descendants:
        prev_status = desc['status']

        if prev_status in [STATUS_INVALID, STATUS_REQUIRES_REVALIDATION]:
            continue

        # Update JSON file
        success = _update_entity_state_json(
            desc['entity_type'],
            desc['entity_id'],
            STATUS_REQUIRES_REVALIDATION,
            desc['version_hash'],
            desc['file_path'],
            desc.get('parent_id'),
            desc.get('parent_version_hash'),
            reason,
            desc.get('metadata')
        )

        if success:
            invalidated.append({
                "entity_type": desc['entity_type'],
                "entity_id": desc['entity_id'],
                "previous_status": prev_status,
                "new_status": STATUS_REQUIRES_REVALIDATION
            })

    return {
        "success": True,
        "invalidated_entities": invalidated
    }


def _get_children_status_json(entity_type: str, entity_id: str) -> Dict[str, Any]:
    """Get children status from JSON files (fallback)."""
    # Determine child type
    if entity_type == 'act':
        child_type = 'chapter'
    elif entity_type == 'chapter':
        child_type = 'scene'
    else:
        return {"total_children": 0, "status_counts": {}, "children": []}

    # Scan JSON files
    json_dir = PLANNING_STATE_JSON_DIR / f"{child_type}s"
    if not json_dir.exists():
        return {"total_children": 0, "status_counts": {}, "children": []}

    children = []
    status_counts = {}

    for json_file in json_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            if state.get('parent_id') == entity_id:
                children.append(state)
                status = state['status']
                status_counts[status] = status_counts.get(status, 0) + 1
        except Exception:
            continue

    return {
        "total_children": len(children),
        "status_counts": status_counts,
        "children": children
    }


# =============================================================================
# Sync Operations
# =============================================================================

def sync_from_json_to_sqlite() -> Dict[str, Any]:
    """
    Sync planning state from JSON files to SQLite on startup.

    Scans all JSON files and inserts/updates SQLite database.

    Returns:
        Dict with:
            - success: bool
            - entities_synced: int
            - errors: List of errors
    """
    try:
        conn = _init_database()
    except Exception as e:
        return {
            "success": False,
            "entities_synced": 0,
            "errors": [f"Failed to initialize database: {e}"]
        }

    entities_synced = 0
    errors = []

    try:
        for entity_type in ENTITY_TYPES:
            json_dir = PLANNING_STATE_JSON_DIR / f"{entity_type}s"
            if not json_dir.exists():
                continue

            for json_file in json_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)

                    # Insert or update in SQLite
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO planning_entities (
                            entity_type, entity_id, status, version_hash, previous_version_hash,
                            file_path, parent_id, parent_version_hash, invalidation_reason,
                            invalidated_at, created_at, updated_at, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        state['entity_type'],
                        state['entity_id'],
                        state['status'],
                        state['version_hash'],
                        state.get('previous_version_hash'),
                        state['file_path'],
                        state.get('parent_id'),
                        state.get('parent_version_hash'),
                        state.get('invalidation_reason'),
                        state.get('invalidated_at'),
                        state.get('created_at', datetime.now(timezone.utc).isoformat()),
                        state.get('updated_at', datetime.now(timezone.utc).isoformat()),
                        json.dumps(state.get('metadata', {}))
                    ))

                    entities_synced += 1

                except Exception as e:
                    errors.append(f"Failed to sync {json_file}: {e}")

        conn.commit()

        return {
            "success": True,
            "entities_synced": entities_synced,
            "errors": errors
        }

    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "entities_synced": entities_synced,
            "errors": errors + [f"Transaction failed: {e}"]
        }
    finally:
        conn.close()


def sync_from_sqlite_to_json() -> Dict[str, Any]:
    """
    Sync planning state from SQLite to JSON files.

    Dumps all entities from SQLite to individual JSON files.

    Returns:
        Dict with:
            - success: bool
            - entities_synced: int
            - errors: List of errors
    """
    try:
        conn = _init_database()
    except Exception as e:
        return {
            "success": False,
            "entities_synced": 0,
            "errors": [f"Failed to initialize database: {e}"]
        }

    entities_synced = 0
    errors = []

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM planning_entities")
        rows = cursor.fetchall()

        for row in rows:
            state = dict(row)

            # Parse metadata JSON
            if state['metadata']:
                try:
                    state['metadata'] = json.loads(state['metadata'])
                except json.JSONDecodeError:
                    state['metadata'] = {}

            # Write to JSON file
            json_path = _get_json_file_path(state['entity_type'], state['entity_id'])
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                entities_synced += 1
            except Exception as e:
                errors.append(f"Failed to write {json_path}: {e}")

        return {
            "success": True,
            "entities_synced": entities_synced,
            "errors": errors
        }

    except Exception as e:
        return {
            "success": False,
            "entities_synced": entities_synced,
            "errors": errors + [f"Failed to read from SQLite: {e}"]
        }
    finally:
        conn.close()
