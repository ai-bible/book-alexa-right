# Command: /rebuild-state

Rebuild MCP planning state from existing files on disk.

**Usage**: `/rebuild-state [--dry-run]`

**Examples**:
- `/rebuild-state` - Rebuild state from all planning files
- `/rebuild-state --dry-run` - Show what would be rebuilt without making changes

---

## Purpose

Reconstructs the MCP planning state database from planning files on disk.

**Use cases**:
- Recovering from database corruption
- Migrating existing plans to hierarchical tracking
- Syncing state after manual file edits
- Initial setup of FEAT-0003 on existing project
- Fixing state inconsistencies

**Safety**: Non-destructive - only reads files and updates database

---

## Workflow

### Step 1: Scan for planning files

Scan the `acts/` directory for all planning files:

**File patterns**:
- Acts: `acts/act-*/strategic-plan.md`
- Chapters: `acts/act-*/chapters/chapter-*/plan.md`
- Scenes: `acts/act-*/chapters/chapter-*/scenes/scene-*-blueprint.md`

Collect all matching files with their paths.

### Step 2: Extract entity information

For each file, extract:
- Entity type (act, chapter, scene)
- Entity ID
- Parent ID (if applicable)
- File path (absolute)

**Validation**:
- File must exist and be readable
- Path must match expected pattern
- Entity ID must be extractable from path

### Step 3: Calculate version hashes

For each file:
- Read file content
- Calculate SHA-256 hash
- Store as version_hash

This creates a baseline snapshot of current file state.

### Step 4: Determine parent version hashes

For entities with parents:
- Find parent entity in collected files
- Get parent's version_hash
- Store as parent_version_hash

This establishes the hierarchy relationships.

### Step 5: Set initial status

Determine initial status for each entity:

**Rules**:
- If entity already exists in state → preserve existing status
- If new entity → set to 'draft'

**Rationale**: Preserve existing workflow progress (approved entities stay approved)

### Step 6: Show rebuild preview (if --dry-run)

Display what would be created/updated:

```
🔍 REBUILD STATE PREVIEW (DRY RUN)

Scanned: acts/ directory
Found: 15 planning files

═══════════════════════════════════════════════════════════
ACTS (2 files)
═══════════════════════════════════════════════════════════

✓ act-1
  File: acts/act-1/strategic-plan.md
  Hash: a1b2c3d4...
  Status: draft (new)

✓ act-2
  File: acts/act-2/strategic-plan.md
  Hash: e5f6g7h8...
  Status: approved (existing)

═══════════════════════════════════════════════════════════
CHAPTERS (5 files)
═══════════════════════════════════════════════════════════

✓ chapter-01 (parent: act-1)
  File: acts/act-1/chapters/chapter-01/plan.md
  Hash: i9j0k1l2...
  Parent hash: a1b2c3d4...
  Status: draft (new)

✓ chapter-02 (parent: act-1)
  File: acts/act-1/chapters/chapter-02/plan.md
  Hash: m3n4o5p6...
  Parent hash: a1b2c3d4...
  Status: approved (existing)

[... more chapters ...]

═══════════════════════════════════════════════════════════
SCENES (8 files)
═══════════════════════════════════════════════════════════

✓ scene-0101 (parent: chapter-01)
  File: acts/act-1/chapters/chapter-01/scenes/scene-0101-blueprint.md
  Hash: q7r8s9t0...
  Parent hash: i9j0k1l2...
  Status: draft (new)

[... more scenes ...]

═══════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════

Total entities: 15
  - Acts: 2
  - Chapters: 5
  - Scenes: 8

New entities: 10 (will be created)
Existing entities: 5 (will be updated)

Run without --dry-run to apply changes.
```

If --dry-run, stop here. Otherwise, proceed to Step 7.

### Step 7: Rebuild state database

For each entity (in hierarchy order: acts → chapters → scenes):

1. Check if entity exists in database
2. If exists → update with new hash/path
3. If new → create with draft status
4. Link to parent (parent_id, parent_version_hash)
5. Log operation

**Transaction**: Use SQLite transaction for all-or-nothing operation

### Step 8: Display results

Show rebuild summary:

```
✅ STATE REBUILD COMPLETE

Processed: 15 files
  - Acts: 2
  - Chapters: 5
  - Scenes: 8

Created: 10 new entities
Updated: 5 existing entities

═══════════════════════════════════════════════════════════
CREATED
═══════════════════════════════════════════════════════════

Acts:
  - act-1 (draft)

Chapters:
  - chapter-01 (draft, parent: act-1)
  - chapter-03 (draft, parent: act-1)
  - chapter-04 (draft, parent: act-2)

Scenes:
  - scene-0101 (draft, parent: chapter-01)
  - scene-0102 (draft, parent: chapter-01)
  - scene-0301 (draft, parent: chapter-03)
  - scene-0401 (draft, parent: chapter-04)
  - scene-0402 (draft, parent: chapter-04)
  - scene-0403 (draft, parent: chapter-04)

═══════════════════════════════════════════════════════════
UPDATED
═══════════════════════════════════════════════════════════

Acts:
  - act-2 (approved) - hash updated

Chapters:
  - chapter-02 (approved, parent: act-1) - hash updated

Scenes:
  - scene-0201 (approved, parent: chapter-02) - hash updated
  - scene-0202 (approved, parent: chapter-02) - hash updated

═══════════════════════════════════════════════════════════
NEXT STEPS
═══════════════════════════════════════════════════════════

New entities are in 'draft' status. To enable hierarchical planning:

1. Review and approve acts:
   approve_entity(entity_type='act', entity_id='act-1')

2. Review and approve chapters:
   approve_entity(entity_type='chapter', entity_id='chapter-01')

3. Review and approve scenes:
   approve_entity(entity_type='scene', entity_id='scene-0101')

💡 Use /show-hierarchy to visualize the hierarchy
```

---

## Error Handling

### No planning files found

```
❌ ERROR: No planning files found

Searched: acts/ directory

Expected file patterns:
  - acts/act-*/strategic-plan.md
  - acts/act-*/chapters/chapter-*/plan.md
  - acts/act-*/chapters/chapter-*/scenes/scene-*-blueprint.md

Action required:
  1. Check that planning files exist in acts/ directory
  2. Verify file naming follows expected patterns
  3. Create planning files if needed
```

### File read errors

```
⚠️  WARNING: Some files could not be read

Skipped files:
  - acts/act-1/strategic-plan.md (permission denied)
  - acts/act-2/chapters/chapter-01/plan.md (file not found)

Successfully processed: 13 / 15 files

Rebuild completed with warnings.
```

### Database errors

```
❌ ERROR: Database operation failed

Failed during: Creating entity 'chapter-02'
Reason: {error_message}

State may be partially rebuilt. Check database:
  workspace/planning-state.db

Recovery options:
  1. Delete database and retry: rm workspace/planning-state.db
  2. Check file permissions
  3. Verify disk space available
```

### MCP unavailable

```
❌ ERROR: Planning state system unavailable

The MCP planning state module is not available.

This command requires:
  - mcp-servers/planning_state_utils.py
  - mcp-servers/generation_state_mcp.py running

Action required:
  1. Verify MCP server is running
  2. Check planning_state_utils.py exists
  3. Review MCP server logs
```

---

## Advanced Usage

### Rebuild specific act

Currently rebuilds entire state. For targeted rebuild:

1. Use /rebuild-state to rebuild all
2. Then manually adjust specific entities via MCP tools

### Preserve custom status

By default, preserves existing entity statuses. To reset all to draft:

1. Delete database: `rm workspace/planning-state.db`
2. Run rebuild
3. Manually approve entities

### Dry run analysis

Use --dry-run to:
- Verify file structure before committing
- Check what would change
- Identify missing parent files
- Validate file naming

---

## Notes

- **Non-destructive**: Only updates database, never modifies files
- **Idempotent**: Safe to run multiple times
- **Preserves status**: Existing approved entities stay approved
- **Transaction-safe**: All-or-nothing database operation
- **Performance**: Fast for typical project sizes (<100 entities)

---

## Related Commands

- `/show-hierarchy` - Visualize hierarchy after rebuild
- `get_entity_state()` - Check individual entity state
- `approve_entity()` - Approve entities after rebuild
- `sync_from_json_to_sqlite()` - Lower-level sync operation (MCP tool)

---

## Migration Workflow

For existing projects without hierarchical tracking:

```bash
# 1. Backup current state (if any)
cp -r workspace/planning-state workspace/planning-state.backup

# 2. Dry run to preview
/rebuild-state --dry-run

# 3. Review preview, verify expected structure

# 4. Execute rebuild
/rebuild-state

# 5. Visualize hierarchy
/show-hierarchy act-1

# 6. Approve entities as needed
approve_entity(entity_type='act', entity_id='act-1')
# ... continue with chapters and scenes

# 7. Begin using hierarchical planning
/plan-chapter 3  # Will enforce parent approval
```

---

## Technical Details

**File Scanning**: Uses glob patterns to find files
**Hash Calculation**: SHA-256 of file content (binary read)
**Parent Resolution**: Extracts from file path structure
**Status Preservation**: Queries existing state before update
**Transaction**: Single SQLite transaction for atomicity

**Performance**:
- 100 files: ~1-2 seconds
- 500 files: ~5-10 seconds
- Mostly I/O bound (reading files, calculating hashes)

**Database Schema**: See `mcp-servers/planning_state_schema.sql`
