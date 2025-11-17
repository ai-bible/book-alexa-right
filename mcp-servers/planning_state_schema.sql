-- Planning State SQLite Schema for FEAT-0003
-- Hierarchical Planning Workflow (Act → Chapter → Scene)
--
-- This schema tracks the state of planning entities (acts, chapters, scenes)
-- with version management, parent-child relationships, and invalidation tracking.
--
-- Design: supports hierarchical planning with cascade invalidation
-- Storage: SQLite for performance, JSON for fallback
-- Created: 2025-11-11

-- Planning entities table
CREATE TABLE IF NOT EXISTS planning_entities (
    -- Primary keys
    entity_type TEXT NOT NULL,  -- 'act', 'chapter', 'scene'
    entity_id TEXT NOT NULL,    -- 'act-1', 'chapter-02', 'scene-0204'

    -- Status tracking
    status TEXT NOT NULL,       -- 'draft', 'approved', 'requires-revalidation', 'invalid'
    version_hash TEXT NOT NULL, -- SHA-256 of file content (64 chars)
    previous_version_hash TEXT, -- Previous version for tracking changes

    -- File system mapping
    file_path TEXT NOT NULL,    -- Absolute path to planning file

    -- Hierarchy relationships
    parent_id TEXT,             -- Parent entity_id (NULL for acts)
    parent_version_hash TEXT,   -- Version hash of parent when created

    -- Invalidation tracking
    invalidation_reason TEXT,   -- Why marked requires-revalidation
    invalidated_at TEXT,        -- ISO 8601 timestamp when invalidated

    -- Timestamps
    created_at TEXT NOT NULL,   -- ISO 8601 timestamp when first created
    updated_at TEXT NOT NULL,   -- ISO 8601 timestamp of last update

    -- Flexible metadata (JSON blob)
    metadata JSON,              -- Extra data (initiated_by, word_count, etc.)

    -- Constraints
    PRIMARY KEY (entity_type, entity_id)
    -- Note: FOREIGN KEY on parent_id would require compound key, handled in application
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_parent_lookup
    ON planning_entities(parent_id);

CREATE INDEX IF NOT EXISTS idx_status_lookup
    ON planning_entities(status);

CREATE INDEX IF NOT EXISTS idx_version_hash
    ON planning_entities(version_hash);

CREATE INDEX IF NOT EXISTS idx_entity_type
    ON planning_entities(entity_type);

-- Composite index for hierarchy queries
CREATE INDEX IF NOT EXISTS idx_parent_type
    ON planning_entities(parent_id, entity_type);

-- Backup history table
CREATE TABLE IF NOT EXISTS planning_entity_backups (
    backup_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Entity identification
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,

    -- Version tracking
    version_hash TEXT NOT NULL,

    -- Backup file location
    backup_file_path TEXT NOT NULL,

    -- Backup metadata
    backed_up_at TEXT NOT NULL,  -- ISO 8601 timestamp
    reason TEXT,                 -- 'regeneration', 'manual', 'restore'

    -- Optional metadata
    metadata JSON                -- Extra info about backup
);

-- Index for backup lookups
CREATE INDEX IF NOT EXISTS idx_backup_entity
    ON planning_entity_backups(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_backup_timestamp
    ON planning_entity_backups(backed_up_at);

-- View: Get hierarchy tree for an act
-- This view helps with cascade operations and visualization
CREATE VIEW IF NOT EXISTS hierarchy_tree_view AS
WITH RECURSIVE tree AS (
    -- Base case: All acts (root level)
    SELECT
        entity_type,
        entity_id,
        status,
        parent_id,
        file_path,
        0 as level,
        entity_id as root_id
    FROM planning_entities
    WHERE entity_type = 'act'

    UNION ALL

    -- Recursive case: All children
    SELECT
        e.entity_type,
        e.entity_id,
        e.status,
        e.parent_id,
        e.file_path,
        t.level + 1,
        t.root_id
    FROM planning_entities e
    INNER JOIN tree t ON e.parent_id = t.entity_id
)
SELECT * FROM tree;

-- View: Get status summary by parent
CREATE VIEW IF NOT EXISTS status_summary_view AS
SELECT
    parent_id,
    entity_type,
    status,
    COUNT(*) as count
FROM planning_entities
WHERE parent_id IS NOT NULL
GROUP BY parent_id, entity_type, status;

-- Sample queries for common operations:

-- 1. Get all descendants of an entity (for cascade invalidation)
-- WITH RECURSIVE descendants AS (
--     SELECT * FROM planning_entities WHERE entity_type = ? AND entity_id = ?
--     UNION ALL
--     SELECT e.* FROM planning_entities e
--     INNER JOIN descendants d ON e.parent_id = d.entity_id
-- )
-- SELECT * FROM descendants WHERE NOT (entity_type = ? AND entity_id = ?);

-- 2. Get children status summary
-- SELECT status, COUNT(*) FROM planning_entities
-- WHERE parent_id = ? GROUP BY status;

-- 3. Get entity with parent info
-- SELECT
--     e.*,
--     p.status as parent_status,
--     p.version_hash as parent_version
-- FROM planning_entities e
-- LEFT JOIN planning_entities p ON e.parent_id = p.entity_id
-- WHERE e.entity_type = ? AND e.entity_id = ?;

-- 4. Find orphan entities (parent missing)
-- SELECT e.* FROM planning_entities e
-- WHERE e.parent_id IS NOT NULL
-- AND NOT EXISTS (
--     SELECT 1 FROM planning_entities p WHERE p.entity_id = e.parent_id
-- );

-- 5. Get backup history for entity
-- SELECT * FROM planning_entity_backups
-- WHERE entity_type = ? AND entity_id = ?
-- ORDER BY backed_up_at DESC;
