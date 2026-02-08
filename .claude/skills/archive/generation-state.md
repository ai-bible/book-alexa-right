# Generation State Management Skill

**Skill Name:** `generation-state`
**Version:** 1.0.0
**Feature:** FEAT-0002 Workflow State Tracking
**Architecture:** Frontend component of Hybrid (MCP + Skill) system

---

## Purpose

User-friendly interface for managing FEAT-0001 scene generation workflow states. Provides slash commands for:
- Checking generation progress
- Resuming failed/interrupted workflows
- Canceling running workflows
- Listing all generation states

**Backend:** Uses MCP Server `generation-state-tracker` tools under the hood.

---

## Commands

### `/generation-state status [scene_id]`

**Description:** Show current status and progress of scene generation(s)

**Usage:**
```bash
/generation-state status           # Show all active/recent generations
/generation-state status 0204      # Show detailed status for scene 0204
```

**What It Does:**
1. Calls MCP tool `get_generation_status`
2. Formats output with:
   - Current step (X/7)
   - Time elapsed
   - Step-by-step progress with timings
   - Current status (IN_PROGRESS, WAITING_USER_APPROVAL, FAILED, COMPLETED)
   - Next action required (if any)

**Example Output:**

```markdown
📊 GENERATION STATUS: Scene 0204

Session ID: 2025-11-03-143045-scene-0204
Started: 2025-11-03T14:30:45Z (6 minutes ago)

Progress: Step 4/7 (IN_PROGRESS)
Current Phase: Generation

## 📋 Detailed Progress

✓ **File System Check** (COMPLETED) - 1s
✓ **Blueprint Validation** (COMPLETED) - 19s
✓ **Verification Plan** (COMPLETED) - 12s
⏳ **Prose Generation** (IN_PROGRESS) - 3m 15s
⋯ **Fast Compliance Check** (PENDING)
⋯ **Full Validation** (PENDING)
⋯ **Final Output** (PENDING)

Generation Attempts: 2/3

## 📁 Artifacts
- **blueprint_path**: acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md
- **constraints_list_path**: workspace/artifacts/scene-0204-constraints.json
- **draft_path**: workspace/artifacts/scene-0204-draft.md

🔄 Auto-refresh: Run command again to update
```

---

### `/generation-state resume <scene_id>`

**Description:** Resume a failed or interrupted scene generation workflow

**Usage:**
```bash
/generation-state resume 0204
/generation-state resume 0204 --force   # Force resume even if warnings
```

**What It Does:**
1. Loads state from `workspace/generation-state-{scene_id}.json`
2. Validates state is resumable (FAILED or CANCELLED status)
3. Calls MCP tool `resume_generation`
4. Continues workflow from last completed step
5. Shows recovery plan before proceeding

**Example Output:**

```markdown
🔧 RESUMING GENERATION: Scene 0204

📂 Loading state: workspace/generation-state-0204.json

✓ State loaded:
  - Session ID: 2025-11-03-143045-scene-0204
  - Started: 2025-11-03T14:30:45Z
  - Failed at: Step 4 (Prose Generation)
  - Reason: Max attempts reached (3/3) - location constraint violated

📋 Recovery Plan:

✓ Step 1: File System Check (SKIP - already completed, 1s)
✓ Step 2: Blueprint Validation (SKIP - already completed, 19s)
✓ Step 3: Verification Plan (SKIP - already completed, user approved)
⚠️ Step 4: Prose Generation (RESUME - was at this step)
   → Will reset attempts counter
   → Will re-read blueprint (may have been fixed)
   → Will use enhanced constraint emphasis
⏭️ Step 5: Fast Compliance Check (will run after Step 4)
⏭️ Step 6: Full Validation (will run after Step 5)
⏭️ Step 7: Final Output (will run after Step 6)

⚡ Time saved: ~52 seconds (Steps 1-3 already completed)

❓ Proceed with resume? The generation-coordinator will continue from this state.
```

**Error Handling:**
- If state file not found → "No state found for scene {ID}"
- If workflow completed → "Scene {ID} already completed"
- If workflow in progress → "Scene {ID} is currently running. Cancel first or wait."
- If state corrupted → "State file corrupted. Cannot resume."

---

### `/generation-state cancel <scene_id>`

**Description:** Cancel a currently running scene generation workflow

**Usage:**
```bash
/generation-state cancel 0204
/generation-state cancel 0204 --reason "Blueprint has error"
```

**What It Does:**
1. Checks if workflow is running (status: IN_PROGRESS or WAITING_USER_APPROVAL)
2. Calls MCP tool `cancel_generation`
3. Saves current state with status CANCELLED
4. Cleans up running agents (if applicable)
5. Shows what was completed before cancellation

**Example Output:**

```markdown
🛑 CANCELLING GENERATION: Scene 0204

⏸️ Previous status: IN_PROGRESS (Step 4/7)

✓ Cancelled successfully

📊 Work completed before cancellation:
   ✓ Step 1: File System Check (1s)
   ✓ Step 2: Blueprint Validation (19s)
   ✓ Step 3: Verification Plan (12s)
   ⏳ Step 4: Prose Generation (2m 15s, INTERRUPTED)

💾 State saved: workspace/generation-state-0204.json
   - Can resume later with: /generation-state resume 0204

📝 Cancellation reason: Blueprint has error

🗑️ Cleanup:
   - State preserved for future resume
   - Artifacts preserved:
     • acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md
     • workspace/artifacts/scene-0204-constraints.json
     • workspace/artifacts/scene-0204-draft-partial.md
```

**Error Handling:**
- If scene ID not found → "No generation found for scene {ID}"
- If already completed → "Cannot cancel completed workflow"
- If already cancelled → "Scene {ID} was already cancelled"

---

### `/generation-state list [filter]`

**Description:** List all scene generations with current status

**Usage:**
```bash
/generation-state list                  # All scenes
/generation-state list --active         # Only active/failed
/generation-state list --completed      # Only completed
/generation-state list --failed         # Only failed
```

**What It Does:**
1. Calls MCP tool `list_generations`
2. Reads all state files from `workspace/generation-state-*.json`
3. Filters by requested criteria
4. Formats as table with key info

**Example Output:**

```markdown
📋 GENERATION STATES (5 total)

┌────────┬──────────────┬─────────┬──────────────┬──────────┬──────────┐
│ Scene  │ Status       │ Step    │ Started      │ Duration │ Actions  │
├────────┼──────────────┼─────────┼──────────────┼──────────┼──────────┤
│ 0204   │ IN_PROGRESS  │ 4/7     │ 14:30 (6m)   │ 6m 15s   │ [Status] │
│ 0203   │ COMPLETED    │ 7/7     │ 11:22 (3h)   │ 7m 42s   │ [View]   │
│ 0202   │ FAILED       │ 4/7     │ Yesterday    │ 11m 05s  │ [Resume] │
│ 0201   │ COMPLETED    │ 7/7     │ 2025-11-01   │ 6m 33s   │ [View]   │
│ 0105   │ CANCELLED    │ 2/7     │ 2025-10-31   │ 0m 22s   │ [Resume] │
└────────┴──────────────┴─────────┴──────────────┴──────────┴──────────┘

Legend:
  • IN_PROGRESS: Workflow currently running
  • WAITING_USER_APPROVAL: Paused at Step 3, needs approval
  • COMPLETED: Successfully finished all 7 steps
  • FAILED: Stopped due to error (can resume)
  • CANCELLED: Manually stopped by user (can resume)

💡 Quick actions:
   - Check details: /generation-state status 0204
   - Resume failed: /generation-state resume 0202
   - Cancel running: /generation-state cancel 0204

🔍 Filters:
   --active     Show only IN_PROGRESS, WAITING_USER_APPROVAL, FAILED
   --completed  Show only COMPLETED
   --failed     Show only FAILED (resumable)
```

---

## Implementation

### Skill Structure

```markdown
# When invoked, this skill:

## 1. Parses Command
- Extracts subcommand: status, resume, cancel, list
- Extracts scene_id (if provided)
- Extracts flags: --force, --active, --reason, etc.

## 2. Validates Input
- scene_id format (4 digits)
- Subcommand is valid
- Required parameters present

## 3. Calls MCP Tool
- Maps subcommand to MCP tool:
  - `status` → `get_generation_status(scene_id, detailed=True)`
  - `resume` → `resume_generation(scene_id, force=False)`
  - `cancel` → `cancel_generation(scene_id, reason=None)`
  - `list` → `list_generations(filter='all', sort_by='started_at')`

## 4. Formats Output
- Adds emoji icons for visual clarity
- Formats tables for readability
- Adds actionable next steps
- Includes error guidance
```

### MCP Tool Mapping

| Skill Command | MCP Tool | Parameters |
|---------------|----------|------------|
| `/generation-state status 0204` | `get_generation_status` | `scene_id="0204", detailed=True` |
| `/generation-state resume 0204` | `resume_generation` | `scene_id="0204", force=False` |
| `/generation-state resume 0204 --force` | `resume_generation` | `scene_id="0204", force=True` |
| `/generation-state cancel 0204` | `cancel_generation` | `scene_id="0204", reason=None` |
| `/generation-state cancel 0204 --reason "..."` | `cancel_generation` | `scene_id="0204", reason="..."` |
| `/generation-state list` | `list_generations` | `filter="all", sort_by="started_at"` |
| `/generation-state list --failed` | `list_generations` | `filter="failed", sort_by="started_at"` |

---

## User Interaction Patterns

### Pattern 1: Happy Path Generation

```
User: "Generate scene 0204"
→ generation-coordinator starts workflow
→ MCP auto-injects state context (conditional)
→ Workflow runs Steps 1-7
→ State updated in real-time

User: /generation-state status 0204
→ Shows "Step 4/7, Attempt 2/3, 3m 15s elapsed"
```

### Pattern 2: Recovery from Failure

```
User: /generation-state list --failed
→ Shows scene 0202 failed at Step 4

User: /generation-state status 0202
→ Shows error details

User fixes blueprint

User: /generation-state resume 0202
→ Workflow continues from Step 4
```

### Pattern 3: Monitoring Active Generation

```
User: /generation-state status 0204
→ "Step 4/7, Attempt 2/3, 3m 15s elapsed"

User waits 2 minutes

User: /generation-state status 0204
→ "Step 5/7, Fast Compliance Check, 5m 42s elapsed"
```

### Pattern 4: Cancellation

```
User realizes blueprint has error mid-generation

User: /generation-state cancel 0204
→ State saved with CANCELLED status

User fixes blueprint

User: /generation-state resume 0204
→ Workflow restarts from last completed step
```

---

## Error Messages

**Clear, actionable error messages:**

```markdown
❌ ERROR: No state found for scene 0204

Possible reasons:
  1. Scene never generated
  2. State file deleted
  3. Wrong scene ID

💡 Next steps:
  - Check scene exists: acts/act-1/chapters/.../scene-0204-blueprint.md
  - List all generations: /generation-state list
  - Start new generation: "Generate scene 0204"
```

```markdown
❌ ERROR: Scene 0204 is currently running

Current status: Step 4/7 (IN_PROGRESS)
Started: 2025-11-03T14:30:45Z (6 minutes ago)

💡 Options:
  - Wait for completion (~2-3 minutes remaining)
  - Check progress: /generation-state status 0204
  - Cancel if needed: /generation-state cancel 0204
```

---

## Integration with MCP Server

**This skill requires:** `generation-state-tracker` MCP server

**Check MCP server is loaded:**
```bash
# List MCP servers
/mcp list

# Should show:
# - generation-state-tracker (✓ loaded)
```

**If MCP server not loaded:**
1. Check Claude Code config: `~/.claude/config.json`
2. Verify MCP server path is correct
3. Restart Claude Code

---

## Examples

### Example 1: Check All Active Generations

```bash
/generation-state list --active
```

Output:
```markdown
📋 GENERATION STATES (2 total)

┌────────┬──────────────┬─────────┬──────────────┬──────────┬──────────┐
│ Scene  │ Status       │ Step    │ Started      │ Duration │ Actions  │
├────────┼──────────────┼─────────┼──────────────┼──────────┼──────────┤
│ 0204   │ IN_PROGRESS  │ 4/7     │ 14:30 (6m)   │ 6m 15s   │ [Status] │
│ 0202   │ FAILED       │ 4/7     │ Yesterday    │ 11m 05s  │ [Resume] │
└────────┴──────────────┴─────────┴──────────────┴──────────┴──────────┘
```

### Example 2: Resume Failed Generation

```bash
/generation-state resume 0202
```

Output:
```markdown
🔧 RESUMING GENERATION: Scene 0202

✓ State loaded
⚡ Time saved: ~52 seconds (Steps 1-3 already completed)
❓ Proceed with resume?
```

### Example 3: Cancel with Reason

```bash
/generation-state cancel 0204 --reason "Need to update blueprint constraints"
```

Output:
```markdown
🛑 CANCELLING GENERATION: Scene 0204

✓ Cancelled successfully
💾 State saved for future resume
📝 Cancellation reason: Need to update blueprint constraints
```

---

## Testing

### Manual Testing

```bash
# 1. Start generation (will fail for testing)
User: "Generate scene 9999"

# 2. Check status
/generation-state status 9999

# 3. List all
/generation-state list

# 4. Try resume
/generation-state resume 9999

# 5. Cancel (if running)
/generation-state cancel 9999 --reason "Testing cancellation"
```

### Expected Behavior

- Commands parse correctly
- MCP tools invoked with correct parameters
- Output formatted nicely
- Error messages clear and actionable
- Flags (--force, --active, etc.) work

---

## Future Enhancements (Out of Scope for v1.0)

1. **Auto-refresh status** (watch mode)
   ```bash
   /generation-state status 0204 --watch
   # Updates every 10 seconds until complete
   ```

2. **Retry with modified constraints**
   ```bash
   /generation-state resume 0204 --enhance-constraint "location"
   # Emphasizes specific constraint on retry
   ```

3. **Batch operations**
   ```bash
   /generation-state cancel --all-failed
   /generation-state resume --all-failed
   ```

4. **Export state as report**
   ```bash
   /generation-state export 0204 --format markdown
   # Creates human-readable report
   ```

---

## Documentation Links

- **Feature Spec:** `features/FEAT-0002-workflow-state-tracking/README.md`
- **MCP Server:** `mcp-servers/generation_state_mcp.py`
- **MCP Server README:** `mcp-servers/README.md`
- **Generation Workflow:** `.workflows/generation.md`
- **Coordinator Agent:** `.claude/agents/generation/generation-coordinator.md`

---

## Version History

**v1.0.0** (2025-11-03)
- Initial release
- 4 commands: status, resume, cancel, list
- MCP integration
- Hybrid architecture (Skill + MCP Server)

---

**Last Updated:** 2025-11-03
**Author:** AI-Assisted Writing System
**Status:** Specification (Ready for Implementation)
