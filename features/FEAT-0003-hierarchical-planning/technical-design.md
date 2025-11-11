# FEAT-0003: Hierarchical Planning Workflow - Technical Design

**Version**: 1.0.0
**Created**: 2025-11-11
**Status**: Technical Design Complete
**Author**: Agent-Architect

---

## Executive Summary

This document defines the complete technical architecture for implementing hierarchical planning (Act → Chapter → Scene) with MCP-based state tracking and hooks-based enforcement.

**Key Architectural Decisions:**
1. **Extend FEAT-0002 MCP Server** with planning state capabilities (unified state management)
2. **Four new hooks** for hierarchy validation, consistency checking, invalidation cascade, and state sync
3. **Agent context injection** via prompt preprocessing (maintains isolation)
4. **Separate commands** `/plan-act`, `/plan-chapter`, `/plan-scene` (explicit hierarchy)
5. **Deep cascade invalidation** with transaction-like semantics (all-or-nothing)
6. **SHA-256 content hashing** for version management (deterministic, git-independent)
7. **SQLite storage** for state with JSON file fallback (performance + reliability)

---

## 1. MCP Server Architecture

### 1.1 Decision: Extend FEAT-0002 Server

**Rationale:**
- FEAT-0002 `generation-state-tracker` already handles workflow state management
- Planning and generation are two phases of the same system (Integration Workflow)
- Unified state tracking simplifies observability and debugging
- Single MCP server reduces complexity and resource usage

**Architecture:**
```
generation-state-tracker (extended)
├── Generation State Management (existing)
│   ├── Tools: resume_generation, get_generation_status, etc.
│   └── Resources: state://generation/{scene_id}
│
└── Planning State Management (NEW)
    ├── Tools: get_entity_state, update_entity_state, get_hierarchy_tree, etc.
    ├── Resources: state://planning/{type}/{id}
    └── Storage: SQLite DB with JSON fallback
```

### 1.2 Extended MCP Server Specification

**New Name:** `planning-and-generation-state-tracker` (or keep `generation-state-tracker` with extended scope)

#### 1.2.1 New Tools

```typescript
// Tool 1: Get entity state
{
  "name": "get_entity_state",
  "description": "Get current state of a planning entity (act/chapter/scene)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_type": {
        "type": "string",
        "enum": ["act", "chapter", "scene"],
        "description": "Type of entity"
      },
      "entity_id": {
        "type": "string",
        "description": "Entity ID (e.g., 'act-1', 'chapter-02', 'scene-0204')"
      }
    },
    "required": ["entity_type", "entity_id"]
  },
  "returns": {
    "type": "object",
    "properties": {
      "entity_id": {"type": "string"},
      "entity_type": {"type": "string"},
      "status": {
        "type": "string",
        "enum": ["draft", "approved", "requires-revalidation", "invalid"]
      },
      "version_hash": {"type": "string"},
      "parent_id": {"type": "string", "nullable": true},
      "parent_version_hash": {"type": "string", "nullable": true},
      "children": {
        "type": "array",
        "items": {"type": "string"}
      },
      "file_path": {"type": "string"},
      "created_at": {"type": "string"},
      "updated_at": {"type": "string"},
      "invalidation_reason": {"type": "string", "nullable": true}
    }
  }
}

// Tool 2: Update entity state
{
  "name": "update_entity_state",
  "description": "Update state of a planning entity",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_type": {"type": "string", "enum": ["act", "chapter", "scene"]},
      "entity_id": {"type": "string"},
      "status": {"type": "string", "enum": ["draft", "approved", "requires-revalidation", "invalid"]},
      "version_hash": {"type": "string"},
      "file_path": {"type": "string"},
      "parent_id": {"type": "string", "nullable": true},
      "parent_version_hash": {"type": "string", "nullable": true},
      "invalidation_reason": {"type": "string", "nullable": true}
    },
    "required": ["entity_type", "entity_id", "status", "version_hash", "file_path"]
  }
}

// Tool 3: Get hierarchy tree
{
  "name": "get_hierarchy_tree",
  "description": "Get complete hierarchy tree for an act with all descendants",
  "inputSchema": {
    "type": "object",
    "properties": {
      "act_id": {"type": "string", "description": "Act ID (e.g., 'act-1')"},
      "include_status": {"type": "boolean", "default": true}
    },
    "required": ["act_id"]
  },
  "returns": {
    "type": "object",
    "description": "Nested tree structure with status for each node"
  }
}

// Tool 4: Cascade invalidation
{
  "name": "cascade_invalidate",
  "description": "Mark entity and all descendants as requires-revalidation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_type": {"type": "string", "enum": ["act", "chapter", "scene"]},
      "entity_id": {"type": "string"},
      "reason": {"type": "string"}
    },
    "required": ["entity_type", "entity_id", "reason"]
  },
  "returns": {
    "type": "object",
    "properties": {
      "success": {"type": "boolean"},
      "invalidated_entities": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "entity_type": {"type": "string"},
            "entity_id": {"type": "string"},
            "previous_status": {"type": "string"},
            "new_status": {"type": "string"}
          }
        }
      }
    }
  }
}

// Tool 5: Get children status
{
  "name": "get_children_status",
  "description": "Get status summary of all children for an entity",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_type": {"type": "string", "enum": ["act", "chapter"]},
      "entity_id": {"type": "string"}
    },
    "required": ["entity_type", "entity_id"]
  },
  "returns": {
    "type": "object",
    "properties": {
      "total_children": {"type": "integer"},
      "status_counts": {
        "type": "object",
        "properties": {
          "draft": {"type": "integer"},
          "approved": {"type": "integer"},
          "requires-revalidation": {"type": "integer"},
          "invalid": {"type": "integer"}
        }
      },
      "children": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "entity_id": {"type": "string"},
            "status": {"type": "string"},
            "file_path": {"type": "string"}
          }
        }
      }
    }
  }
}

// Tool 6: Approve entity
{
  "name": "approve_entity",
  "description": "Change entity status from draft to approved (with validation)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_type": {"type": "string", "enum": ["act", "chapter", "scene"]},
      "entity_id": {"type": "string"},
      "force": {"type": "boolean", "default": false, "description": "Approve even with warnings"}
    },
    "required": ["entity_type", "entity_id"]
  },
  "returns": {
    "type": "object",
    "properties": {
      "success": {"type": "boolean"},
      "message": {"type": "string"},
      "warnings": {"type": "array", "items": {"type": "string"}}
    }
  }
}
```

#### 1.2.2 New Resources

```typescript
{
  "uri": "state://planning/{entity_type}/{entity_id}",
  "name": "Planning Entity State",
  "description": "Current state of planning entity (act/chapter/scene)",
  "mimeType": "application/json",
  "auto_inject": "never",  // Hooks will retrieve when needed
  "notes": "Accessed by hooks, not auto-injected"
}

{
  "uri": "state://planning/hierarchy/{act_id}",
  "name": "Act Hierarchy Tree",
  "description": "Complete hierarchy tree for an act",
  "mimeType": "application/json",
  "auto_inject": "never"
}
```

### 1.3 Storage Mechanism: SQLite + JSON Fallback

**Decision:** SQLite for performance, JSON files for fallback

**Rationale:**
- SQLite provides fast querying (hierarchy trees, children status, etc.)
- Atomic transactions for cascading operations (all-or-nothing)
- JSON files provide human-readable fallback if DB corrupted
- 50-100 entities per act is small enough for SQLite to handle efficiently

**Schema:**

```sql
-- Planning entities table
CREATE TABLE planning_entities (
    entity_type TEXT NOT NULL,  -- 'act', 'chapter', 'scene'
    entity_id TEXT NOT NULL,    -- 'act-1', 'chapter-02', 'scene-0204'
    status TEXT NOT NULL,       -- 'draft', 'approved', 'requires-revalidation', 'invalid'
    version_hash TEXT NOT NULL, -- SHA-256 of file content
    previous_version_hash TEXT, -- For tracking changes
    file_path TEXT NOT NULL,    -- Absolute path to file
    parent_id TEXT,             -- Parent entity_id (NULL for acts)
    parent_version_hash TEXT,   -- Version hash of parent when created
    invalidation_reason TEXT,   -- Why marked requires-revalidation
    created_at TEXT NOT NULL,   -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,   -- ISO 8601 timestamp
    invalidated_at TEXT,        -- When marked requires-revalidation
    metadata JSON,              -- Flexible JSON blob for extra data

    PRIMARY KEY (entity_type, entity_id),
    FOREIGN KEY (parent_id) REFERENCES planning_entities(entity_id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX idx_parent_lookup ON planning_entities(parent_id);
CREATE INDEX idx_status_lookup ON planning_entities(status);
CREATE INDEX idx_version_hash ON planning_entities(version_hash);

-- Backup history table
CREATE TABLE planning_entity_backups (
    backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    version_hash TEXT NOT NULL,
    backup_file_path TEXT NOT NULL,
    backed_up_at TEXT NOT NULL,
    reason TEXT  -- 'regeneration', 'manual', 'restore'
);

CREATE INDEX idx_backup_entity ON planning_entity_backups(entity_type, entity_id);
```

**JSON Fallback Format:**

If SQLite unavailable, fall back to JSON files:

```
workspace/planning-state/
├── acts/
│   └── act-1.json
├── chapters/
│   ├── chapter-01.json
│   ├── chapter-02.json
│   └── ...
└── scenes/
    ├── scene-0101.json
    ├── scene-0102.json
    └── ...
```

Each JSON file contains the same fields as SQLite row.

**Sync Strategy:**
- MCP server writes to SQLite
- Every 10 updates OR every 60 seconds → dump SQLite to JSON files
- On startup: Load from SQLite; if missing/corrupted → load from JSON files

### 1.4 Configuration

**Environment Variables:**

```bash
# Storage backend
PLANNING_STATE_STORAGE=sqlite  # 'sqlite' or 'json'
PLANNING_STATE_DB_PATH=workspace/planning-state.db
PLANNING_STATE_JSON_DIR=workspace/planning-state/

# Sync settings
PLANNING_STATE_JSON_SYNC_ENABLED=true
PLANNING_STATE_JSON_SYNC_INTERVAL_SECONDS=60

# Performance
PLANNING_CASCADE_MAX_DEPTH=10  # Prevent infinite loops
PLANNING_STATE_CACHE_TTL_SECONDS=30

# Logging
PLANNING_STATE_LOG_FILE=workspace/logs/mcp-planning-state.log
```

---

## 2. Hook System Design

### 2.1 Hook Architecture Overview

**4 New Hooks:**

| Hook Name | Type | Trigger | Purpose | Blocking |
|-----------|------|---------|---------|----------|
| `hierarchy_validation_hook.py` | PreToolUse | Before planning commands | Validate parent exists and approved | YES (hard block) |
| `consistency_check_hook.py` | PostToolUse | After file write | Validate child matches parent | NO (warning) |
| `invalidation_cascade_hook.py` | PostToolUse | After file write (parent) | Mark children as requires-revalidation | YES (must complete) |
| `state_sync_hook.py` | PostToolUse | After any planning file write | Sync file → MCP state | NO (best-effort) |

### 2.2 Execution Order & Dependencies

```
┌─────────────────────────────────────────────────────────┐
│  USER: /plan-chapter 2                                  │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────┐
│  PRE-TOOL-USE HOOKS                                   │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 1. session_guard_hook.py (existing)             │  │
│  │    → Check: Active session exists?              │  │
│  │    → If NO: BLOCK                               │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 2. hierarchy_validation_hook.py (NEW)           │  │
│  │    → Check: Parent (act-1) exists?              │  │
│  │    → Check: Parent status = 'approved'?         │  │
│  │    → If NO: BLOCK with error message            │  │
│  │    → If YES: Proceed                            │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────┐
│  TOOL EXECUTION                                       │
│  planning-coordinator creates chapter plan            │
│  → Writes acts/act-1/chapters/chapter-02/plan.md      │
└───────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────┐
│  POST-TOOL-USE HOOKS (Sequential Order)               │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 1. state_sync_hook.py (NEW)                     │  │
│  │    → Hash file content (SHA-256)                │  │
│  │    → Call MCP: update_entity_state()            │  │
│  │    → Status: 'draft', parent: act-1             │  │
│  │    → If MCP fails: Log warning, continue        │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 2. consistency_check_hook.py (NEW)              │  │
│  │    → Read parent plan (act-1)                   │  │
│  │    → Read child plan (chapter-02)               │  │
│  │    → Check: child aligns with parent?           │  │
│  │    → If inconsistencies: Log warnings           │  │
│  │    → Never blocks (observability only)          │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 3. state_tracking_hook.py (existing)            │  │
│  │    → Check generation state files updated       │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

**Execution Order Guarantees:**
1. PreToolUse hooks run in registration order (session → hierarchy)
2. PostToolUse hooks run in registration order (state sync → consistency → state tracking)
3. If ANY PreToolUse hook exits with code 1 → tool call blocked
4. PostToolUse hooks run even if tool call failed (for cleanup)

### 2.3 Hook Specifications

#### 2.3.1 `hierarchy_validation_hook.py` (PreToolUse)

**Responsibility:** Enforce hierarchy (Act → Chapter → Scene) before planning

**Trigger:** Before Task tool with planning agents (`planning-coordinator`)

**Logic:**

```python
def main():
    # 1. Parse event data
    event = json.load(sys.stdin)
    tool = event.get("tool_name")

    if tool != "Task":
        sys.exit(0)  # Not planning, skip

    # 2. Detect planning command
    prompt = event.get("tool_input", {}).get("prompt", "")
    command_type, entity_id = detect_planning_command(prompt)
    # Returns: ("plan-act", "1"), ("plan-chapter", "2"), ("plan-scene", "0204"), or (None, None)

    if not command_type:
        sys.exit(0)  # Not a planning command

    # 3. Validate hierarchy
    if command_type == "plan-act":
        # Acts have no parent, always allowed
        sys.exit(0)

    elif command_type == "plan-chapter":
        chapter_num = int(entity_id)
        act_num = 1  # Extract from context or assume act-1 (configurable)

        # Check if parent act exists and approved
        parent_state = call_mcp_tool("get_entity_state", {
            "entity_type": "act",
            "entity_id": f"act-{act_num}"
        })

        if not parent_state or parent_state["status"] != "approved":
            block_with_error(
                f"Cannot plan chapter {entity_id}",
                f"Parent act plan not approved (current status: {parent_state.get('status', 'missing')})",
                [
                    f"1. Review act plan: {parent_state.get('file_path', 'N/A')}",
                    f"2. Run: /approve-plan act {act_num}",
                    f"3. Then retry: /plan-chapter {entity_id}"
                ]
            )

    elif command_type == "plan-scene":
        scene_id = entity_id
        chapter_id = f"chapter-{scene_id[:2]}"  # Extract chapter from scene ID

        # Check if parent chapter exists and approved
        parent_state = call_mcp_tool("get_entity_state", {
            "entity_type": "chapter",
            "entity_id": chapter_id
        })

        if not parent_state or parent_state["status"] != "approved":
            block_with_error(
                f"Cannot plan scene {scene_id}",
                f"Parent chapter plan not approved (current status: {parent_state.get('status', 'missing')})",
                [
                    f"1. Review chapter plan: {parent_state.get('file_path', 'N/A')}",
                    f"2. Run: /approve-plan chapter {chapter_id[8:]}",
                    f"3. Then retry: /plan-scene {scene_id}"
                ]
            )

def block_with_error(reason, details, actions):
    print(f"\n❌ BLOCKED BY HIERARCHY VALIDATION\n", file=sys.stderr)
    print(f"Reason: {reason}", file=sys.stderr)
    print(f"{details}\n", file=sys.stderr)
    print("Action required:", file=sys.stderr)
    for action in actions:
        print(f"  {action}", file=sys.stderr)
    print("\nHierarchy: Act → Chapter → Scene\n", file=sys.stderr)
    sys.exit(1)  # Exit with error to block
```

**Data Sources:**
- MCP tool: `get_entity_state(entity_type, entity_id)`
- Returns entity state including status

**Exit Codes:**
- `0` = Allow (no validation needed or validation passed)
- `1` = Block (parent not approved)

#### 2.3.2 `consistency_check_hook.py` (PostToolUse)

**Responsibility:** Validate child plan matches parent constraints (observability, not enforcement)

**Trigger:** After file write of planning files (`plan.md`, `*-blueprint.md`, `strategic-plan.md`)

**Logic:**

```python
def main():
    # 1. Parse event data
    event = json.load(sys.stdin)
    tool = event.get("tool_name")

    if tool not in ["Write", "Edit"]:
        sys.exit(0)  # Not a file write

    file_path = event.get("tool_input", {}).get("file_path", "")

    # 2. Detect planning file
    entity_type, entity_id = detect_planning_file(file_path)
    # Returns: ("chapter", "chapter-02") or ("scene", "scene-0204") or (None, None)

    if not entity_type or entity_type == "act":
        sys.exit(0)  # Acts have no parent to check against

    # 3. Get parent state
    if entity_type == "chapter":
        parent_type = "act"
        parent_id = "act-1"  # Extract from file path
    elif entity_type == "scene":
        parent_type = "chapter"
        parent_id = f"chapter-{entity_id[6:8]}"  # scene-0204 → chapter-02

    parent_state = call_mcp_tool("get_entity_state", {
        "entity_type": parent_type,
        "entity_id": parent_id
    })

    if not parent_state:
        print(f"⚠️ [Consistency Check] Parent {parent_id} not found in state", file=sys.stderr)
        sys.exit(0)  # Can't check consistency without parent

    # 4. Read both files
    parent_content = read_file(parent_state["file_path"])
    child_content = read_file(file_path)

    # 5. Run consistency checks
    warnings = []

    # Check 1: Character overlap
    parent_chars = extract_characters(parent_content)
    child_chars = extract_characters(child_content)
    extra_chars = set(child_chars) - set(parent_chars)
    if extra_chars:
        warnings.append(f"Characters in {entity_id} not mentioned in parent: {extra_chars}")

    # Check 2: Location consistency
    parent_locations = extract_locations(parent_content)
    child_locations = extract_locations(child_content)
    invalid_locs = set(child_locations) - set(parent_locations)
    if invalid_locs:
        warnings.append(f"Locations in {entity_id} not planned in parent: {invalid_locs}")

    # Check 3: Timeline consistency (scene only)
    if entity_type == "scene":
        parent_timeline = extract_timeline(parent_content)
        child_timeline = extract_timeline(child_content)
        if not timeline_compatible(parent_timeline, child_timeline):
            warnings.append(f"Timeline in {entity_id} conflicts with parent chapter plan")

    # 6. Log warnings (non-blocking)
    if warnings:
        print(f"\n⚠️ [Consistency Check] Warnings for {entity_id}:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
        print(f"💡 Consider reviewing {file_path} against parent plan\n", file=sys.stderr)

    # Always exit successfully (non-blocking)
    sys.exit(0)
```

**Data Sources:**
- MCP tool: `get_entity_state()` to get parent file path
- File system: Read parent and child files

**Exit Codes:**
- Always `0` (non-blocking, observability only)

#### 2.3.3 `invalidation_cascade_hook.py` (PostToolUse)

**Responsibility:** Mark children as `requires-revalidation` when parent regenerated

**Trigger:** After file write of planning files (only when file already existed = regeneration)

**Logic:**

```python
def main():
    # 1. Parse event data
    event = json.load(sys.stdin)
    tool = event.get("tool_name")

    if tool not in ["Write", "Edit"]:
        sys.exit(0)

    file_path = event.get("tool_input", {}).get("file_path", "")

    # 2. Detect planning file
    entity_type, entity_id = detect_planning_file(file_path)

    if not entity_type:
        sys.exit(0)  # Not a planning file

    # 3. Check if this is a regeneration (file already existed in state)
    current_state = call_mcp_tool("get_entity_state", {
        "entity_type": entity_type,
        "entity_id": entity_id
    })

    if not current_state:
        # New entity, not regeneration
        sys.exit(0)

    # 4. Calculate new version hash
    file_content = read_file(file_path)
    new_hash = sha256(file_content)

    if new_hash == current_state["version_hash"]:
        # No changes, skip cascade
        sys.exit(0)

    # 5. This IS a regeneration - cascade invalidation
    print(f"\n⚠️ [Invalidation Cascade] {entity_id} regenerated", file=sys.stderr)
    print(f"  Old version: {current_state['version_hash'][:8]}...", file=sys.stderr)
    print(f"  New version: {new_hash[:8]}...", file=sys.stderr)

    # 6. Call MCP to cascade invalidation
    result = call_mcp_tool("cascade_invalidate", {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "reason": f"parent_{entity_type}_regenerated"
    })

    if not result["success"]:
        print(f"❌ [Invalidation Cascade] Failed: {result.get('error')}", file=sys.stderr)
        sys.exit(1)  # Block on cascade failure (critical operation)

    # 7. Display summary
    invalidated = result["invalidated_entities"]
    print(f"  ✓ Invalidated {len(invalidated)} children:", file=sys.stderr)
    for entity in invalidated:
        print(f"    - {entity['entity_id']} ({entity['previous_status']} → {entity['new_status']})", file=sys.stderr)
    print("", file=sys.stderr)

    sys.exit(0)
```

**Data Sources:**
- MCP tool: `get_entity_state()` to check if entity exists
- MCP tool: `cascade_invalidate()` to mark children
- File system: Read file to compute hash

**Exit Codes:**
- `0` = Success (cascade completed or not needed)
- `1` = Failure (cascade failed - critical error)

**Cascade Algorithm (in MCP server):**

```python
def cascade_invalidate(entity_type, entity_id, reason):
    """
    Mark entity and ALL descendants as requires-revalidation.
    Transaction-based: all-or-nothing.
    """
    # 1. Get all descendants (recursive query)
    descendants = get_all_descendants(entity_type, entity_id)

    # 2. Start transaction
    with db.transaction():
        # 3. For each descendant
        invalidated = []
        for desc in descendants:
            prev_status = desc["status"]

            # Skip if already invalid or requires-revalidation
            if prev_status in ["invalid", "requires-revalidation"]:
                continue

            # Update status
            db.execute("""
                UPDATE planning_entities
                SET status = 'requires-revalidation',
                    invalidation_reason = ?,
                    invalidated_at = ?
                WHERE entity_type = ? AND entity_id = ?
            """, (reason, now(), desc["entity_type"], desc["entity_id"]))

            invalidated.append({
                "entity_type": desc["entity_type"],
                "entity_id": desc["entity_id"],
                "previous_status": prev_status,
                "new_status": "requires-revalidation"
            })

        # 4. Commit transaction (all-or-nothing)

    return {"success": True, "invalidated_entities": invalidated}

def get_all_descendants(entity_type, entity_id):
    """
    Recursive query to get all descendants.
    """
    # Build recursive CTE
    query = """
        WITH RECURSIVE descendants AS (
            -- Base case: direct children
            SELECT * FROM planning_entities
            WHERE parent_id = ?

            UNION ALL

            -- Recursive case: children of children
            SELECT e.* FROM planning_entities e
            INNER JOIN descendants d ON e.parent_id = d.entity_id
        )
        SELECT * FROM descendants
    """

    results = db.execute(query, (entity_id,))
    return results
```

#### 2.3.4 `state_sync_hook.py` (PostToolUse)

**Responsibility:** Sync file system → MCP state after planning file writes

**Trigger:** After any write to planning files

**Logic:**

```python
def main():
    # 1. Parse event data
    event = json.load(sys.stdin)
    tool = event.get("tool_name")

    if tool not in ["Write", "Edit"]:
        sys.exit(0)

    file_path = event.get("tool_input", {}).get("file_path", "")

    # 2. Detect planning file
    entity_type, entity_id = detect_planning_file(file_path)

    if not entity_type:
        sys.exit(0)  # Not a planning file

    # 3. Read file and compute hash
    try:
        file_content = read_file(file_path)
        version_hash = sha256(file_content)
    except Exception as e:
        print(f"⚠️ [State Sync] Failed to read file: {e}", file=sys.stderr)
        sys.exit(0)  # Non-blocking

    # 4. Determine parent
    parent_id = None
    parent_version_hash = None

    if entity_type == "chapter":
        act_num = extract_act_from_path(file_path)
        parent_id = f"act-{act_num}"
        parent_state = call_mcp_tool("get_entity_state", {
            "entity_type": "act",
            "entity_id": parent_id
        })
        if parent_state:
            parent_version_hash = parent_state["version_hash"]

    elif entity_type == "scene":
        chapter_num = entity_id[6:8]  # scene-0204 → 02
        parent_id = f"chapter-{chapter_num}"
        parent_state = call_mcp_tool("get_entity_state", {
            "entity_type": "chapter",
            "entity_id": parent_id
        })
        if parent_state:
            parent_version_hash = parent_state["version_hash"]

    # 5. Sync to MCP
    try:
        call_mcp_tool("update_entity_state", {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": "draft",  # Always draft on creation/update
            "version_hash": version_hash,
            "file_path": file_path,
            "parent_id": parent_id,
            "parent_version_hash": parent_version_hash
        })
        print(f"✓ [State Sync] {entity_id} synced to MCP state", file=sys.stderr)
    except Exception as e:
        # Best-effort sync, don't block on failure
        print(f"⚠️ [State Sync] Failed to sync {entity_id}: {e}", file=sys.stderr)

    # Always exit successfully (non-blocking)
    sys.exit(0)
```

**Data Sources:**
- File system: Read file to compute hash
- MCP tool: `update_entity_state()` to write state
- MCP tool: `get_entity_state()` to get parent version

**Exit Codes:**
- Always `0` (non-blocking, best-effort sync)

### 2.4 Hook Registration

**File:** `.claude/hooks.config.json`

```json
{
  "hooks": {
    "preToolUse": [
      {
        "name": "session-guard",
        "script": ".claude/hooks/session_guard_hook.py",
        "enabled": true,
        "order": 1
      },
      {
        "name": "hierarchy-validation",
        "script": ".claude/hooks/hierarchy_validation_hook.py",
        "enabled": true,
        "order": 2
      }
    ],
    "postToolUse": [
      {
        "name": "state-sync",
        "script": ".claude/hooks/state_sync_hook.py",
        "enabled": true,
        "order": 1
      },
      {
        "name": "consistency-check",
        "script": ".claude/hooks/consistency_check_hook.py",
        "enabled": true,
        "order": 2
      },
      {
        "name": "invalidation-cascade",
        "script": ".claude/hooks/invalidation_cascade_hook.py",
        "enabled": true,
        "order": 3
      },
      {
        "name": "state-tracking",
        "script": ".claude/hooks/state_tracking_hook.py",
        "enabled": true,
        "order": 4
      }
    ]
  }
}
```

**Order guarantees sequential execution.**

---

## 3. Agent Integration: Context Injection

### 3.1 Decision: Prompt Preprocessing (Not Agent Modification)

**Rationale:**
- Maintains agent isolation (agents don't know about hierarchy)
- Agents remain focused on creative work (planning content)
- Orchestrator (`planning-coordinator`) handles context injection
- No need to modify existing agents

**Architecture:**

```
User: /plan-chapter 2
    ↓
hierarchy_validation_hook validates parent
    ↓
MCP: get_entity_state(act, act-1) → returns parent state
    ↓
Read parent file: acts/act-1/strategic-plan.md
    ↓
Inject into planning-coordinator prompt:
    ↓
┌────────────────────────────────────────────────┐
│ You are planning Chapter 2.                   │
│                                                │
│ PARENT CONTEXT (Act 1 Strategic Plan):        │
│ ───────────────────────────────────────────    │
│ [Full content of strategic-plan.md]           │
│ ───────────────────────────────────────────    │
│                                                │
│ Your chapter plan MUST align with this act    │
│ plan. Follow Phase 1-5 workflow as normal.    │
└────────────────────────────────────────────────┘
    ↓
planning-coordinator runs normally
    ↓
Agents receive parent context transparently
```

### 3.2 Implementation: Command Routing

**New Commands:**

```bash
/plan-act <N>       # Route to planning-coordinator with level=act
/plan-chapter <N>   # Route to planning-coordinator with level=chapter + parent context
/plan-scene <NNNN>  # Route to planning-coordinator with level=scene + parent context
```

**Existing:**

```bash
/plan-story         # Keep for backward compatibility, shows level selection menu
```

**Command Handler:**

```python
def handle_plan_command(command, args):
    """
    Route planning commands to planning-coordinator with context injection.
    """
    # 1. Parse command
    if command == "/plan-act":
        level = "act"
        entity_id = f"act-{args[0]}"
        parent_context = None

    elif command == "/plan-chapter":
        level = "chapter"
        chapter_num = args[0]
        entity_id = f"chapter-{chapter_num.zfill(2)}"

        # Get parent context
        act_num = 1  # TODO: Extract from current working directory or config
        parent_state = call_mcp("get_entity_state", {
            "entity_type": "act",
            "entity_id": f"act-{act_num}"
        })

        if not parent_state:
            raise Error("Parent act plan not found")

        parent_content = read_file(parent_state["file_path"])
        parent_context = {
            "type": "act",
            "id": f"act-{act_num}",
            "content": parent_content,
            "file_path": parent_state["file_path"]
        }

    elif command == "/plan-scene":
        level = "scene"
        scene_id = args[0]
        entity_id = f"scene-{scene_id}"

        # Get parent context
        chapter_num = scene_id[:2]
        parent_state = call_mcp("get_entity_state", {
            "entity_type": "chapter",
            "entity_id": f"chapter-{chapter_num}"
        })

        if not parent_state:
            raise Error("Parent chapter plan not found")

        parent_content = read_file(parent_state["file_path"])
        parent_context = {
            "type": "chapter",
            "id": f"chapter-{chapter_num}",
            "content": parent_content,
            "file_path": parent_state["file_path"]
        }

    # 2. Build prompt with context injection
    prompt = build_planning_prompt(level, entity_id, parent_context)

    # 3. Invoke planning-coordinator
    invoke_agent("planning-coordinator", prompt)

def build_planning_prompt(level, entity_id, parent_context):
    """
    Build prompt with optional parent context injection.
    """
    base_prompt = f"""
You are planning {level}: {entity_id}.

Follow the standard Planning Workflow (Phases 1-5):
- Phase 1: Exploration (dialogue-analyst, context-analyzer)
- Phase 2: Scenario generation (scenario-generator, consequence-predictor)
- Phase 3: Path planning (arc-planner, dependency-mapper)
- Phase 4: Detailing (emotional-arc-designer, beat-planner, dialogue-weaver)
- Phase 5: Integration (storyline-integrator, impact-analyzer)

Output: Save plan to appropriate location.
"""

    if parent_context:
        parent_section = f"""

═══════════════════════════════════════════════════════════
PARENT CONTEXT ({parent_context['type'].upper()})
═══════════════════════════════════════════════════════════

File: {parent_context['file_path']}

{parent_context['content']}

═══════════════════════════════════════════════════════════

CRITICAL: Your {level} plan MUST align with the parent {parent_context['type']} plan above.

- Characters mentioned in your plan should be from parent plan
- Events should follow the structure outlined in parent plan
- Timeline should be consistent with parent plan
- Locations should match parent plan

If you need to introduce NEW elements not in parent plan:
1. Flag them explicitly in your output
2. Explain why they're necessary
3. User will review and may request parent plan update

═══════════════════════════════════════════════════════════
"""
        return base_prompt + parent_section

    return base_prompt
```

### 3.3 Agent Isolation Maintained

**Key Points:**
- Agents (`dialogue-analyst`, `context-analyzer`, etc.) receive NO modifications
- All agents work EXACTLY as before
- Parent context injected at coordinator level, flows naturally through workflow
- Agents see parent content as part of "context" (same as reading world-bible)
- No coupling between agents and hierarchy system

**Flow Example:**

```
planning-coordinator receives:
  "Plan chapter 2. Parent context: [act plan]"
    ↓
coordinator Phase 1: "Ask questions about chapter 2"
    ↓
dialogue-analyst: Reads prompt, sees act plan in context, asks relevant questions
    ↓
context-analyzer: Reads act plan, extracts constraints for chapter 2
    ↓
... workflow continues normally ...
    ↓
Final output: chapter plan that naturally aligns with act plan
```

---

## 4. Command Implementation

### 4.1 Command Structure: Separate Commands

**Decision:** Use separate commands `/plan-act`, `/plan-chapter`, `/plan-scene`

**Rationale:**
- Explicit hierarchy (user always knows what level they're planning)
- Clear in logs and documentation (easier to debug)
- Simpler validation (each command has specific rules)
- Backward compatible (keep `/plan-story` as fallback)

**Command Specifications:**

```bash
# Command: /plan-act
# Description: Create strategic plan for an entire act
# Usage: /plan-act <act_number>
# Example: /plan-act 1
# Validation:
#   - act_number must be integer 1-10
#   - No parent validation (acts are root)
# Output: acts/act-{N}/strategic-plan.md

# Command: /plan-chapter
# Description: Create detailed plan for a chapter
# Usage: /plan-chapter <chapter_number> [--act <act_number>]
# Example: /plan-chapter 2
# Validation:
#   - chapter_number must be integer 1-99
#   - Parent act must exist and be approved (validated by hook)
# Output: acts/act-{N}/chapters/chapter-{NN}/plan.md

# Command: /plan-scene
# Description: Create blueprint for a scene
# Usage: /plan-scene <scene_id>
# Example: /plan-scene 0204
# Validation:
#   - scene_id must be 4 digits (CCSS format)
#   - Parent chapter must exist and be approved (validated by hook)
# Output: acts/act-{N}/chapters/chapter-{CC}/scenes/scene-{CCSS}-blueprint.md

# Command: /plan-story (LEGACY)
# Description: Interactive planning with level selection
# Usage: /plan-story
# Behavior: Shows menu, then routes to appropriate command
```

### 4.2 Backward Compatibility

**Existing `/plan-story` command:**

```
User: /plan-story

planning-coordinator: "What do you want to plan?"

Options:
1. Strategic planning (entire act)    → Routes to /plan-act
2. Storyline planning (character arc) → Existing storyline workflow
3. Chapter planning (chapter)         → Routes to /plan-chapter
4. Scene planning (scene)             → Routes to /plan-scene
5. Event planning (event)             → Existing event workflow

User selects option → Routes to appropriate specialized command
```

**Migration Path:**
1. v1: Both `/plan-story` and new commands work
2. v2: Deprecate `/plan-story` menu, require explicit commands
3. v3: Remove `/plan-story` (breaking change, major version)

### 4.3 Parameter Parsing

**Implementation:**

```python
def parse_plan_command(raw_command):
    """
    Parse planning command and extract parameters.

    Returns: (command_type, entity_id, params)
    """
    parts = raw_command.split()
    command = parts[0]

    if command == "/plan-act":
        act_num = parts[1]
        return ("plan-act", f"act-{act_num}", {"act_num": act_num})

    elif command == "/plan-chapter":
        chapter_num = parts[1].zfill(2)  # Pad to 2 digits

        # Optional --act flag
        act_num = "1"  # Default
        if "--act" in parts:
            act_idx = parts.index("--act")
            act_num = parts[act_idx + 1]

        return ("plan-chapter", f"chapter-{chapter_num}", {
            "chapter_num": chapter_num,
            "act_num": act_num
        })

    elif command == "/plan-scene":
        scene_id = parts[1].zfill(4)  # Pad to 4 digits
        chapter_num = scene_id[:2]
        act_num = "1"  # Extract from context or default

        return ("plan-scene", f"scene-{scene_id}", {
            "scene_id": scene_id,
            "chapter_num": chapter_num,
            "act_num": act_num
        })

    else:
        raise ValueError(f"Unknown command: {command}")
```

---

## 5. Cascading Invalidation Algorithm

### 5.1 Deep Cascade Strategy

**Decision:** Deep cascade (act → all chapters → all scenes)

**Rationale:**
- Simplicity: Single operation invalidates entire subtree
- Safety: Better to over-invalidate than miss dependencies
- User control: User can selectively re-approve compatible children
- Performance: 50-100 entities is small enough for deep cascade

**Algorithm:**

```python
def cascade_invalidate_recursive(entity_type, entity_id, reason):
    """
    Recursively invalidate entity and all descendants.
    Uses transaction for atomicity.
    """
    invalidated = []

    # Use recursive CTE to get ALL descendants in one query
    descendants_query = """
        WITH RECURSIVE descendants AS (
            -- Base: entity itself
            SELECT entity_type, entity_id, status
            FROM planning_entities
            WHERE entity_type = ? AND entity_id = ?

            UNION ALL

            -- Recursive: all children at any depth
            SELECT e.entity_type, e.entity_id, e.status
            FROM planning_entities e
            INNER JOIN descendants d
                ON (
                    -- Chapter children of act
                    (d.entity_type = 'act' AND e.entity_type = 'chapter' AND e.parent_id = d.entity_id)
                    OR
                    -- Scene children of chapter
                    (d.entity_type = 'chapter' AND e.entity_type = 'scene' AND e.parent_id = d.entity_id)
                )
        )
        SELECT entity_type, entity_id, status FROM descendants
        WHERE NOT (entity_type = ? AND entity_id = ?)  -- Exclude root entity
    """

    with db.transaction():
        # 1. Get all descendants
        rows = db.execute(descendants_query, (entity_type, entity_id, entity_type, entity_id))

        # 2. Update each descendant
        for row in rows:
            prev_status = row["status"]

            # Skip if already invalidated
            if prev_status in ["invalid", "requires-revalidation"]:
                continue

            # Update to requires-revalidation
            db.execute("""
                UPDATE planning_entities
                SET status = 'requires-revalidation',
                    invalidation_reason = ?,
                    invalidated_at = ?
                WHERE entity_type = ? AND entity_id = ?
            """, (reason, now(), row["entity_type"], row["entity_id"]))

            invalidated.append({
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "previous_status": prev_status,
                "new_status": "requires-revalidation"
            })

    return invalidated
```

### 5.2 Transaction Semantics (All-or-Nothing)

**Guarantee:** Either ALL descendants invalidated OR none

**Implementation:**
- SQLite transaction wraps entire cascade
- If ANY update fails → rollback entire transaction
- Hook exits with error code 1 if cascade fails
- User sees clear error message, must fix state manually

**Error Handling:**

```python
try:
    with db.transaction():
        # ... cascade logic ...
        db.commit()
except Exception as e:
    db.rollback()
    raise CascadeError(f"Failed to cascade invalidation: {e}")
```

### 5.3 Performance Considerations

**Worst Case:** Act with 20 chapters, each with 10 scenes = 220 entities to invalidate

**Performance:**
- Recursive CTE query: <10ms (SQLite is fast for 220 rows)
- 220 UPDATE statements: <50ms (within transaction)
- Total cascade time: <100ms

**Optimization:** Use single UPDATE with IN clause:

```sql
UPDATE planning_entities
SET status = 'requires-revalidation',
    invalidation_reason = ?,
    invalidated_at = ?
WHERE entity_id IN (
    -- Recursive CTE returns list of entity_ids
)
```

Reduces to single UPDATE, faster for large cascades.

---

## 6. Version Management

### 6.1 Version Hash Calculation: SHA-256

**Decision:** SHA-256 hash of file content (UTF-8 encoded)

**Rationale:**
- Deterministic: Same content → same hash
- Fast: SHA-256 hashing is <1ms for typical file sizes
- Git-independent: Works even if not using git
- Collision-resistant: SHA-256 has negligible collision probability

**Implementation:**

```python
import hashlib

def calculate_version_hash(file_path):
    """
    Calculate SHA-256 hash of file content.
    """
    with open(file_path, 'rb') as f:
        content = f.read()

    hash_obj = hashlib.sha256(content)
    return hash_obj.hexdigest()  # Returns 64-char hex string

# Example usage
hash1 = calculate_version_hash("acts/act-1/strategic-plan.md")
# "a7f3b9d2c8e1f4..." (64 characters)

# Later, check if file changed
hash2 = calculate_version_hash("acts/act-1/strategic-plan.md")
if hash1 != hash2:
    print("File was modified")
```

### 6.2 Backup File Naming

**Format:** `{original-name}-{YYYY-MM-DD-HH-MM-SS}.md`

**Examples:**
```
backups/plan-2025-11-11-14-30-45.md
backups/strategic-plan-2025-11-10-09-15-22.md
backups/scene-0204-blueprint-2025-11-11-16-45-10.md
```

**Directory Structure:**

```
acts/act-1/
├── strategic-plan.md              ← Current version
├── backups/
│   ├── strategic-plan-2025-11-10-09-15-22.md
│   ├── strategic-plan-2025-11-09-14-22-10.md
│   └── strategic-plan-2025-11-08-11-05-33.md
└── chapters/chapter-01/
    ├── plan.md                     ← Current version
    ├── backups/
    │   ├── plan-2025-11-11-10-30-15.md
    │   └── plan-2025-11-10-15-20-45.md
    └── scenes/scene-0101/
        ├── scene-0101-blueprint.md  ← Current version
        └── backups/
            └── scene-0101-blueprint-2025-11-09-12-00-00.md
```

### 6.3 Backup Creation Process

**Triggered by:** File write when entity already exists in state (regeneration)

**Flow:**

```
1. Hook detects file write to plan.md
2. Check MCP state: Does chapter-02 exist?
3. If YES (regeneration):
   a. Read current file path from state
   b. Calculate backup file name (timestamp)
   c. Create backups/ subdirectory if not exists
   d. Copy current file → backups/plan-{timestamp}.md
   e. Log backup to MCP: planning_entity_backups table
   f. Continue with file write (overwrite current file)
4. If NO (new entity):
   a. Skip backup, this is initial creation
```

**Implementation (in invalidation_cascade_hook.py):**

```python
def create_backup(entity_type, entity_id, current_file_path):
    """
    Create timestamped backup before regeneration.
    """
    # 1. Get parent directory
    parent_dir = Path(current_file_path).parent
    backups_dir = parent_dir / "backups"
    backups_dir.mkdir(exist_ok=True)

    # 2. Generate backup filename
    original_name = Path(current_file_path).stem  # plan, strategic-plan, scene-0204-blueprint
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    backup_name = f"{original_name}-{timestamp}.md"
    backup_path = backups_dir / backup_name

    # 3. Copy file
    shutil.copy2(current_file_path, backup_path)

    # 4. Log to MCP
    call_mcp_tool("log_backup", {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "version_hash": calculate_version_hash(current_file_path),
        "backup_file_path": str(backup_path),
        "reason": "regeneration"
    })

    print(f"✓ Backup created: {backup_path}", file=sys.stderr)
```

### 6.4 Restore Mechanism

**Command:** `/restore-version <type> <id> <timestamp>`

**Example:**
```bash
/restore-version chapter 2 2025-11-10-15-20-45
```

**Flow:**

```
1. Parse command: type=chapter, id=2, timestamp=2025-11-10-15-20-45
2. Construct backup path:
   acts/act-1/chapters/chapter-02/backups/plan-2025-11-10-15-20-45.md
3. Check if backup exists
4. If exists:
   a. Create backup of CURRENT version (pre-restore backup)
   b. Copy backup file → current location (plan.md)
   c. Update MCP state with restored version hash
   d. Trigger cascade invalidation (same as regeneration)
5. Show summary:
   "✓ Restored chapter 2 to version from 2025-11-10 15:20:45
    ⚠️ Invalidated X children (requires revalidation)"
```

### 6.5 Diff Calculation

**Command:** `/diff-version <type> <id> <timestamp>`

**Implementation:**

```python
def show_version_diff(entity_type, entity_id, timestamp):
    """
    Show diff between current version and backup.
    """
    # 1. Get current file path from MCP
    state = call_mcp_tool("get_entity_state", {
        "entity_type": entity_type,
        "entity_id": entity_id
    })
    current_path = state["file_path"]

    # 2. Construct backup path
    parent_dir = Path(current_path).parent
    filename = Path(current_path).stem
    backup_path = parent_dir / "backups" / f"{filename}-{timestamp}.md"

    # 3. Read both files
    current_content = read_file(current_path)
    backup_content = read_file(backup_path)

    # 4. Calculate diff (using difflib)
    import difflib
    diff = difflib.unified_diff(
        backup_content.splitlines(keepends=True),
        current_content.splitlines(keepends=True),
        fromfile=f"Backup ({timestamp})",
        tofile="Current",
        lineterm=""
    )

    # 5. Display diff
    print("\n".join(diff))
```

**Output Example:**

```diff
--- Backup (2025-11-10-15-20-45)
+++ Current
@@ -10,7 +10,7 @@

 ### Events главы
 1. Событие: Алекса прибывает в медпалату
-   - Сцены: 2.1, 2.2
+   - Сцены: 2.1, 2.2, 2.3 (добавлена новая сцена)
 2. Событие: Знакомство с Рейном
```

---

## 7. Recovery & Fallback Strategies

### 7.1 MCP Server Unavailable

**Scenario:** MCP server crashes or not started

**Detection:**
- Hooks call MCP tools
- If connection error → catch exception

**Behavior:**

```python
def call_mcp_tool(tool_name, params):
    """
    Call MCP tool with graceful fallback.
    """
    try:
        result = mcp_client.call_tool(tool_name, params)
        return result
    except ConnectionError:
        # MCP server unavailable
        print(f"⚠️ MCP server unavailable, using fallback", file=sys.stderr)
        return fallback_handler(tool_name, params)
    except Exception as e:
        print(f"⚠️ MCP error: {e}", file=sys.stderr)
        return None
```

**Fallback Handler:**

```python
def fallback_handler(tool_name, params):
    """
    Fallback to JSON files when MCP unavailable.
    """
    if tool_name == "get_entity_state":
        # Read from JSON file
        entity_type = params["entity_type"]
        entity_id = params["entity_id"]
        json_path = f"workspace/planning-state/{entity_type}s/{entity_id}.json"

        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                return json.load(f)
        return None

    elif tool_name == "update_entity_state":
        # Write to JSON file
        entity_type = params["entity_type"]
        entity_id = params["entity_id"]
        json_path = f"workspace/planning-state/{entity_type}s/{entity_id}.json"

        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        state_data = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": params["status"],
            "version_hash": params["version_hash"],
            "file_path": params["file_path"],
            "parent_id": params.get("parent_id"),
            "parent_version_hash": params.get("parent_version_hash"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        with open(json_path, 'w') as f:
            json.dump(state_data, f, indent=2)

        return {"success": True}

    # ... other tools fallback ...
```

### 7.2 State Sync After MCP Restart

**Scenario:** MCP server restarted, SQLite DB lost or out of sync

**Solution:** Sync from JSON files on startup

**Implementation (in MCP server):**

```python
def sync_from_json_on_startup():
    """
    On MCP server startup, sync state from JSON files.
    """
    json_dir = os.getenv("PLANNING_STATE_JSON_DIR", "workspace/planning-state")

    if not os.path.exists(json_dir):
        print("No JSON files found, starting with empty state")
        return

    # 1. Scan JSON files
    for entity_type in ["acts", "chapters", "scenes"]:
        type_dir = os.path.join(json_dir, entity_type)
        if not os.path.exists(type_dir):
            continue

        for json_file in os.listdir(type_dir):
            if not json_file.endswith(".json"):
                continue

            # 2. Read JSON
            with open(os.path.join(type_dir, json_file), 'r') as f:
                state_data = json.load(f)

            # 3. Insert into SQLite (or update if exists)
            db.execute("""
                INSERT OR REPLACE INTO planning_entities
                (entity_type, entity_id, status, version_hash, file_path, parent_id, parent_version_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state_data["entity_type"],
                state_data["entity_id"],
                state_data["status"],
                state_data["version_hash"],
                state_data["file_path"],
                state_data.get("parent_id"),
                state_data.get("parent_version_hash"),
                state_data.get("created_at", now()),
                state_data.get("updated_at", now())
            ))

    print(f"✓ Synced state from JSON files")
```

### 7.3 Manual State File Fallback

**Command:** `/rebuild-state`

**Purpose:** Rebuild MCP state from file system (emergency recovery)

**Flow:**

```
1. Scan file system for all planning files:
   - acts/*/strategic-plan.md
   - acts/*/chapters/*/plan.md
   - acts/*/chapters/*/scenes/*-blueprint.md

2. For each file:
   a. Calculate version hash (SHA-256)
   b. Detect entity type and ID from path
   c. Detect parent from path structure
   d. Create state entry with status='draft' (conservative)

3. Update MCP state (SQLite + JSON)

4. Show summary:
   "✓ Rebuilt state for:
    - 1 act (act-1)
    - 5 chapters (chapter-01 through chapter-05)
    - 23 scenes

    ⚠️ All entities marked as 'draft' (conservative)
    Run /approve-plan to approve entities individually"
```

### 7.4 Consistency Checking & Repair

**Command:** `/check-state-consistency`

**Checks:**

1. **File existence:** All entities in state have existing files
2. **Version mismatch:** File content hash matches state version_hash
3. **Orphan detection:** Entities with parent_id that doesn't exist
4. **Broken hierarchy:** Scene parent is not in same chapter, etc.

**Output:**

```
Consistency Check Results:

✓ File existence: 29/29 files found
⚠️ Version mismatches: 3 entities
  - chapter-02: File changed (hash mismatch)
  - scene-0204: File changed (hash mismatch)
  - scene-0205: File changed (hash mismatch)

❌ Orphan entities: 1
  - scene-0310: Parent chapter-03 not found in state

✓ Hierarchy structure: All valid

Actions:
1. Update version hashes: /sync-version-hashes
2. Rebuild state for orphans: /rebuild-state
```

**Auto-Repair:**

```bash
/repair-state --fix-hashes --rebuild-orphans
```

Automatically fixes version hash mismatches and rebuilds orphan entities.

---

## 8. Implementation Phases

### Phase 1: MCP Server Extension (Week 1)

**Deliverables:**
- [ ] SQLite schema implemented
- [ ] 6 new MCP tools implemented (get_entity_state, update_entity_state, etc.)
- [ ] JSON fallback mechanism implemented
- [ ] Sync from JSON on startup implemented
- [ ] Unit tests for MCP tools (pytest)

**Files:**
- `mcp-servers/generation_state_mcp.py` (extend existing)
- `mcp-servers/planning_state_schema.sql` (new)
- `mcp-servers/tests/test_planning_state.py` (new)

**Testing:**
- Create mock entities in SQLite
- Test get_entity_state returns correct data
- Test update_entity_state writes correctly
- Test cascade_invalidate recursively updates children
- Test JSON fallback when SQLite unavailable

---

### Phase 2: Hook Implementation (Week 2)

**Deliverables:**
- [ ] `hierarchy_validation_hook.py` implemented
- [ ] `consistency_check_hook.py` implemented
- [ ] `invalidation_cascade_hook.py` implemented
- [ ] `state_sync_hook.py` implemented
- [ ] Hook registration in `.claude/hooks.config.json`
- [ ] Integration tests for hooks

**Files:**
- `.claude/hooks/hierarchy_validation_hook.py`
- `.claude/hooks/consistency_check_hook.py`
- `.claude/hooks/invalidation_cascade_hook.py`
- `.claude/hooks/state_sync_hook.py`
- `.claude/hooks.config.json` (update)

**Testing:**
- Test hierarchy validation blocks when parent not approved
- Test consistency check logs warnings (non-blocking)
- Test invalidation cascade marks all children
- Test state sync updates MCP after file write
- Test hook execution order (sequential)

---

### Phase 3: Command Implementation (Week 3)

**Deliverables:**
- [ ] `/plan-act` command implemented
- [ ] `/plan-chapter` command implemented
- [ ] `/plan-scene` command implemented
- [ ] Command routing with context injection
- [ ] Backward compatibility with `/plan-story`
- [ ] Integration tests for commands

**Files:**
- `.claude/commands/plan-act.md` (new)
- `.claude/commands/plan-chapter.md` (new)
- `.claude/commands/plan-scene.md` (new)
- `.claude/commands/plan-story.md` (update for routing)

**Testing:**
- Test /plan-act creates act plan
- Test /plan-chapter injects parent context
- Test /plan-scene injects chapter context
- Test hooks block invalid commands
- Test end-to-end workflow (act → chapter → scene)

---

### Phase 4: Approval & Revalidation Workflow (Week 4)

**Deliverables:**
- [ ] `/approve-plan` command implemented
- [ ] `/revalidate-scene` command implemented
- [ ] `/revalidate-all` command implemented
- [ ] Approval validation (warnings if inconsistencies)
- [ ] Revalidation comparison tool

**Files:**
- `.claude/commands/approve-plan.md` (new)
- `.claude/commands/revalidate-scene.md` (new)
- `.claude/commands/revalidate-all.md` (new)

**Testing:**
- Test approve changes status draft → approved
- Test approve blocks if parent not approved
- Test revalidate shows comparison
- Test revalidate-all batch processes scenes

---

### Phase 5: Version Management (Week 5)

**Deliverables:**
- [ ] Backup creation on regeneration
- [ ] `/list-versions` command
- [ ] `/restore-version` command
- [ ] `/diff-version` command
- [ ] Backup table in SQLite

**Files:**
- `mcp-servers/generation_state_mcp.py` (add backup tools)
- `.claude/commands/list-versions.md` (new)
- `.claude/commands/restore-version.md` (new)
- `.claude/commands/diff-version.md` (new)

**Testing:**
- Test backup created when file regenerated
- Test list-versions shows backup history
- Test restore-version replaces current file
- Test diff-version shows correct differences

---

### Phase 6: Recovery & Utilities (Week 6)

**Deliverables:**
- [ ] `/rebuild-state` command
- [ ] `/check-state-consistency` command
- [ ] `/repair-state` command
- [ ] `/show-hierarchy` command (visual tree)
- [ ] Emergency recovery documentation

**Files:**
- `.claude/commands/rebuild-state.md` (new)
- `.claude/commands/check-state-consistency.md` (new)
- `.claude/commands/repair-state.md` (new)
- `.claude/commands/show-hierarchy.md` (new)
- `docs/emergency-recovery.md` (new)

**Testing:**
- Test rebuild-state recreates state from files
- Test check-state-consistency detects issues
- Test repair-state fixes common problems
- Test show-hierarchy displays tree correctly

---

### Phase 7: Integration & Polish (Week 7)

**Deliverables:**
- [ ] Update `.workflows/planning.md` documentation
- [ ] Update `CLAUDE.md` with new commands
- [ ] Create user tutorial (step-by-step guide)
- [ ] Performance testing (cascade on large hierarchy)
- [ ] End-to-end testing (complete workflow)

**Files:**
- `.workflows/planning.md` (update)
- `CLAUDE.md` (update)
- `docs/hierarchical-planning-tutorial.md` (new)
- `docs/performance-benchmarks.md` (new)

**Testing:**
- Complete workflow test: act → chapters → scenes → generation
- Performance test: cascade with 20 chapters, 200 scenes
- Stress test: regenerate act, verify all children invalidated
- User acceptance testing (manual)

---

## 9. Risk Analysis & Mitigation

### Risk 1: MCP Server Complexity

**Risk:** Extended MCP server becomes too complex, hard to maintain

**Impact:** High (single point of failure for entire system)

**Mitigation:**
- Modular design: Separate planning state from generation state logically
- Comprehensive unit tests (>80% coverage)
- JSON fallback ensures system works even if SQLite breaks
- Documentation: Clear module boundaries and responsibilities

**Monitoring:**
- Track MCP server error rate (should be <1%)
- Monitor response times for tools (<100ms avg)
- Log all tool calls for debugging

---

### Risk 2: Hook Execution Overhead

**Risk:** 4 new hooks slow down every file write

**Impact:** Medium (user-facing latency)

**Mitigation:**
- Hooks run in <100ms each (total <400ms overhead)
- Non-blocking hooks (consistency_check, state_sync) never slow down workflow
- Caching: MCP tools cache frequently accessed state (30s TTL)
- Async writes: State sync happens in background

**Monitoring:**
- Log hook execution times
- Alert if any hook takes >200ms
- Profile slow hooks and optimize

---

### Risk 3: Cascade Invalidation Bugs

**Risk:** Cascade marks wrong entities or misses entities

**Impact:** High (data integrity)

**Mitigation:**
- Transaction-based cascade (all-or-nothing)
- Recursive CTE tested with unit tests (edge cases)
- Manual /check-state-consistency command to detect issues
- /rebuild-state emergency recovery

**Testing:**
- Unit tests for cascade algorithm (10+ test cases)
- Integration tests with real file structures
- Edge cases: orphan entities, circular dependencies (should never happen), deep hierarchies (10 levels)

---

### Risk 4: State Drift (File ≠ MCP State)

**Risk:** File content changes outside of hooks (manual edits)

**Impact:** Medium (state becomes unreliable)

**Mitigation:**
- Hooks run on every Write/Edit (catches most changes)
- /check-state-consistency command detects drift
- /sync-version-hashes command fixes drift automatically
- Documentation warns against manual edits

**Monitoring:**
- Periodic consistency checks (cron job? manual?)
- Log warnings when state_sync fails

---

### Risk 5: Performance at Scale

**Risk:** System slow with 1000+ scenes (future growth)

**Impact:** Low (current scale is 50-100 entities per act)

**Mitigation:**
- SQLite handles 10,000+ rows easily (our scale is 100-300)
- Indexed queries for fast lookups
- Future: Shard by act (separate DB per act)
- Future: Archive old acts to separate storage

**Benchmarks:**
- Cascade 200 entities: <100ms
- Get hierarchy tree: <50ms
- Update state: <10ms

---

### Risk 6: User Confusion (Complex Hierarchy)

**Risk:** Users don't understand hierarchy requirements

**Impact:** Medium (user experience)

**Mitigation:**
- Clear error messages with actionable steps
- Tutorial documentation with examples
- `/show-hierarchy` command visualizes structure
- Gradual rollout: Start with acts, then chapters, then scenes

**User Education:**
- Step-by-step tutorial in docs
- Example workflow with screenshots
- FAQ for common errors

---

## 10. Testing Strategy

### 10.1 Unit Tests

**MCP Tools:**
```python
# tests/test_mcp_planning_state.py

def test_get_entity_state_returns_correct_data():
    # Setup: Create entity in DB
    db.insert_entity("chapter", "chapter-02", "approved", "hash123", "/path/to/file")

    # Test
    result = mcp.get_entity_state("chapter", "chapter-02")

    # Assert
    assert result["entity_id"] == "chapter-02"
    assert result["status"] == "approved"
    assert result["version_hash"] == "hash123"

def test_cascade_invalidate_marks_all_children():
    # Setup: Create hierarchy
    db.insert_entity("act", "act-1", "approved", "hash1", "/path")
    db.insert_entity("chapter", "chapter-01", "approved", "hash2", "/path", parent_id="act-1")
    db.insert_entity("scene", "scene-0101", "approved", "hash3", "/path", parent_id="chapter-01")
    db.insert_entity("scene", "scene-0102", "approved", "hash4", "/path", parent_id="chapter-01")

    # Test
    result = mcp.cascade_invalidate("chapter", "chapter-01", "test_reason")

    # Assert
    assert len(result["invalidated_entities"]) == 2  # 2 scenes
    assert db.get_status("scene-0101") == "requires-revalidation"
    assert db.get_status("scene-0102") == "requires-revalidation"
```

**Hooks:**
```python
# tests/test_hooks.py

def test_hierarchy_validation_blocks_unapproved_parent():
    # Setup: Create act with status=draft
    mcp.update_entity_state("act", "act-1", "draft", "hash1", "/path")

    # Test: Try to plan chapter
    event = {
        "tool_name": "Task",
        "tool_input": {"prompt": "/plan-chapter 1"}
    }

    exit_code = run_hook("hierarchy_validation_hook.py", event)

    # Assert
    assert exit_code == 1  # Blocked

def test_consistency_check_warns_on_character_mismatch():
    # Setup: Create parent and child with different characters
    create_file("act-plan.md", "Characters: Alice, Bob")
    create_file("chapter-plan.md", "Characters: Alice, Charlie")

    # Test
    event = {
        "tool_name": "Write",
        "tool_input": {"file_path": "chapter-plan.md"}
    }

    output = run_hook("consistency_check_hook.py", event)

    # Assert
    assert "Charlie" in output  # Warning about extra character
```

### 10.2 Integration Tests

**End-to-End Workflow:**
```python
# tests/integration/test_hierarchical_planning.py

def test_complete_planning_workflow():
    """
    Test: Act → Chapter → Scene → Generation
    """
    # 1. Plan act
    run_command("/plan-act 1")
    assert file_exists("acts/act-1/strategic-plan.md")
    assert mcp.get_status("act-1") == "draft"

    # 2. Try to plan chapter (should fail - not approved)
    result = run_command("/plan-chapter 1")
    assert "not approved" in result.error

    # 3. Approve act
    run_command("/approve-plan act 1")
    assert mcp.get_status("act-1") == "approved"

    # 4. Plan chapter (should succeed)
    run_command("/plan-chapter 1")
    assert file_exists("acts/act-1/chapters/chapter-01/plan.md")
    assert mcp.get_status("chapter-01") == "draft"

    # 5. Approve chapter
    run_command("/approve-plan chapter 1")

    # 6. Plan scene
    run_command("/plan-scene 0101")
    assert file_exists("acts/act-1/chapters/chapter-01/scenes/scene-0101-blueprint.md")

    # 7. Approve scene
    run_command("/approve-plan scene 0101")

    # 8. Generate scene
    run_command("Generate scene 0101")
    assert file_exists("acts/act-1/chapters/chapter-01/content/scene-0101.md")
```

**Invalidation Cascade:**
```python
def test_chapter_regeneration_invalidates_scenes():
    # Setup: Create chapter with 5 approved scenes
    setup_chapter_with_scenes("chapter-01", num_scenes=5)

    # Test: Regenerate chapter
    run_command("/plan-chapter 1")  # Triggers regeneration

    # Assert: All scenes invalidated
    for i in range(1, 6):
        scene_id = f"scene-010{i}"
        assert mcp.get_status(scene_id) == "requires-revalidation"

    # Verify backups created
    assert file_exists("backups/plan-{timestamp}.md")
```

### 10.3 Performance Tests

**Benchmark:**
```python
# tests/performance/test_cascade_performance.py

def test_cascade_performance_large_hierarchy():
    """
    Test cascade with 20 chapters, 200 scenes (large act).
    Target: <500ms
    """
    # Setup
    setup_act_with_chapters_and_scenes(
        act="act-1",
        num_chapters=20,
        scenes_per_chapter=10  # Total: 200 scenes
    )

    # Test
    start = time.time()
    mcp.cascade_invalidate("act", "act-1", "benchmark")
    duration = time.time() - start

    # Assert
    assert duration < 0.5  # Less than 500ms
    assert count_invalidated() == 220  # 20 chapters + 200 scenes
```

### 10.4 Manual Testing Checklist

**User Acceptance Testing:**

- [ ] User can plan act, chapter, scene in sequence
- [ ] User receives clear error when skipping hierarchy levels
- [ ] User sees parent context when planning chapter/scene
- [ ] User can approve plans and see status change
- [ ] User regenerates chapter, sees invalidation warning
- [ ] User revalidates scenes after chapter change
- [ ] User restores old version, sees cascade invalidation
- [ ] User views hierarchy tree with /show-hierarchy
- [ ] User recovers from MCP server crash using fallback
- [ ] User rebuilds state after corruption

---

## 11. Open Questions Resolution

### Q1: MCP Server Architecture

**RESOLVED:** Extend FEAT-0002 server with planning state

### Q2: Resource URIs

**RESOLVED:** Single namespace `state://planning/{type}/{id}`

### Q3: State Storage

**RESOLVED:** SQLite primary, JSON fallback

### Q4: Hook Execution Order

**RESOLVED:** Sequential, registration order, documented in Section 2.2

### Q5: Data Passing Between Hooks

**RESOLVED:** Hooks don't pass data directly; each reads from MCP independently

### Q6: Agent Prompt Injection

**RESOLVED:** Prompt preprocessing at coordinator level, agents unmodified

### Q7: Agent Isolation

**RESOLVED:** Maintained via artifact-based context injection, no agent changes

### Q8: Version Hash Calculation

**RESOLVED:** SHA-256 of file content

### Q9: Graceful Degradation

**RESOLVED:** JSON fallback, documented in Section 7.1-7.4

### Q10: Command Structure

**RESOLVED:** Separate commands `/plan-act`, `/plan-chapter`, `/plan-scene`

### Q11: Backward Compatibility

**RESOLVED:** Keep `/plan-story` with routing to new commands

### Q12: Cascading Behavior Scope

**RESOLVED:** Deep cascade (all descendants invalidated)

### Q13: Approval Workflow

**RESOLVED:** Manual approval required, warnings logged but don't block

---

## 12. Success Criteria

The implementation is successful when:

✅ **Hierarchy Enforcement:**
- Cannot plan chapter without approved act (hard block)
- Cannot plan scene without approved chapter (hard block)
- Clear error messages with actionable steps

✅ **Parent Context Flow:**
- Chapter planning receives full act plan automatically
- Scene planning receives full chapter plan automatically
- Agents generate content aligned with parent plans

✅ **Invalidation Cascade:**
- Regenerating parent marks all children as requires-revalidation
- Backups created automatically before regeneration
- Transaction-based cascade (all-or-nothing)

✅ **State Tracking:**
- All entities tracked in MCP (status, version, parent links)
- File changes synced to MCP automatically via hooks
- State survives MCP restart (JSON fallback)

✅ **Version Management:**
- Backups created with timestamps
- Can restore old versions
- Can diff versions

✅ **Recovery:**
- System works with MCP server unavailable (JSON fallback)
- Can rebuild state from file system
- Can detect and repair inconsistencies

✅ **Performance:**
- Hooks add <400ms overhead per operation
- Cascade 200 entities in <500ms
- MCP tools respond in <100ms

✅ **User Experience:**
- Commands are intuitive (/plan-act, /plan-chapter, /plan-scene)
- Error messages are actionable
- /show-hierarchy visualizes structure
- Tutorial documentation guides users

---

## 13. Appendix

### A. Complete File Structure

```
/project-root
├── mcp-servers/
│   ├── generation_state_mcp.py          # Extended MCP server
│   ├── planning_state_schema.sql        # SQLite schema
│   ├── requirements.txt
│   └── tests/
│       └── test_planning_state.py
│
├── .claude/
│   ├── hooks/
│   │   ├── hierarchy_validation_hook.py
│   │   ├── consistency_check_hook.py
│   │   ├── invalidation_cascade_hook.py
│   │   └── state_sync_hook.py
│   ├── hooks.config.json                # Hook registration
│   ├── commands/
│   │   ├── plan-act.md
│   │   ├── plan-chapter.md
│   │   ├── plan-scene.md
│   │   ├── approve-plan.md
│   │   ├── revalidate-scene.md
│   │   ├── list-versions.md
│   │   ├── restore-version.md
│   │   ├── rebuild-state.md
│   │   └── show-hierarchy.md
│   └── agents/
│       └── planning/
│           └── planning-coordinator.md  # (No changes needed)
│
├── workspace/
│   ├── planning-state.db                # SQLite database
│   ├── planning-state/                  # JSON fallback
│   │   ├── acts/
│   │   ├── chapters/
│   │   └── scenes/
│   └── logs/
│       └── mcp-planning-state.log
│
├── features/FEAT-0003-hierarchical-planning/
│   ├── README.md                        # Feature Brief
│   └── technical-design.md              # This document
│
└── docs/
    ├── hierarchical-planning-tutorial.md
    ├── emergency-recovery.md
    └── performance-benchmarks.md
```

### B. State Schema (Complete)

```sql
-- See Section 1.3 for full schema
```

### C. MCP Tool Signatures (Complete)

```typescript
// See Section 1.2.1 for full tool signatures
```

### D. Hook Pseudocode (Complete)

```python
# See Section 2.3 for full hook implementations
```

---

**END OF TECHNICAL DESIGN**

This document provides the complete technical architecture for FEAT-0003. Implementation can proceed in 7 phases over approximately 7 weeks.

**Next Steps:**
1. Review and approve this design
2. Begin Phase 1 (MCP Server Extension)
3. Iterative implementation and testing
4. User acceptance testing
5. Documentation and tutorial creation
6. Production deployment
