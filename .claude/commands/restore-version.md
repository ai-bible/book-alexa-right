# Command: /restore-version

Restore a previous backup version of a planning file.

**Usage**: `/restore-version <entity_type> <entity_id> <backup_id>`

**Examples**:
- `/restore-version act 1 42` - Restore Act 1 to backup #42
- `/restore-version chapter 02 38` - Restore Chapter 02 to backup #38
- `/restore-version scene 0204 55` - Restore Scene 0204 to backup #55

---

## Purpose

Restore a planning entity to a previous version from backup history.

**Safety features**:
- Creates backup of current version before restoring
- Updates entity state with restored version hash
- Triggers cascade invalidation for child entities

**Use cases**:
- Undo recent changes
- Recover from mistakes
- Compare different approaches by switching versions
- Restore after accidental corruption

---

## Workflow

### Step 1: Extract and validate parameters

Extract from command:
- `<entity_type>` - Required ('act', 'chapter', or 'scene')
- `<entity_id>` - Required (entity ID without prefixes)
- `<backup_id>` - Required (positive integer)

**Normalization**:
- Entity type: Validate against ['act', 'chapter', 'scene']
- Entity ID: Format according to type (act-1, chapter-02, scene-0204)
- Backup ID: Must be positive integer

### Step 2: Show preview (optional but recommended)

Before restoring, show what will be restored:

```
📋 RESTORE PREVIEW

**Backup to restore**:
  Backup ID: {backup_id}
  Created: {backed_up_at}
  Reason: {reason}
  Version: {version_hash[:8]}...
  File: {backup_file_path}

**Current version**:
  Entity: {entity_type}/{entity_id}
  Current version: {current_version_hash[:8]}...
  Status: {current_status}
  File: {current_file_path}

**What will happen**:
  1. Current version will be backed up (safety measure)
  2. Backup #{backup_id} will replace current file
  3. Entity state will be updated with restored version hash
  4. If entity has children, they'll be marked requires-revalidation

⚠️  **WARNING**: This action is destructive (but reversible)

Proceed with restore? (y/n)
```

### Step 3: Wait for confirmation

If user confirms (y):
- Proceed with restore
If user cancels (n):
- Abort without changes

### Step 4: Call MCP tool

Use `restore_backup(entity_type=..., entity_id=..., backup_id=...)`.

### Step 5: Display results

**On success**:
```
✅ BACKUP RESTORED SUCCESSFULLY

**Entity**: {entity_type}/{entity_id}
**Restored from**: backup #{backup_id} ({backed_up_at})
**File**: {restored_from}
**Version**: {version_hash[:8]}...

**Current version backed up as**: backup #{new_backup_id}

⚠️  **WARNING**: Restoring older version may invalidate child plans

If this entity has approved children, they may need revalidation.
The invalidation_cascade_hook will mark descendants as requires-revalidation.

💡 Next steps:
  1. Review restored content: Read {file_path}
  2. Check if children need revalidation: /revalidate-all
  3. Approve if satisfied: /approve-plan {entity_type} {entity_id_number}

💡 To undo this restore:
  /restore-version {entity_type} {entity_id_number} {new_backup_id}
```

**On failure**:
```
❌ ERROR: Restore failed

Reason: {error_message}

{if backup not found:}
Backup #{backup_id} not found for {entity_type}/{entity_id}

Check available backups: /list-versions {entity_type} {entity_id_number}

{if entity not found:}
Entity {entity_type}/{entity_id} not found in planning state.

Run: /rebuild-state

{if file not found:}
Backup file not found on disk: {backup_file_path}

The backup may have been deleted. Check backups/ directory manually.
```

---

## Error Handling

### Invalid parameters
```
❌ Error: Invalid parameters

Usage: /restore-version <entity_type> <entity_id> <backup_id>

Parameters:
  entity_type: act, chapter, or scene
  entity_id: entity number/ID (1, 02, 0204, etc.)
  backup_id: positive integer from /list-versions

Examples:
  /restore-version act 1 42
  /restore-version chapter 02 38
  /restore-version scene 0204 55
```

### Backup not found
```
❌ Error: Backup #{backup_id} not found

Entity: {entity_type}/{entity_id}

Check available backups using:
  /list-versions {entity_type} {entity_id_number}
```

### Entity not found
See Step 5 error messages.

### Backup file missing
```
❌ Error: Backup file not found

Backup #{backup_id} is logged in database but file is missing:
  Expected path: {backup_file_path}

The backup file may have been:
  - Manually deleted
  - Moved to a different location
  - Lost due to disk issues

Recovery options:
  1. Check backups/ directory for similar files
  2. Restore from a different backup
  3. Regenerate the plan if no valid backups exist
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

## Special Cases

### Restoring triggers cascade invalidation

When restoring a parent entity (act or chapter), all descendants are marked `requires-revalidation`:

**Example**: Restoring Act 1
- Act 1 restored to older version
- All chapters in Act 1 → requires-revalidation
- All scenes in those chapters → requires-revalidation

**After restore**:
```
⚠️  CASCADE INVALIDATION TRIGGERED

Restored: act/act-1

Affected descendants (marked requires-revalidation):
  - chapter-01 (2 scenes)
  - chapter-02 (3 scenes)
  - chapter-03 (1 scene)

Total affected: 3 chapters, 6 scenes

Action required:
  1. Review all affected plans for alignment
  2. Run: /revalidate-all --act 1
  3. Approve or regenerate as needed
```

### Restoring scene (leaf node)

Scenes have no children, so no cascade invalidation:

```
✅ Scene restored successfully

Scene: scene-0204
No child entities affected (scenes are leaf nodes)

Next steps:
  1. Review restored blueprint
  2. Approve: /approve-plan scene 0204
  3. Generate prose: "Generate scene 0204"
```

---

## Notes

- **Reversible**: Current version always backed up before restore
- **Safe**: Confirmation required before destructive operation
- **Traceable**: Full audit trail in backup history
- **Cascade-aware**: Automatically invalidates affected descendants
- **Idempotent**: Can restore same version multiple times safely

---

## Related Commands

- `/list-versions <entity_type> <entity_id>` - View backup history
- `/diff-version <backup_id1> <backup_id2>` - Compare versions before restoring
- `/revalidate-all` - Revalidate descendants after restore
- `/approve-plan <entity_type> <entity_id>` - Approve restored version
- `restore_backup()` - Underlying MCP tool

---

## Technical Details

**MCP Tool**: `restore_backup(entity_type, entity_id, backup_id)`

**Restore Process**:
1. Validate backup exists
2. Create safety backup of current version
3. Copy backup file to current location
4. Update entity state with restored version hash
5. Trigger invalidation_cascade_hook (if parent entity)
6. Return success with new backup ID

**Safety Measures**:
- Current version backed up before restore (reason: 'restore')
- Backup logged to database for traceability
- State updated atomically
- Hook-based cascade invalidation

**State Changes**:
- `version_hash` updated to restored version
- `status` preserved (draft/approved/requires-revalidation)
- `updated_at` updated to restore timestamp
- Children marked `requires-revalidation` (if parent)
