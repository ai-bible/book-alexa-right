# Command: /diff-version

Compare two backup versions with unified diff.

**Usage**: `/diff-version <backup_id1> <backup_id2>`

**Examples**:
- `/diff-version 42 45` - Compare backup #42 (older) with backup #45 (newer)
- `/diff-version 38 42` - Compare backup #38 with backup #42

---

## Purpose

View differences between two backup versions of the same planning entity.

**Use cases**:
- Understand what changed between versions
- Decide which version to restore
- Review evolution of plans
- Identify when specific changes were made
- Validate regeneration results

---

## Workflow

### Step 1: Extract and validate parameters

Extract from command:
- `<backup_id1>` - Required (positive integer, typically older version)
- `<backup_id2>` - Required (positive integer, typically newer version)

**Validation**:
- Both must be positive integers
- Both must exist in backup database
- Both must be from the same entity

### Step 2: Call MCP tool

Use `get_backup_diff(backup_id1=..., backup_id2=...)` to generate unified diff.

### Step 3: Display results

Show comprehensive comparison:

```
📊 BACKUP COMPARISON

**Backup #42** (older):
  Entity: chapter/chapter-02
  Date: 2025-11-12 15:30:45
  Version: a1b2c3d4...
  File: acts/act-1/chapters/chapter-02/backups/plan-2025-11-12-15-30-45.md

**Backup #45** (newer):
  Entity: chapter/chapter-02
  Date: 2025-11-12 16:30:00
  Version: f9e8d7c6...
  File: acts/act-1/chapters/chapter-02/backups/plan-2025-11-12-16-30-00.md

═══════════════════════════════════════════════════════════
UNIFIED DIFF
═══════════════════════════════════════════════════════════

--- chapter-02 (backup 42, 2025-11-12 15:30:45)
+++ chapter-02 (backup 45, 2025-11-12 16:30:00)
@@ -15,7 +15,7 @@

 ## Chapter Objective

-Establish Alex's motivation for investigating the anomaly
+Establish Alex's motivation and introduce the time distortion mystery

 ## Scene Breakdown

@@ -45,6 +45,12 @@
   - Setting: Upper city observation deck
   - Purpose: Introduce time cascade phenomenon

+### Scene 3: Investigation Begins
+  - Characters: Alex, Mira
+  - Setting: Archive level
+  - Purpose: Reveal historical context
+
 ## Thematic Elements

═══════════════════════════════════════════════════════════

**Legend**:
  - Lines: Lines starting with "-" were removed
  + Lines: Lines starting with "+" were added
  @@ Lines: Show line number context

  Unchanged lines are shown for context

💡 Actions you can take:
  - Restore older version: /restore-version chapter 02 42
  - Restore newer version: /restore-version chapter 02 45
  - List all versions: /list-versions chapter 02
```

**If files are identical**:
```
📊 BACKUP COMPARISON

**Backup #42** (older):
  Entity: chapter/chapter-02
  Date: 2025-11-12 15:30:45
  Version: a1b2c3d4...

**Backup #45** (newer):
  Entity: chapter/chapter-02
  Date: 2025-11-12 16:30:00
  Version: a1b2c3d4...

═══════════════════════════════════════════════════════════
UNIFIED DIFF
═══════════════════════════════════════════════════════════

No differences found - files are identical.

💡 Both backups have the same content (same version hash).
This may happen if:
  - Backup created without file changes
  - File restored to previous version
  - Manual backup created for safety
```

---

## Error Handling

### Invalid backup IDs
```
❌ Error: Invalid backup ID

Backup IDs must be positive integers.

Usage: /diff-version <backup_id1> <backup_id2>
Examples:
  /diff-version 42 45
  /diff-version 38 42
```

### Backup not found
```
❌ Error: Backup not found

Backup #{backup_id} not found in database.

Check available backups:
  - Use /list-versions to see all backups
  - Ensure backup ID is correct
```

### Different entities
```
❌ Error: Backups from different entities

Backup #42: chapter/chapter-02
Backup #45: scene/scene-0204

Cannot compare backups from different entities.

To compare versions:
  1. Use /list-versions to find backups for the same entity
  2. Select two backup IDs from the same entity
```

### Backup file missing
```
❌ Error: Backup file not found

Backup #{backup_id} exists in database but file is missing:
  Expected: {backup_file_path}

The backup file may have been deleted or moved.

Options:
  1. Check backups/ directory manually
  2. Try a different backup ID
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

## Diff Reading Guide

### Unified Diff Format

```
--- chapter-02 (backup 42, 2025-11-12 15:30:45)
+++ chapter-02 (backup 45, 2025-11-12 16:30:00)
```
- `---` line: Older version (backup_id1)
- `+++` line: Newer version (backup_id2)

```
@@ -15,7 +15,7 @@
```
- `@@` markers: Show line number ranges
- `-15,7`: In old file, starting at line 15, showing 7 lines
- `+15,7`: In new file, starting at line 15, showing 7 lines

```
 Unchanged line
-Removed line (was in old version)
+Added line (new in new version)
```
- No prefix: Line unchanged in both versions (shown for context)
- `-` prefix: Line exists in old version, removed in new version
- `+` prefix: Line added in new version, didn't exist in old version

### Example Interpretation

```diff
@@ -20,3 +20,5 @@
 ## Scene Breakdown

 ### Scene 1: Discovery
+### Scene 2: Confrontation
+### Scene 3: Resolution
```

**Interpretation**:
- Lines 20-22 unchanged (Scene Breakdown header, blank line, Scene 1)
- Two new scenes added after Scene 1
- Old file had 3 lines in this section
- New file has 5 lines in this section

---

## Use Cases

### Before Restoring

Compare current with backup before restoring:

```bash
# 1. Get backup IDs
/list-versions chapter 02

# 2. Compare current version with backup
# (current version has most recent backup ID)
/diff-version 45 42

# 3. Decide which to restore based on diff
/restore-version chapter 02 42  # if older version is better
```

### After Regeneration

Compare regenerated version with original:

```bash
# 1. Regenerate creates backup of old version
/plan-chapter 2  # choose "regenerate"

# 2. Get backup IDs
/list-versions chapter 02

# 3. Compare old vs new
/diff-version <old_backup_id> <new_backup_id>

# 4. Restore old if new isn't better
/restore-version chapter 02 <old_backup_id>
```

### Version Evolution

Track how plan evolved over time:

```bash
# 1. List all versions
/list-versions chapter 02

# 2. Compare sequential versions
/diff-version 42 45  # first → second
/diff-version 45 48  # second → third
/diff-version 48 51  # third → fourth

# 3. Or compare first → latest
/diff-version 42 51  # see all changes
```

---

## Notes

- **Read-only**: This command doesn't modify any files
- **Context**: Shows surrounding unchanged lines for context
- **Large diffs**: For very large diffs, consider viewing files directly
- **Binary files**: Only works with text files (markdown)
- **Line-based**: Compares line by line, not word by word

---

## Related Commands

- `/list-versions <entity_type> <entity_id>` - View backup history to find backup IDs
- `/restore-version <entity_type> <entity_id> <backup_id>` - Restore a version after comparing
- `get_backup_diff()` - Underlying MCP tool

---

## Technical Details

**MCP Tool**: `get_backup_diff(backup_id1, backup_id2)`

**Diff Algorithm**: Python's `difflib.unified_diff()`
- Standard unified diff format
- Shows context lines (unchanged)
- Line-based comparison
- Format compatible with patch tools

**Validation**:
- Both backups must exist
- Both must be from same entity (same entity_type + entity_id)
- Files must be readable

**Output**:
- Unified diff with 3 lines of context by default
- Entity metadata (type, ID, timestamps, versions)
- Legend for reading diff markers
- Suggested actions based on comparison

**Performance**:
- Efficient for typical planning files (<1000 lines)
- May be slow for very large files (>10,000 lines)
- Entire files loaded into memory for comparison
