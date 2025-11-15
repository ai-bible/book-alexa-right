# Command: /plan-chapter

Create and plan a new chapter for an act.

**Usage**: `/plan-chapter <chapter_number> [--act <act_number>]`

**Examples**:
- `/plan-chapter 1` - Plan Chapter 1 (assumes act-1)
- `/plan-chapter 2` - Plan Chapter 2 (assumes act-1)
- `/plan-chapter 5 --act 2` - Plan Chapter 5 in Act 2

---

## Workflow

You are assisting with **hierarchical planning** for a science fiction novel. Your task is to create a detailed plan for a chapter.

### Step 1: Extract parameters

Extract from command:
- `<chapter_number>` - Required (1, 2, 3, ...)
- `--act <act_number>` - Optional (default: 1)

Examples:
- `/plan-chapter 2` → chapter_number=2, act_number=1
- `/plan-chapter 5 --act 2` → chapter_number=5, act_number=2

### Step 2: Validate parameters

**Chapter number:**
- Must be positive integer (1, 2, 3, ...)
- If invalid → show error and stop

**Act number:**
- Must be positive integer
- Default to 1 if not specified

### Step 3: Determine file paths

Calculate:
- Act ID: `act-{act_number}` (e.g., `act-1`)
- Chapter ID: `chapter-{chapter_number:02d}` (e.g., `chapter-02` for chapter 2)
- Parent plan file: `acts/act-{act_number}/strategic-plan.md`
- Chapter plan file: `acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/plan.md`

### Step 4: CRITICAL - Check parent act approved

Use MCP tool `get_entity_state(entity_type='act', entity_id='act-{act_number}')`:

**If parent act NOT FOUND:**
```
❌ ERROR: Cannot plan chapter {chapter_number}

Parent act not found: act-{act_number}

Action required:
  1. Create act plan first: /plan-act {act_number}
  2. Approve the act plan
  3. Then retry: /plan-chapter {chapter_number}

Hierarchical planning: Act → Chapter → Scene
```
Stop execution.

**If parent act status ≠ 'approved':**
```
❌ ERROR: Cannot plan chapter {chapter_number}

Parent act plan not approved.
  - Act: act-{act_number}
  - Current status: {status}
  - File: {parent_file_path}

Action required:
  1. Review act plan: {parent_file_path}
  2. Approve: approve_entity(entity_type='act', entity_id='act-{act_number}')
  3. Then retry: /plan-chapter {chapter_number}

Hierarchical planning: Act must be approved before planning chapters.
```
Stop execution.

**If parent act status = 'approved':**
Proceed to Step 5.

### Step 5: Load parent context

Read the parent act plan file: `acts/act-{act_number}/strategic-plan.md`

Extract relevant information:
- Act objective
- Thematic focus
- Characters involved
- Chapter breakdown (if mentioned)
- Plot structure

This context will be injected into the planning agent prompt.

### Step 6: Check if chapter already exists

Check if `acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/plan.md` exists:

**If file exists:**
- Use MCP tool `get_entity_state` to check status
- Show current status:
  ```
  Chapter {chapter_number} already exists:
    - Status: {status}
    - File: {file_path}
    - Version: {version_hash[:8]}...
    - Parent: act-{act_number} (approved)

  Options:
    1. Edit existing plan
    2. View current plan
    3. Regenerate (creates backup, invalidates scenes)
    4. Abort
  ```
- Wait for user choice
- If edit → open file, proceed to Step 8
- If view → read and display, stop
- If regenerate → proceed to Step 7 (with backup warning)
- If abort → stop

**If file does not exist:**
Proceed to Step 7.

### Step 7: Create chapter plan

Launch `planning-coordinator` agent with context injection:

```
Create a detailed plan for Chapter {chapter_number} of Act {act_number}.

═══════════════════════════════════════════════════════════
PARENT CONTEXT (Act {act_number} Strategic Plan)
═══════════════════════════════════════════════════════════

File: acts/act-{act_number}/strategic-plan.md

{full_content_of_strategic_plan}

═══════════════════════════════════════════════════════════

CRITICAL: Your chapter plan MUST align with the act plan above.

TASK:
Create a comprehensive chapter plan covering:

1. **Chapter Objective**: What should happen in this chapter according to the act plan?
2. **Setting & Timeframe**: Where and when does this chapter take place?
3. **Characters**: Which characters appear? What are their roles?
4. **Events**: What specific events occur? (3-5 major events)
5. **Scene Breakdown**: How many scenes? Brief description of each.
   Format: Scene {chapter_number}{scene_number:02d} - Description
   Example: Scene 0201 - Character arrives at medical ward
6. **Conflicts**: What conflicts arise or develop?
7. **Character Development**: How do characters change/react?
8. **Connections**: How does this connect to previous/next chapters?

OUTPUT FORMAT:
Markdown file with clear structure.

CONSTRAINTS:
- Length: 300-700 words
- Scenes: 3-7 scenes per chapter (typical)
- Characters: Only use characters mentioned in act plan (or explicitly justify new ones)
- Events: Must align with act plot structure
- Locations: Match act-level world-building

ALIGNMENT REQUIREMENTS:
- If act plan mentions specific events for this chapter → include them
- If act plan specifies character arcs → reflect them
- If act plan sets themes → explore them
- If introducing NEW elements → flag explicitly and justify

Save to: acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/plan.md
```

**Agent**: `planning-coordinator`
- Uses Planning Workflow (5 phases)
- Interactive approval at key points
- Parent context injected automatically

### Step 8: Verify file created

After agent completes:
- Read `acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/plan.md`
- If missing → show error
- If exists → proceed to Step 9

### Step 9: Automatic state sync

The `state_sync_hook` will automatically:
- Calculate version hash
- Create MCP state for `chapter-{chapter_number:02d}`
- Set status to 'draft'
- Link to parent: `parent_id = 'act-{act_number}'`
- Record parent version: `parent_version_hash = {act_version_hash}`

**No manual action needed.**

### Step 10: Show results

Display:
```
✅ Chapter {chapter_number} plan created successfully

📁 File: acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/plan.md
📊 Status: draft (not yet approved)
🔢 Version: {version_hash[:8]}...
👆 Parent: act-{act_number} (approved, v{parent_version[:8]}...)

Next steps:
  1. Review the chapter plan
  2. Verify alignment with act plan
  3. Make any necessary edits
  4. Approve: approve_entity(entity_type='chapter', entity_id='chapter-{chapter_number:02d}')
  5. After approval, plan scenes: /plan-scene {chapter_number:02d}01

💡 Hierarchical planning: You must approve this chapter before planning scenes.
```

### Step 11: Suggest approval (optional)

Ask: "Would you like to approve this chapter plan now? (y/n)"

If yes:
- Use MCP tool `approve_entity(entity_type='chapter', entity_id='chapter-{chapter_number:02d}')`
- Show approval confirmation
- Suggest next action: "Ready to plan scenes? Use /plan-scene {chapter_number:02d}01"

If no:
- Stop

---

## Special Case: Regeneration

If user chooses **Option 3: Regenerate** in Step 6:

### Warning before regeneration:
```
⚠️  WARNING: Regenerating Chapter {chapter_number}

This will:
  1. Create backup: backups/plan-{timestamp}.md
  2. Generate new chapter plan
  3. Mark ALL existing scenes as 'requires-revalidation'

Current chapter has {num_scenes} scenes:
  {list_of_scene_ids}

These scenes will need manual review/revalidation after regeneration.

Proceed with regeneration? (y/n)
```

If user confirms:
1. Create backup (manual or via hook)
2. Proceed with Step 7 (create new plan)
3. After Step 9 (state sync), the `invalidation_cascade_hook` will:
   - Detect version_hash changed
   - Call `cascade_invalidate(entity_type='chapter', entity_id='chapter-{chapter_number:02d}', reason='parent_chapter_regenerated')`
   - Mark all scenes as 'requires-revalidation'

4. Show regeneration summary:
```
✅ Chapter {chapter_number} regenerated

📁 New plan: acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/plan.md
📦 Backup: acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/backups/plan-{timestamp}.md

⚠️  Invalidated {num_scenes} scenes:
  - scene-{chapter_number:02d}01: approved → requires-revalidation
  - scene-{chapter_number:02d}02: approved → requires-revalidation
  ...

Next steps:
  1. Approve new chapter plan
  2. Review each scene blueprint
  3. Revalidate or regenerate scenes as needed
```

---

## Error Handling

### Invalid chapter number
```
❌ Error: Invalid chapter number '{input}'

Chapter number must be a positive integer (1, 2, 3, ...)

Usage: /plan-chapter <chapter_number> [--act <act_number>]
Example: /plan-chapter 2
```

### Parent act not approved
See Step 4 error messages.

### File creation failed
```
❌ Error: Failed to create chapter plan file

The planning agent did not create the expected file.
Please check agent output and try again.
```

### Hierarchy validation blocked by hook
If user somehow bypasses command checks, the `hierarchy_validation_hook` will block:
```
🚫 BLOCKED: Hierarchical planning constraint violation

File: acts/act-{act_number}/chapters/chapter-{chapter_number:02d}/plan.md
Entity: chapter 'chapter-{chapter_number:02d}'
Parent: act 'act-{act_number}'

Reason: Parent act plan not approved (current status: draft)

Action Required:
  1. Approve parent plan first
  2. Use: approve_entity(entity_type='act', entity_id='act-{act_number}')
  3. Then retry this operation
```

---

## Notes

- Parent context injection ensures chapter aligns with act
- Hooks automatically handle state sync and cascade invalidation
- Hierarchical validation enforced at multiple levels (command + hook)
- Chapter numbering uses 2-digit padding (01, 02, ... 99)

---

## Related Commands

- `/plan-act <act_number>` - Plan parent act first
- `/plan-scene <scene_id>` - Plan scenes after chapter approved
- `approve_entity()` - Approve chapter plan
- `get_entity_state()` - Check chapter status
- `get_children_status()` - See scene statuses
