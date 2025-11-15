# Command: /plan-scene

Create and plan a new scene for a chapter.

**Usage**: `/plan-scene <scene_id> [--act <act_number>]`

**Examples**:
- `/plan-scene 0101` - Plan Scene 0101 (Chapter 01, Scene 01, assumes act-1)
- `/plan-scene 0205` - Plan Scene 0205 (Chapter 02, Scene 05, assumes act-1)
- `/plan-scene 0304 --act 2` - Plan Scene 0304 in Act 2

---

## Workflow

You are assisting with **hierarchical planning** for a science fiction novel. Your task is to create a detailed scene blueprint.

### Step 1: Extract parameters

Extract from command:
- `<scene_id>` - Required (4-digit format: XXYY where XX=chapter, YY=scene)
- `--act <act_number>` - Optional (default: 1)

Examples:
- `/plan-scene 0201` → scene_id=0201, chapter=02, scene=01, act=1
- `/plan-scene 0304 --act 2` → scene_id=0304, chapter=03, scene=04, act=2

### Step 2: Validate parameters

**Scene ID:**
- Must be 4-digit format: XXYY (e.g., 0101, 0205, 1003)
- XX = chapter number (01-99)
- YY = scene number within chapter (01-99)
- If invalid → show error and stop

**Act number:**
- Must be positive integer
- Default to 1 if not specified

**Chapter extraction:**
- Extract chapter number from first 2 digits of scene_id
- Example: 0205 → chapter_number=02

### Step 3: Determine file paths

Calculate:
- Act ID: `act-{act_number}` (e.g., `act-1`)
- Chapter ID: `chapter-{chapter_number}` (e.g., `chapter-02`)
- Scene ID: `scene-{scene_id}` (e.g., `scene-0205`)
- Parent chapter plan: `acts/act-{act_number}/chapters/chapter-{chapter_number}/plan.md`
- Scene blueprint: `acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/scene-{scene_id}-blueprint.md`

### Step 4: CRITICAL - Check parent chapter approved

Use MCP tool `get_entity_state(entity_type='chapter', entity_id='chapter-{chapter_number}')`:

**If parent chapter NOT FOUND:**
```
❌ ERROR: Cannot plan scene {scene_id}

Parent chapter not found: chapter-{chapter_number}

Action required:
  1. Create chapter plan first: /plan-chapter {chapter_number}
  2. Approve the chapter plan
  3. Then retry: /plan-scene {scene_id}

Hierarchical planning: Act → Chapter → Scene
```
Stop execution.

**If parent chapter status ≠ 'approved':**
```
❌ ERROR: Cannot plan scene {scene_id}

Parent chapter plan not approved.
  - Chapter: chapter-{chapter_number}
  - Current status: {status}
  - File: {parent_file_path}

Action required:
  1. Review chapter plan: {parent_file_path}
  2. Approve: approve_entity(entity_type='chapter', entity_id='chapter-{chapter_number}')
  3. Then retry: /plan-scene {scene_id}

Hierarchical planning: Chapter must be approved before planning scenes.
```
Stop execution.

**If parent chapter status = 'approved':**
Proceed to Step 5.

### Step 5: Load parent context

Read the parent chapter plan file: `acts/act-{act_number}/chapters/chapter-{chapter_number}/plan.md`

Extract relevant information:
- Chapter objective
- Scene breakdown (which scene number this is)
- Expected events for this scene
- Characters involved
- Setting and timeframe
- Thematic elements

This context will be injected into the planning agent prompt.

### Step 6: Check if scene already exists

Check if `acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/scene-{scene_id}-blueprint.md` exists:

**If file exists:**
- Use MCP tool `get_entity_state` to check status
- Show current status:
  ```
  Scene {scene_id} already exists:
    - Status: {status}
    - File: {file_path}
    - Version: {version_hash[:8]}...
    - Parent: chapter-{chapter_number} (approved)

  Options:
    1. Edit existing blueprint
    2. View current blueprint
    3. Regenerate (creates backup)
    4. Abort
  ```
- Wait for user choice
- If edit → open file, proceed to Step 8
- If view → read and display, stop
- If regenerate → proceed to Step 7 (with backup warning)
- If abort → stop

**If file does not exist:**
Proceed to Step 7.

### Step 7: Create scene blueprint

Launch `planning-coordinator` agent with context injection:

```
Create a detailed scene blueprint for Scene {scene_id} (Chapter {chapter_number}, Scene {scene_number}).

═══════════════════════════════════════════════════════════
PARENT CONTEXT (Chapter {chapter_number} Plan)
═══════════════════════════════════════════════════════════

File: acts/act-{act_number}/chapters/chapter-{chapter_number}/plan.md

{full_content_of_chapter_plan}

═══════════════════════════════════════════════════════════

CRITICAL: Your scene blueprint MUST align with the chapter plan above.

TASK:
Create a comprehensive scene blueprint covering:

1. **Scene Objective**: What is the primary goal of this scene?
2. **Setting**: Where does this scene take place? Time of day?
3. **Characters**: Who appears? What are their roles and goals?
4. **Beats**: Break down the scene into 5-10 beats (narrative units)
   Format:
   - Beat 1: [Action/Event] - [Emotional/Thematic purpose]
   - Beat 2: ...
5. **Conflicts**: What conflicts drive this scene?
6. **Character States**:
   - Entering emotional state for each character
   - Exiting emotional state
   - Knowledge gained/lost
7. **Sensory Details**: Key sensory elements (sight, sound, smell, etc.)
8. **Dialogue Exchanges**: Major dialogue moments (topic, subtext, emotional tone)
9. **Tension Design**: How does tension build/release?
10. **Scene Function**: How does this scene serve the chapter/act?

OUTPUT FORMAT:
Markdown file with clear structure (use ## for sections).

CONSTRAINTS:
- Length: 400-800 words
- Beats: 5-10 narrative beats
- Characters: Only use characters mentioned in chapter plan (or justify new ones)
- Events: Must align with chapter plan's scene breakdown
- Tone: Match chapter's thematic focus

ALIGNMENT REQUIREMENTS:
- If chapter plan specifies events for this scene → include them
- If chapter plan mentions character development → reflect it
- If chapter plan sets emotional tone → maintain it
- If introducing NEW elements → flag explicitly and justify

IMPORTANT:
This is a BLUEPRINT for prose generation. It should be detailed enough that a prose writer can generate 2000-3000 word scene from it without additional planning.

Save to: acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/scene-{scene_id}-blueprint.md
```

**Agent**: `planning-coordinator`
- Uses Planning Workflow (5 phases)
- Interactive approval at key points
- Parent context injected automatically

### Step 8: Verify file created

After agent completes:
- Read `acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/scene-{scene_id}-blueprint.md`
- If missing → show error
- If exists → proceed to Step 9

### Step 9: Automatic state sync

The `state_sync_hook` will automatically:
- Calculate version hash
- Create MCP state for `scene-{scene_id}`
- Set status to 'draft'
- Link to parent: `parent_id = 'chapter-{chapter_number}'`
- Record parent version: `parent_version_hash = {chapter_version_hash}`

**No manual action needed.**

### Step 10: Show results

Display:
```
✅ Scene {scene_id} blueprint created successfully

📁 File: acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/scene-{scene_id}-blueprint.md
📊 Status: draft (not yet approved)
🔢 Version: {version_hash[:8]}...
👆 Parent: chapter-{chapter_number} (approved, v{parent_version[:8]}...)

Next steps:
  1. Review the scene blueprint
  2. Verify alignment with chapter plan
  3. Make any necessary edits
  4. Approve: approve_entity(entity_type='scene', entity_id='scene-{scene_id}')
  5. After approval, generate prose: "Generate scene {scene_id}"

💡 Hierarchical planning: You must approve this scene before generating prose.
```

### Step 11: Suggest approval (optional)

Ask: "Would you like to approve this scene blueprint now? (y/n)"

If yes:
- Use MCP tool `approve_entity(entity_type='scene', entity_id='scene-{scene_id}')`
- Show approval confirmation
- Suggest next action: "Ready to generate prose? Say: 'Generate scene {scene_id}'"

If no:
- Stop

---

## Special Case: Regeneration

If user chooses **Option 3: Regenerate** in Step 6:

### Warning before regeneration:
```
⚠️  WARNING: Regenerating Scene {scene_id}

This will:
  1. Create backup: backups/scene-{scene_id}-blueprint-{timestamp}.md
  2. Generate new scene blueprint
  3. If prose already exists, it will need regeneration

Current scene has generated prose: {exists ? "YES" : "NO"}

If prose exists, you'll need to regenerate it after approving the new blueprint.

Proceed with regeneration? (y/n)
```

If user confirms:
1. Create backup manually or via hook
2. Proceed with Step 7 (create new blueprint)
3. After Step 9 (state sync), show regeneration summary:

```
✅ Scene {scene_id} blueprint regenerated

📁 New blueprint: acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/scene-{scene_id}-blueprint.md
📦 Backup: acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/backups/scene-{scene_id}-blueprint-{timestamp}.md

⚠️  Existing prose (if any) is now outdated
  - If prose file exists: acts/.../content/scene-{scene_id}.md
  - You should regenerate prose after approving new blueprint

Next steps:
  1. Approve new blueprint
  2. Regenerate prose: "Generate scene {scene_id}"
```

**Note**: Scenes have no children, so no cascade invalidation needed.

---

## Error Handling

### Invalid scene ID format
```
❌ Error: Invalid scene ID '{input}'

Scene ID must be 4-digit format: XXYY
  - XX = chapter number (01-99)
  - YY = scene number (01-99)

Examples: 0101, 0205, 1003

Usage: /plan-scene <scene_id> [--act <act_number>]
Example: /plan-scene 0201
```

### Invalid act number
```
❌ Error: Invalid act number '{input}'

Act number must be a positive integer (1, 2, 3, ...)

Usage: /plan-scene <scene_id> --act <act_number>
Example: /plan-scene 0201 --act 2
```

### Parent chapter not approved
See Step 4 error messages.

### File creation failed
```
❌ Error: Failed to create scene blueprint file

The planning agent did not create the expected file.
Please check agent output and try again.
```

### Hierarchy validation blocked by hook
If user somehow bypasses command checks, the `hierarchy_validation_hook` will block:
```
🚫 BLOCKED: Hierarchical planning constraint violation

File: acts/act-{act_number}/chapters/chapter-{chapter_number}/scenes/scene-{scene_id}-blueprint.md
Entity: scene 'scene-{scene_id}'
Parent: chapter 'chapter-{chapter_number}'

Reason: Parent chapter plan not approved (current status: draft)

Action Required:
  1. Approve parent plan first
  2. Use: approve_entity(entity_type='chapter', entity_id='chapter-{chapter_number}')
  3. Then retry this operation
```

---

## Notes

- Parent context injection ensures scene aligns with chapter
- Hooks automatically handle state sync (no cascade - scenes have no children)
- Hierarchical validation enforced at multiple levels (command + hook)
- Scene ID format: XXYY (4 digits) - chapter-{XX}, scene-{YY}
- Scenes are leaf nodes - no children to invalidate

---

## Related Commands

- `/plan-act <act_number>` - Plan parent act first
- `/plan-chapter <chapter_number>` - Plan parent chapter
- `approve_entity()` - Approve scene blueprint
- `get_entity_state()` - Check scene status
- "Generate scene {scene_id}" - Generate prose after approval

---

## Generation Workflow Integration

After scene blueprint is approved:
1. User says: "Generate scene {scene_id}"
2. System launches `generation-coordinator` agent
3. 7-step generation workflow executes:
   - Blueprint validation
   - Verification plan (human approval)
   - Prose generation (with retry)
   - Fast compliance check
   - Full validation (7 validators)
   - Final output
4. Generated prose saved to: `acts/.../content/scene-{scene_id}.md`

See `.workflows/generation.md` for full generation workflow documentation.
