# Command: /revalidate-all

Batch review and revalidate all scenes marked as 'requires-revalidation'.

**Usage**: `/revalidate-all [--act <act_number>] [--chapter <chapter_number>]`

**Examples**:
- `/revalidate-all` - Revalidate all scenes across all acts
- `/revalidate-all --act 1` - Revalidate all scenes in Act 1
- `/revalidate-all --chapter 02` - Revalidate all scenes in Chapter 02 (assumes act-1)
- `/revalidate-all --act 2 --chapter 05` - Revalidate all scenes in Act 2, Chapter 05

---

## Purpose

After parent plans (chapters or acts) are modified, many scenes may be marked as `requires-revalidation`. This command helps you efficiently process multiple scenes in batch mode.

Benefits:
- **Overview**: See all scenes needing revalidation at once
- **Batch operations**: Approve multiple aligned scenes quickly
- **Prioritization**: Focus on scenes that need attention
- **Progress tracking**: Track revalidation progress

---

## Workflow

### Step 1: Extract and validate parameters

Extract optional filters:
- `--act <act_number>` - Optional (filter by act)
- `--chapter <chapter_number>` - Optional (filter by chapter)

**Validation**:
- Act number: positive integer (if specified)
- Chapter number: positive integer (if specified)
- If chapter specified without act → default act to 1

**Normalization**:
- Act filter: `act-{act_number}` (if specified)
- Chapter filter: `chapter-{chapter_number:02d}` (if specified)

### Step 2: Query all scenes needing revalidation

Use MCP tools to find all scenes with status = 'requires-revalidation':

**If no filters:**
- Query all planning entities where `entity_type='scene' AND status='requires-revalidation'`

**If act filter:**
- Query scenes where `parent_id` starts with filtered act → get chapters → get scenes

**If chapter filter:**
- Query scenes where `parent_id = 'chapter-{chapter_number}'`

**Collect results** → list of scenes needing revalidation.

### Step 3: Check if any scenes found

**If NO scenes found:**
```
✅ No scenes require revalidation

{if filters:}
Filters applied:
  - Act: {act_filter if specified}
  - Chapter: {chapter_filter if specified}
{end}

All scenes are either:
  - draft (being worked on)
  - approved (ready for generation)
  - invalid (need regeneration)

No revalidation needed! 🎉
```
Stop execution (success).

**If scenes found:**
Show count and proceed to Step 4.

```
Found {num_scenes} scene(s) requiring revalidation

{if filters:}
Filters applied:
  - Act: {act_filter if specified}
  - Chapter: {chapter_filter if specified}
{end}

Loading details...
```

### Step 4: Load details for all scenes

For each scene:
1. Get entity state (status, version, parent info, invalidation details)
2. Get parent chapter state (version, status)
3. Calculate time since invalidation
4. Determine priority (based on parent changes, age, etc.)

**Priority levels**:
- **High**: Parent changed multiple times since invalidation
- **Medium**: Parent changed once
- **Low**: Parent unchanged since invalidation

### Step 5: Display revalidation summary

Show comprehensive table:

```
═══════════════════════════════════════════════════════════
BATCH REVALIDATION SUMMARY
═══════════════════════════════════════════════════════════

Total scenes requiring revalidation: {num_scenes}
{if filters:}Filtered to: {filter_description}{end}

┌────────┬──────────┬──────────────┬─────────────┬──────────┐
│ Scene  │ Parent   │ Invalidated  │ Reason      │ Priority │
├────────┼──────────┼──────────────┼─────────────┼──────────┤
│ 0101   │ ch-01    │ 2h ago       │ parent_ch…  │ HIGH     │
│ 0102   │ ch-01    │ 2h ago       │ parent_ch…  │ HIGH     │
│ 0201   │ ch-02    │ 1d ago       │ parent_ch…  │ MEDIUM   │
│ 0204   │ ch-02    │ 1d ago       │ parent_ch…  │ MEDIUM   │
│ 0301   │ ch-03    │ 3d ago       │ parent_ch…  │ LOW      │
└────────┴──────────┴──────────────┴─────────────┴──────────┘

═══════════════════════════════════════════════════════════
PARENT CHAPTERS AFFECTED
═══════════════════════════════════════════════════════════

chapter-01: 2 scenes need revalidation
  - Last modified: 2h ago
  - Status: approved
  - Scenes: 0101, 0102

chapter-02: 2 scenes need revalidation
  - Last modified: 1d ago
  - Status: approved
  - Scenes: 0201, 0204

chapter-03: 1 scene needs revalidation
  - Last modified: 3d ago
  - Status: requires-revalidation ⚠️
  - Scenes: 0301
  - ⚠️  Warning: Parent chapter also needs revalidation!

═══════════════════════════════════════════════════════════
BATCH OPERATIONS
═══════════════════════════════════════════════════════════

Choose operation mode:

1. **Interactive Review** - Review each scene individually
   → Shows detailed report for each scene
   → Allows keep/edit/regenerate per scene
   → Similar to /revalidate-scene but in batch

2. **Bulk Approve (Low Priority)** - Approve all LOW priority scenes at once
   → Only approves scenes where parent barely changed
   → Skips HIGH/MEDIUM priority for manual review
   → Safe for aligned scenes

3. **Bulk Approve (All)** - Approve ALL scenes without review
   → ⚠️  Use with caution!
   → Only if you're confident all scenes are still valid
   → No individual review

4. **Export Report** - Save summary to file for review
   → Creates detailed report in workspace
   → No status changes
   → Review offline

5. **Group by Chapter** - Process scenes chapter by chapter
   → Shows scenes grouped by parent chapter
   → Allows batch operations per chapter
   → More organized review

6. **Abort** - Exit without changes
   → No status changes
   → Can run command again later

Enter choice (1-6):
```

### Step 6: Process based on user choice

**Choice 1: Interactive Review**
→ Go to Step 7a

**Choice 2: Bulk Approve (Low Priority)**
→ Go to Step 7b

**Choice 3: Bulk Approve (All)**
→ Go to Step 7c

**Choice 4: Export Report**
→ Go to Step 7d

**Choice 5: Group by Chapter**
→ Go to Step 7e

**Choice 6: Abort**
→ Go to Step 7f

### Step 7a: Interactive Review

Process each scene one by one:

```
═══════════════════════════════════════════════════════════
INTERACTIVE REVIEW: Scene {current}/{total}
═══════════════════════════════════════════════════════════

Scene: scene-{scene_id}
Parent: chapter-{chapter_number}
Priority: {priority}
Invalidated: {time_ago}
Reason: {invalidation_reason}

{brief alignment check - similar to /revalidate-scene but more concise}

Options:
  k = Keep & approve this scene
  e = Edit this scene
  r = Regenerate this scene
  s = Skip to next scene (no changes)
  v = View full details (opens detailed report)
  q = Quit interactive review

Enter choice:
```

Process each scene based on input.

**After all scenes processed:**
```
✅ Interactive review complete

Processed: {num_processed} / {total_scenes}
  - Approved: {num_approved}
  - Edited: {num_edited}
  - Regenerated: {num_regenerated}
  - Skipped: {num_skipped}

Remaining scenes with 'requires-revalidation': {num_remaining}

{if num_remaining > 0:}
Run /revalidate-all again to continue review.
{else:}
All scenes have been revalidated! 🎉
{end}
```

### Step 7b: Bulk Approve (Low Priority)

Filter LOW priority scenes and show confirmation:

```
⚠️  BULK APPROVE (LOW PRIORITY ONLY)

This will approve {num_low_priority} scene(s):
{list_of_low_priority_scenes}

These scenes have LOW priority because:
  - Parent changed minimally since invalidation
  - Scenes likely still aligned

HIGH/MEDIUM priority scenes will be skipped for manual review:
{list_of_high_medium_scenes}

Proceed with bulk approval of LOW priority scenes? (y/n)
```

**If user confirms (y):**
- Loop through LOW priority scenes
- Approve each using `approve_entity()`
- Track successes/failures

```
✅ Bulk approval complete

Approved: {num_approved} / {num_low_priority}
{if failures:}
Failed: {num_failed}
  {list_failed_scenes}
{end}

Remaining scenes needing manual review: {num_remaining}
  - HIGH priority: {num_high}
  - MEDIUM priority: {num_medium}

Run /revalidate-all again to review remaining scenes.
```

**If user cancels (n):**
```
❌ Bulk approval cancelled

No scenes were approved.
```

### Step 7c: Bulk Approve (All)

Show strong warning:

```
⚠️  WARNING: BULK APPROVE ALL SCENES

This will approve ALL {num_scenes} scene(s) without individual review:
{list_all_scenes_with_priorities}

Priority breakdown:
  - HIGH: {num_high} scenes (parent changed significantly)
  - MEDIUM: {num_medium} scenes (parent changed moderately)
  - LOW: {num_low} scenes (parent changed minimally)

⚠️  USE WITH CAUTION!
Only proceed if you're confident ALL scenes are still aligned with their updated parent plans.

Type 'APPROVE ALL' to confirm (case-sensitive):
```

**If user types exactly 'APPROVE ALL':**
- Loop through all scenes
- Approve each using `approve_entity(force=True)` (force to bypass individual checks)
- Track successes/failures

```
✅ Bulk approval complete

Approved: {num_approved} / {num_scenes}
{if failures:}
Failed: {num_failed}
  {list_failed_scenes}

  Failures may indicate:
    - Parent not approved
    - State corruption
    - MCP errors

  Run /revalidate-scene {failed_scene_id} to investigate.
{end}

{if all_succeeded:}
All scenes revalidated successfully! 🎉
{end}
```

**If user types anything else:**
```
❌ Bulk approval cancelled

No scenes were approved. To proceed, type exactly 'APPROVE ALL'.
```

### Step 7d: Export Report

Generate detailed report and save to file:

```
📄 Generating revalidation report...

Report will include:
  - Summary of all scenes requiring revalidation
  - Parent chapter details
  - Invalidation reasons and timestamps
  - Priority assessments
  - Recommended actions

Saving to: workspace/revalidation-reports/report-{timestamp}.md
```

Generate markdown report with all details.

```
✅ Report exported successfully

File: workspace/revalidation-reports/report-{timestamp}.md
Size: {file_size}

Report includes:
  - {num_scenes} scenes requiring revalidation
  - Detailed breakdown per scene
  - Parent chapter status
  - Recommended actions

You can:
  1. Review the report offline
  2. Come back and run /revalidate-all to take action
  3. Use /revalidate-scene {scene_id} for individual scenes
```

### Step 7e: Group by Chapter

Show scenes organized by chapter:

```
═══════════════════════════════════════════════════════════
GROUPED BY CHAPTER
═══════════════════════════════════════════════════════════

chapter-01 (2 scenes need revalidation):
  - scene-0101 (HIGH priority, invalidated 2h ago)
  - scene-0102 (HIGH priority, invalidated 2h ago)

  Chapter status: approved
  Last modified: 2h ago

  Options:
    a = Approve all scenes in this chapter
    r = Review scenes one by one
    s = Skip this chapter

chapter-02 (2 scenes need revalidation):
  - scene-0201 (MEDIUM priority, invalidated 1d ago)
  - scene-0204 (MEDIUM priority, invalidated 1d ago)

  Chapter status: approved
  Last modified: 1d ago

  Options:
    a = Approve all scenes in this chapter
    r = Review scenes one by one
    s = Skip this chapter

...

Process chapters one by one? (y/n)
```

**If user confirms:**
Process each chapter interactively.

**For each chapter:**
- Show chapter details
- Show all scenes in that chapter
- Allow batch approve for chapter or review individually

After all chapters processed, show summary.

### Step 7f: Abort

```
ℹ️  Batch revalidation aborted

No changes made to any scenes.

Found {num_scenes} scene(s) requiring revalidation:
{list_scenes}

You can:
  1. Run /revalidate-all again anytime
  2. Use /revalidate-scene {scene_id} for individual review
  3. Use /approve-plan scene {scene_id} if you're confident scene is valid
```

---

## Error Handling

### Invalid act number
```
❌ Error: Invalid act number '{input}'

Act number must be a positive integer (1, 2, 3, ...)

Usage: /revalidate-all [--act <act_number>] [--chapter <chapter_number>]
Example: /revalidate-all --act 1
```

### Invalid chapter number
```
❌ Error: Invalid chapter number '{input}'

Chapter number must be a positive integer (1, 2, 3, ...)

Usage: /revalidate-all [--act <act_number>] [--chapter <chapter_number>]
Example: /revalidate-all --chapter 02
```

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

- **Efficient**: Process multiple scenes in batch mode
- **Flexible**: Multiple processing modes (interactive, bulk, grouped)
- **Safe**: Confirmations for destructive operations
- **Filtering**: Scope operations to specific acts or chapters
- **Priority-based**: Focus on scenes that need most attention
- **Reporting**: Export reports for offline review

---

## Related Commands

- `/revalidate-scene <scene_id>` - Detailed revalidation for single scene
- `/approve-plan scene <scene_id>` - Approve scene directly
- `get_entity_state()` - Query scene status (MCP tool)
- `get_children_status()` - Get status counts for children (MCP tool)

---

## When to Use This Command

Use `/revalidate-all` when:
- Multiple scenes need revalidation (after chapter/act modifications)
- You want an overview of all invalidated scenes
- You need to process many scenes efficiently
- You want to prioritize review based on parent changes

Use `/revalidate-scene` instead when:
- Only one scene needs review
- You want detailed alignment analysis
- You need guided decision-making for a specific scene

---

## Technical Details

**Query**: Finds all scenes with `status = 'requires-revalidation'`

**Filtering**: Optional filters by act and/or chapter

**Priority Calculation**:
- HIGH: `parent_version_changes >= 2` or `invalidated > 7 days ago`
- MEDIUM: `parent_version_changes == 1` and `invalidated 1-7 days ago`
- LOW: `parent_version_changes == 0` and `invalidated < 1 day ago`

**Bulk Operations**:
- Bulk Approve (Low): Only LOW priority, safe defaults
- Bulk Approve (All): Uses `force=True`, requires strong confirmation

**Safety**:
- Strong confirmations for bulk approvals
- Priority-based filtering
- Detailed reports before actions
- Non-destructive options (export, view)

**Performance**:
- Batch queries for efficiency
- Parallel approval operations (where safe)
- Progress tracking for long operations
