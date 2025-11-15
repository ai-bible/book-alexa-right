# Command: /list-versions

List backup version history for a planning entity.

**Usage**: `/list-versions <entity_type> <entity_id>`

**Examples**:
- `/list-versions act 1` - List all backups for Act 1
- `/list-versions chapter 02` - List all backups for Chapter 02
- `/list-versions scene 0204` - List all backups for Scene 0204

---

## Purpose

View backup history for a planning entity, including timestamps, reasons, and version hashes.

Useful for:
- Understanding version history
- Finding backups to restore
- Comparing versions
- Verifying backup creation

---

## Workflow

### Step 1: Extract and validate parameters

Extract from command:
- `<entity_type>` - Required ('act', 'chapter', or 'scene')
- `<entity_id>` - Required (entity ID without prefixes)

**Normalization**:
- act: `1` → `act-1`
- chapter: `02` → `chapter-02`
- scene: `0204` → `scene-0204`

### Step 2: Call MCP tool

Use `list_backups(entity_type=..., entity_id=...)` to get backup history.

### Step 3: Display results

Show formatted backup history:

```
📦 BACKUP HISTORY: {entity_type}/{entity_id}

Found {count} backup(s):

**ID: 45** | 2025-11-12 16:30:00 | regeneration | ✓ exists
  File: acts/act-1/chapters/chapter-02/backups/plan-2025-11-12-16-30-00.md
  Version: f9e8d7c6...

**ID: 42** | 2025-11-12 15:30:45 | manual | ✓ exists
  File: acts/act-1/chapters/chapter-02/backups/plan-2025-11-12-15-30-45.md
  Version: a1b2c3d4...

**ID: 38** | 2025-11-11 14:20:30 | restore | ✓ exists
  File: acts/act-1/chapters/chapter-02/backups/plan-2025-11-11-14-20-30.md
  Version: b3c4d5e6...

💡 To restore a backup:
  /restore-version {entity_type} {entity_id_number} <backup_id>

💡 To compare backups:
  /diff-version <backup_id1> <backup_id2>
```

**If no backups found**:
```
📦 BACKUP HISTORY: {entity_type}/{entity_id}

No backups found for this entity.

💡 Create a backup manually:
  create_backup(entity_type='{entity_type}', entity_id='{entity_id}')

Automatic backups are created when:
  - Regenerating plans (via /plan-* commands)
  - Restoring previous versions
```

---

## Error Handling

### Invalid entity type
```
❌ Error: Invalid entity type '{input}'

Entity type must be one of: act, chapter, scene

Usage: /list-versions <entity_type> <entity_id>
```

### Entity not found
```
❌ Error: Entity not found

Entity: {entity_type} '{entity_id}'

This entity doesn't exist in the planning state.

Action required:
  1. Check if the entity was created
  2. If entity exists but not tracked, run: /rebuild-state
```

### MCP unavailable
```
❌ ERROR: Planning state system unavailable

The MCP planning state server is not available.

Action required:
  1. Check MCP server status
  2. Verify planning_state_utils.py is working
```

---

## Related Commands

- `/restore-version <entity_type> <entity_id> <backup_id>` - Restore a backup version
- `/diff-version <backup_id1> <backup_id2>` - Compare two backups
- `create_backup()` - Create manual backup (MCP tool)
- `list_backups()` - Underlying MCP tool

---

## Technical Details

**MCP Tool**: `list_backups(entity_type, entity_id)`

**Backup Reasons**:
- `regeneration`: Created when regenerating plans
- `manual`: Created manually via create_backup()
- `restore`: Created as safety backup before restoring

**File Status**:
- ✓ exists: Backup file present on disk
- ✗ MISSING: Backup logged but file not found (may have been deleted)

**Sorting**: Backups listed newest first (most recent at top)
