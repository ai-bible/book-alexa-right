# Command: /plan-act

Create and plan a new act for the novel.

**Usage**: `/plan-act <act_number>`

**Examples**:
- `/plan-act 1` - Plan Act 1
- `/plan-act 2` - Plan Act 2

---

## Workflow

You are assisting with **hierarchical planning** for a science fiction novel. Your task is to create a strategic plan for an act.

### Step 1: Extract parameters

Extract the act number from the command: `<act_number>`

Example: If command is `/plan-act 1`, then act_number = 1

### Step 2: Validate act number

- Must be a positive integer (1, 2, 3, ...)
- If invalid, show error and stop

### Step 3: Determine file paths

Calculate the file paths:
- Act ID: `act-{act_number}` (e.g., `act-1`)
- Strategic plan file: `acts/act-{act_number}/strategic-plan.md`
- Act directory: `acts/act-{act_number}/`

### Step 4: Check if act already exists

Check if `acts/act-{act_number}/strategic-plan.md` exists:

**If file exists:**
- Use MCP tool `get_entity_state` to check current status
- Show current status to user:
  ```
  Act {act_number} already exists:
    - Status: {status}
    - File: {file_path}
    - Version: {version_hash[:8]}...

  Options:
    1. Edit existing plan (opens file for editing)
    2. View current plan (read file)
    3. Abort
  ```
- Wait for user choice
- If edit → open file for editing, then proceed to Step 6
- If view → read and display file, then stop
- If abort → stop

**If file does not exist:**
- Proceed to Step 5

### Step 5: Create strategic plan

Launch the `planning-coordinator` agent with the following prompt:

```
Create a strategic plan for Act {act_number} of the science fiction novel.

CONTEXT:
- Novel setting: Vertical megacity with time manipulation technologies
- Genre: Hard sci-fi, psychological thriller
- Target: Adult readers interested in social commentary and philosophical themes

TASK:
Create a comprehensive strategic plan for Act {act_number} covering:

1. **Act Objective**: What is the main goal/arc of this act?
2. **Thematic Focus**: What themes are explored in this act?
3. **Character Arcs**: Which characters are central? What do they experience?
4. **World-building Elements**: What aspects of the world are revealed?
5. **Plot Structure**:
   - Inciting incident
   - Rising action
   - Climax
   - Resolution
6. **Chapter Breakdown**: How many chapters? Brief description of each.
7. **Connections**: How does this act connect to previous/next acts?

OUTPUT FORMAT:
Write a markdown file with the structure above.

CONSTRAINTS:
- Length: 500-1000 words
- Tone: Analytical, planning-focused
- Style: Clear, structured, actionable

Save the plan to: acts/act-{act_number}/strategic-plan.md
```

**Agent**: `planning-coordinator` (from Planning Workflow)
- Uses scenario generation and arc planning
- Interactive user approval at key decision points
- Outputs structured markdown plan

### Step 6: Verify file created

After agent completes, verify file exists:
- Read `acts/act-{act_number}/strategic-plan.md`
- If file missing → show error
- If file exists → proceed to Step 7

### Step 7: Automatic state sync

The `state_sync_hook` (PostToolUse) will automatically:
- Calculate version hash
- Create MCP state entry for `act-{act_number}`
- Set status to 'draft'

**No manual action needed** - hook handles this automatically.

### Step 8: Show results to user

Display confirmation:

```
✅ Act {act_number} strategic plan created successfully

📁 File: acts/act-{act_number}/strategic-plan.md
📊 Status: draft (not yet approved)
🔢 Version: {version_hash[:8]}...

Next steps:
  1. Review the strategic plan
  2. Make any necessary edits
  3. Approve the plan: Use MCP tool approve_entity(entity_type='act', entity_id='act-{act_number}')
  4. After approval, you can plan chapters: /plan-chapter <chapter_number>

💡 Hierarchical planning: You must approve this act plan before planning chapters.
```

### Step 9: Suggest approval (optional)

Ask user: "Would you like to approve this act plan now? (y/n)"

If yes:
- Use MCP tool `approve_entity(entity_type='act', entity_id='act-{act_number}')`
- Show approval confirmation

If no:
- Stop

---

## Error Handling

### Act number invalid
```
❌ Error: Invalid act number '{input}'

Act number must be a positive integer (1, 2, 3, ...)

Usage: /plan-act <act_number>
Example: /plan-act 1
```

### File creation failed
```
❌ Error: Failed to create strategic plan file

The planning agent did not create the expected file:
  acts/act-{act_number}/strategic-plan.md

Please check agent output for errors and try again.
```

### MCP unavailable
```
⚠️ Warning: Planning state tracking unavailable

The strategic plan was created, but state tracking is not available.
You can still work with the file manually, but hierarchical validation won't work.

Created file: acts/act-{act_number}/strategic-plan.md
```

---

## Notes

- This command uses the Planning Workflow (FEAT-0001)
- State tracking via MCP (FEAT-0003)
- Hooks automatically sync file changes to state
- Parent validation enforced by `hierarchy_validation_hook`
- Acts have no parent, so no validation needed

---

## Related Commands

- `/plan-chapter <chapter_number>` - Plan a chapter (after act approved)
- `/plan-scene <scene_id>` - Plan a scene (after chapter approved)
- `approve_entity()` - Approve a plan (MCP tool)
- `get_entity_state()` - Check plan status (MCP tool)
