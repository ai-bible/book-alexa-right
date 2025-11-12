# Command: /approve-plan

Approve a planning entity (act, chapter, or scene), changing its status from 'draft' to 'approved'.

**Usage**: `/approve-plan <entity_type> <entity_id>`

**Examples**:
- `/approve-plan act 1` - Approve Act 1
- `/approve-plan chapter 02` - Approve Chapter 02
- `/approve-plan scene 0204` - Approve Scene 0204

---

## Workflow

You are approving a hierarchical planning entity. Approval enables child planning and locks the entity version.

### Step 1: Extract and validate parameters

Extract from command:
- `<entity_type>` - Required ('act', 'chapter', or 'scene')
- `<entity_id>` - Required (entity ID without prefixes)

**Parameter Normalization**:
- Entity type: Validate against ['act', 'chapter', 'scene']
- Entity ID formatting:
  - act: `{number}` → `act-{number}` (e.g., `1` → `act-1`)
  - chapter: `{number}` → `chapter-{number:02d}` (e.g., `2` → `chapter-02`)
  - scene: `{scene_id}` → `scene-{scene_id}` (e.g., `0204` → `scene-0204`)

**Validation**:
- Entity type must be valid
- Entity ID must match expected format
- If invalid → show error and stop

### Step 2: Check entity exists

Use MCP tool `get_entity_state(entity_type=..., entity_id=...)` to check if entity exists.

**If entity NOT FOUND:**
```
❌ ERROR: Cannot approve - entity not found

Entity: {entity_type} '{entity_id}'

This entity doesn't exist in the planning state.

Action required:
  1. Check if the file exists
  2. If file exists but not in state, run: /rebuild-state
  3. If file doesn't exist, create it first:
     - For acts: /plan-act {act_number}
     - For chapters: /plan-chapter {chapter_number}
     - For scenes: /plan-scene {scene_id}
```
Stop execution.

**If entity EXISTS:**
Proceed to Step 3.

### Step 3: Check current status

Get current status from entity state.

**If status = 'approved':**
```
ℹ️  Entity already approved

Entity: {entity_type} '{entity_id}'
Status: approved
Version: {version_hash[:8]}...
Approved at: {updated_at}

No action needed - entity is already approved.
```
Stop execution (success - idempotent operation).

**If status = 'invalid':**
```
❌ ERROR: Cannot approve invalid entity

Entity: {entity_type} '{entity_id}'
Status: invalid

Invalid entities cannot be approved. They must be regenerated or replaced.

Action required:
  1. Regenerate the plan (creates new version)
  2. Then approve the new version
```
Stop execution.

**If status = 'draft' or 'requires-revalidation':**
Proceed to Step 4.

### Step 4: Check parent approved (if not top-level)

**For acts:**
- No parent - skip this step

**For chapters:**
- Extract act number from file path
- Use `get_entity_state(entity_type='act', entity_id='act-{act_number}')` to check parent
- If parent not found → error
- If parent status ≠ 'approved' → error (show parent status)

**For scenes:**
- Extract chapter number from scene_id (first 2 digits)
- Use `get_entity_state(entity_type='chapter', entity_id='chapter-{chapter_number}')` to check parent
- If parent not found → error
- If parent status ≠ 'approved' → error (show parent status)

**Error format if parent not approved:**
```
❌ ERROR: Cannot approve - parent not approved

Entity: {entity_type} '{entity_id}'
Parent: {parent_type} '{parent_id}'
Parent status: {parent_status}

Hierarchical planning requires parent approval before approving children.

Action required:
  1. Approve parent first: /approve-plan {parent_type} {parent_id_number}
  2. Then retry: /approve-plan {entity_type} {entity_id_number}
```
Stop execution.

**If parent approved (or no parent):**
Proceed to Step 5.

### Step 5: Run consistency checks

Check for potential issues that should be warned about (non-blocking):

**Check 1: Parent version mismatch**
- Compare `entity.parent_version_hash` with `parent.version_hash`
- If different → warning (parent has changed since entity created)

**Check 2: File hash mismatch**
- Calculate current file hash
- Compare with `entity.version_hash` in state
- If different → warning (file modified since last state sync)

**Check 3: Children status**
- If entity has approved children → info (they'll remain approved)

**Collect all warnings** and proceed to Step 6.

### Step 6: Show approval preview

Display summary with warnings:

```
📋 APPROVAL PREVIEW

Entity: {entity_type} '{entity_id}'
File: {file_path}
Current status: {current_status}
→ New status: approved

Version: {version_hash[:8]}...
Parent: {parent_id} (status: {parent_status}, version: {parent_version[:8]}...)

{if warnings:}
⚠️  WARNINGS:

  • Parent version has changed since this plan was created
    - Plan created with parent v{entity.parent_version_hash[:8]}...
    - Parent current version: v{parent.version_hash[:8]}...
    - **Recommendation**: Review parent plan and verify this plan is still aligned

  • File has been modified since last state sync
    - State version: v{entity.version_hash[:8]}...
    - File current version: v{calculated_hash[:8]}...
    - **Recommendation**: Review recent changes

{if children:}
ℹ️  This entity has {num_children} child(ren):
  - {child_1_id} (status: {child_1_status})
  - {child_2_id} (status: {child_2_status})
  ...

These children will remain unaffected by approval.

{end}

Approve this entity? (y/n/force)
  y = approve (if no critical warnings)
  n = cancel
  force = approve even with warnings
```

### Step 7: Wait for user confirmation

Wait for user response:
- `y` or `yes` → proceed with approval if no critical warnings
- `n` or `no` → cancel, show cancellation message
- `force` → proceed with approval even if warnings
- Any other input → ask again

**If critical warnings present** (e.g., file hash mismatch):
- Only allow `force` or `no`
- `y` is not sufficient

### Step 8: Perform approval

Use MCP tool `approve_entity(entity_type=..., entity_id=..., force=...)`:

```python
result = approve_entity(
    entity_type=entity_type,
    entity_id=full_entity_id,
    force=(user_input == 'force')
)
```

**If approval succeeds:**
```
✅ Entity approved successfully

Entity: {entity_type} '{entity_id}'
Status: draft → approved
Version: {version_hash[:8]}...
Approved at: {timestamp}

{if entity_type == 'act':}
Next steps:
  1. Plan chapters: /plan-chapter 1, /plan-chapter 2, ...
  2. Approve chapters when ready

{elif entity_type == 'chapter':}
Next steps:
  1. Plan scenes: /plan-scene {chapter_id}01, /plan-scene {chapter_id}02, ...
  2. Approve scenes when ready

{elif entity_type == 'scene':}
Next steps:
  1. Generate prose: "Generate scene {scene_id}"
  2. Review and edit generated content
{end}
```

**If approval fails:**
```
❌ ERROR: Approval failed

Entity: {entity_type} '{entity_id}'
Reason: {error_message}

{if error suggests parent not approved:}
Action required:
  1. Approve parent first
  2. Then retry approval

{elif error suggests state corruption:}
Action required:
  1. Run: /rebuild-state
  2. Then retry approval
{end}
```

---

## Error Handling

### Invalid entity type
```
❌ Error: Invalid entity type '{input}'

Entity type must be one of: act, chapter, scene

Usage: /approve-plan <entity_type> <entity_id>
Examples:
  /approve-plan act 1
  /approve-plan chapter 02
  /approve-plan scene 0204
```

### Invalid entity ID format
```
❌ Error: Invalid entity ID format '{input}'

Expected format:
  - act: positive integer (1, 2, 3, ...)
  - chapter: 1-2 digit number (1, 2, ..., 12, ...)
  - scene: 4-digit scene ID (0101, 0205, ...)

Usage: /approve-plan <entity_type> <entity_id>
```

### Entity not found
See Step 2.

### Already approved
See Step 3 (success case - idempotent).

### Invalid entity
See Step 3.

### Parent not approved
See Step 4.

### MCP unavailable
```
❌ ERROR: Planning state system unavailable

The MCP planning state server is not available.

Action required:
  1. Check MCP server status
  2. Restart MCP server if needed
  3. Verify planning_state_utils.py is working
```

---

## Notes

- **Idempotent**: Approving already-approved entity is success (no-op)
- **Validation**: Parent approval checked before allowing child approval
- **Warnings**: Non-critical issues shown but don't block approval
- **Force mode**: Allows approval even with warnings (use cautiously)
- **State sync**: Approval updates status in both SQLite and JSON
- **Hierarchy enforcement**: Validates entire parent chain

---

## Related Commands

- `/plan-act <act_number>` - Create act plan (draft status)
- `/plan-chapter <chapter_number>` - Create chapter plan (requires approved act)
- `/plan-scene <scene_id>` - Create scene blueprint (requires approved chapter)
- `get_entity_state()` - Check entity status (MCP tool)
- `approve_entity()` - Underlying MCP tool (called by this command)
- `/revalidate-scene <scene_id>` - Revalidate scene after parent changes

---

## Technical Details

**MCP Tool Used**: `approve_entity(entity_type, entity_id, force=False)`

**Status Transitions Allowed**:
- `draft` → `approved` ✓
- `requires-revalidation` → `approved` ✓ (after user verifies)
- `invalid` → `approved` ✗ (blocked - must regenerate)
- `approved` → `approved` ✓ (no-op, idempotent)

**Checks Performed**:
1. Entity exists
2. Parent approved (if not top-level)
3. Current status allows approval
4. Consistency warnings (non-blocking)

**Side Effects**:
- Updates `status` to 'approved'
- Updates `updated_at` timestamp
- Clears `invalidation_reason` and `invalidated_at` (if transitioning from requires-revalidation)
- Syncs to both SQLite and JSON

**Concurrency**: Safe - uses SQLite transactions
