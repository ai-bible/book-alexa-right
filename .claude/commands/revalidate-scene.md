# Command: /revalidate-scene

Review and revalidate a scene blueprint that was marked as 'requires-revalidation' after parent changes.

**Usage**: `/revalidate-scene <scene_id>`

**Examples**:
- `/revalidate-scene 0101` - Revalidate Scene 0101
- `/revalidate-scene 0204` - Revalidate Scene 0204

---

## Purpose

When a parent plan (chapter or act) is regenerated or modified, all descendant scenes are automatically marked as `requires-revalidation`. This ensures that scene blueprints remain aligned with updated parent plans.

This command helps you:
1. Understand why the scene needs revalidation
2. Compare the scene with the current parent plan
3. Decide whether to keep, edit, or regenerate the scene blueprint

---

## Workflow

### Step 1: Extract and validate scene ID

Extract `<scene_id>` from command.

**Validation**:
- Must be 4-digit format: XXYY (e.g., 0101, 0204)
- XX = chapter number (01-99)
- YY = scene number (01-99)
- If invalid → show error and stop

**Normalize** to full ID: `scene-{scene_id}`

### Step 2: Check scene exists and status

Use MCP tool `get_entity_state(entity_type='scene', entity_id='scene-{scene_id}')`.

**If scene NOT FOUND:**
```
❌ ERROR: Scene not found

Scene: scene-{scene_id}

This scene doesn't exist in the planning state.

Action required:
  1. Check if blueprint file exists
  2. If file exists but not in state, run: /rebuild-state
  3. If file doesn't exist, create it: /plan-scene {scene_id}
```
Stop execution.

**If scene status ≠ 'requires-revalidation':**
```
ℹ️  Scene doesn't require revalidation

Scene: scene-{scene_id}
Status: {status}
File: {file_path}

This scene is not marked for revalidation.

Current status meanings:
  - draft: Scene is being worked on
  - approved: Scene is validated and ready for generation
  - invalid: Scene should be regenerated (cannot revalidate)
  - requires-revalidation: Scene needs review after parent changes ← Expected

{if status == 'approved':}
✅ Scene is already approved and ready for generation.

{elif status == 'draft':}
💡 To approve this scene: /approve-plan scene {scene_id}

{elif status == 'invalid':}
❌ Invalid scenes cannot be revalidated. They must be regenerated.
   Use: /plan-scene {scene_id} (choose "regenerate")
{end}
```
Stop execution.

**If scene status = 'requires-revalidation':**
Proceed to Step 3.

### Step 3: Load invalidation details

From scene state, extract:
- `invalidation_reason` - Why was it invalidated?
- `invalidated_at` - When was it invalidated?
- `parent_version_hash` - What parent version was scene based on?
- `version_hash` - Scene's current version

### Step 4: Load parent state

Extract chapter number from scene_id (first 2 digits).

Use `get_entity_state(entity_type='chapter', entity_id='chapter-{chapter_number}')` to get parent.

**If parent NOT FOUND:**
```
❌ ERROR: Parent chapter not found

Scene: scene-{scene_id}
Expected parent: chapter-{chapter_number}

The parent chapter doesn't exist in planning state.

Action required:
  1. Run: /rebuild-state
  2. If parent still missing, create it: /plan-chapter {chapter_number}
```
Stop execution.

**If parent found:**
- Compare `scene.parent_version_hash` with `chapter.version_hash`
- This shows what changed in parent

Proceed to Step 5.

### Step 5: Display revalidation report

Show comprehensive report:

```
🔄 SCENE REVALIDATION REPORT

═══════════════════════════════════════════════════════════
SCENE DETAILS
═══════════════════════════════════════════════════════════

Scene: scene-{scene_id}
File: {scene_file_path}
Status: requires-revalidation ⚠️
Scene version: {scene.version_hash[:8]}...

Invalidated: {invalidated_at} ({time_ago})
Reason: {invalidation_reason}

═══════════════════════════════════════════════════════════
PARENT CHAPTER STATUS
═══════════════════════════════════════════════════════════

Chapter: chapter-{chapter_number}
File: {chapter_file_path}
Status: {chapter.status}

Version when scene created: {scene.parent_version_hash[:8]}...
Current version: {chapter.version_hash[:8]}...

{if versions_match:}
✅ Parent version matches - no parent changes since invalidation
{else:}
⚠️  Parent has changed since scene was created

Parent has been modified {num_parent_changes} time(s) since this scene was planned.
{end}

═══════════════════════════════════════════════════════════
ALIGNMENT CHECK
═══════════════════════════════════════════════════════════

Reading scene blueprint: {scene_file_path}
Reading chapter plan: {chapter_file_path}

{read both files and extract key sections}

**Scene Objective** (from blueprint):
{scene_objective_text}

**Chapter's Expectation for This Scene** (from chapter plan):
{search chapter plan for mention of this scene number}

{compare and show alignment}

{if well_aligned:}
✅ Scene objective aligns well with chapter plan

{elif misaligned:}
⚠️  Potential misalignment detected:
  - Scene focuses on: {scene_focus}
  - Chapter expects: {chapter_expectation}
  - **Discrepancy**: {describe_difference}

{elif chapter_plan_unclear:}
ℹ️  Chapter plan doesn't explicitly mention this scene's requirements.
   You'll need to manually verify alignment.
{end}

═══════════════════════════════════════════════════════════
REVALIDATION OPTIONS
═══════════════════════════════════════════════════════════

What would you like to do with this scene?

1. **Keep & Approve** - Scene is still valid, approve it as-is
   → Changes status to 'approved'
   → Scene ready for prose generation

2. **Edit Blueprint** - Scene needs minor adjustments
   → Opens blueprint file for editing
   → After editing, you can approve manually

3. **Regenerate** - Scene needs major changes to align with new chapter plan
   → Creates backup of current blueprint
   → Generates new blueprint with updated parent context
   → New blueprint starts in 'draft' status

4. **View Files** - Compare scene and chapter files side-by-side
   → Opens both files for manual comparison
   → No status change

5. **Abort** - Do nothing now, decide later
   → No changes made
   → Scene remains in 'requires-revalidation' status

Enter choice (1-5):
```

### Step 6: Wait for user choice

Process user input:

**Choice 1: Keep & Approve**
→ Go to Step 7a

**Choice 2: Edit Blueprint**
→ Go to Step 7b

**Choice 3: Regenerate**
→ Go to Step 7c

**Choice 4: View Files**
→ Go to Step 7d, then return to Step 5

**Choice 5: Abort**
→ Go to Step 7e

**Invalid input**
→ Ask again

### Step 7a: Keep & Approve

Use MCP tool `approve_entity(entity_type='scene', entity_id='scene-{scene_id}', force=False)`.

**On success:**
```
✅ Scene revalidated and approved

Scene: scene-{scene_id}
Status: requires-revalidation → approved
Version: {version_hash[:8]}...
Approved at: {timestamp}

The scene blueprint was reviewed and is still valid.

Next steps:
  1. Generate prose: "Generate scene {scene_id}"
  2. Review and edit generated content
```

**On failure:**
```
❌ ERROR: Approval failed

Reason: {error_message}

Action required:
  1. {suggested_fix}
  2. Retry revalidation
```

### Step 7b: Edit Blueprint

Open the blueprint file for editing:

```
📝 Opening blueprint for editing...

File: {scene_file_path}

After editing:
  1. Save the file
  2. The state_sync_hook will update the version hash automatically
  3. Approve when ready: /approve-plan scene {scene_id}
```

Use `Edit` tool or notify user to edit manually.

After editing, show:
```
✅ Blueprint opened for editing

When done editing:
  1. Review your changes
  2. Approve: /approve-plan scene {scene_id}
  3. Or run revalidation again: /revalidate-scene {scene_id}
```

### Step 7c: Regenerate

Warn about regeneration:

```
⚠️  WARNING: Regenerating scene {scene_id}

This will:
  1. Create backup: {backup_path}
  2. Generate new blueprint with current chapter context
  3. New blueprint will be in 'draft' status

Current blueprint will be preserved in backups.

Proceed with regeneration? (y/n)
```

Wait for confirmation.

**If user confirms (y):**
- Create backup (manual or suggest backup creation)
- Launch planning-coordinator with updated chapter context (similar to /plan-scene workflow)
- Show regeneration summary

```
✅ Scene {scene_id} blueprint regenerated

📁 New blueprint: {scene_file_path}
📦 Backup: {backup_path}
📊 Status: draft

Next steps:
  1. Review new blueprint
  2. Make any edits if needed
  3. Approve: /approve-plan scene {scene_id}
  4. Generate prose: "Generate scene {scene_id}"
```

**If user cancels (n):**
```
❌ Regeneration cancelled

No changes made to scene {scene_id}.
```

### Step 7d: View Files

Show paths for manual comparison:

```
📄 FILE COMPARISON

**Scene Blueprint**:
  File: {scene_file_path}
  Size: {file_size}
  Version: {scene.version_hash[:8]}...

**Chapter Plan**:
  File: {chapter_file_path}
  Size: {file_size}
  Version: {chapter.version_hash[:8]}...

{optionally read and display both files with clear separation}

═══════════════════════════════════════════════════════════
SCENE BLUEPRINT
═══════════════════════════════════════════════════════════

{read and display scene blueprint file}

═══════════════════════════════════════════════════════════
CHAPTER PLAN
═══════════════════════════════════════════════════════════

{read and display chapter plan file}

═══════════════════════════════════════════════════════════

Press Enter to return to revalidation options...
```

After viewing, return to Step 5 (show options again).

### Step 7e: Abort

```
ℹ️  Revalidation aborted

Scene: scene-{scene_id}
Status: requires-revalidation (unchanged)

No changes made. You can revalidate later using:
  /revalidate-scene {scene_id}

Or approve directly if you're confident it's still valid:
  /approve-plan scene {scene_id}
```

---

## Error Handling

### Invalid scene ID
```
❌ Error: Invalid scene ID '{input}'

Scene ID must be 4-digit format: XXYY
  - XX = chapter number (01-99)
  - YY = scene number (01-99)

Examples: 0101, 0204, 1003

Usage: /revalidate-scene <scene_id>
```

### Scene not found
See Step 2.

### Scene doesn't need revalidation
See Step 2 (info message).

### Parent not found
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

- **Non-destructive**: Original blueprint preserved when regenerating (backup created)
- **Context-aware**: Shows parent changes and alignment issues
- **Flexible**: Multiple options (keep, edit, regenerate)
- **Interactive**: Guides user through decision-making
- **Safe**: Warnings before destructive operations

---

## Related Commands

- `/approve-plan scene <scene_id>` - Approve scene without revalidation report
- `/revalidate-all` - Batch revalidate all scenes needing review
- `/plan-scene <scene_id>` - Create new scene or regenerate existing
- `get_entity_state()` - Check scene status (MCP tool)
- `cascade_invalidate()` - Mark scenes for revalidation (MCP tool)

---

## When to Use This Command

Use `/revalidate-scene` when:
- Scene status is 'requires-revalidation'
- Parent chapter has been modified
- You want guided review of scene-parent alignment
- You need help deciding: keep, edit, or regenerate

Don't use this command when:
- Scene status is 'draft' or 'approved' (use /approve-plan instead)
- Scene status is 'invalid' (regenerate with /plan-scene)
- You're confident scene is still valid (use /approve-plan directly)

---

## Technical Details

**Status Check**: Only processes scenes with status = 'requires-revalidation'

**Alignment Analysis**:
- Compares scene objective with chapter expectations
- Identifies version mismatches
- Shows invalidation reason and timestamp

**Operations Available**:
- Keep & Approve: Status → 'approved'
- Edit: Opens file, status unchanged until manual approval
- Regenerate: Creates backup, generates new draft
- View: Read-only comparison
- Abort: No changes

**Safety**:
- Backups created before regeneration
- Warnings shown before destructive operations
- Idempotent reads (no side effects from viewing)
