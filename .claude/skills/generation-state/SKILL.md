---
name: generation-state
description: >-
  This skill should be used when the user asks to "generation state", "generation status",
  "check generation progress", "resume generation", "cancel generation", "list generations",
  "/generation-state", "статус генерации", "прогресс генерации", "возобновить генерацию",
  "отменить генерацию", "список генераций", or wants to monitor, resume, or cancel
  scene generation workflows.
---

# Generation State Management

User-friendly interface for managing scene generation workflow states.
Backend: MCP Server `generation-state-tracker`.

## Commands

### `/generation-state status [scene_id]`

Show current status and progress of scene generation(s).

```
/generation-state status           # All active/recent generations
/generation-state status 0204      # Detailed status for scene 0204
```

MCP call: `get_generation_status(scene_id, detailed=True)`

Shows: current step (X/7), time elapsed, step-by-step progress with timings,
status (IN_PROGRESS / WAITING_USER_APPROVAL / FAILED / COMPLETED),
generation attempts count, artifact paths.

### `/generation-state resume <scene_id>`

Resume a failed or interrupted scene generation workflow.

```
/generation-state resume 0204
/generation-state resume 0204 --force   # Force resume even with warnings
```

MCP call: `resume_generation(scene_id, force=False|True)`

1. Load state from `workspace/generation-state-{scene_id}.json`
2. Validate state is resumable (FAILED or CANCELLED)
3. Show recovery plan: completed steps (SKIP), resume point, pending steps
4. Show time saved from skipping completed steps
5. Ask for confirmation before proceeding

Errors: state not found, already completed, currently running, state corrupted.

### `/generation-state cancel <scene_id>`

Cancel a currently running scene generation workflow.

```
/generation-state cancel 0204
/generation-state cancel 0204 --reason "Blueprint has error"
```

MCP call: `cancel_generation(scene_id, reason=None|"...")`

1. Check workflow is running (IN_PROGRESS or WAITING_USER_APPROVAL)
2. Save state with CANCELLED status
3. Show work completed before cancellation
4. Preserve state for future resume

Errors: scene not found, already completed, already cancelled.

### `/generation-state list [filter]`

List all scene generations with current status.

```
/generation-state list                  # All scenes
/generation-state list --active         # IN_PROGRESS, WAITING, FAILED
/generation-state list --completed      # Only COMPLETED
/generation-state list --failed         # Only FAILED (resumable)
```

MCP call: `list_generations(filter, sort_by="started_at")`

Shows table: scene ID, status, step progress, start time, duration, quick actions.

## MCP Tool Mapping

| Command | MCP Tool | Key Parameters |
|---------|----------|----------------|
| `status [id]` | `get_generation_status` | `scene_id, detailed=True` |
| `resume <id>` | `resume_generation` | `scene_id, force` |
| `resume <id> --force` | `resume_generation` | `scene_id, force=True` |
| `cancel <id>` | `cancel_generation` | `scene_id, reason` |
| `cancel <id> --reason "..."` | `cancel_generation` | `scene_id, reason="..."` |
| `list` | `list_generations` | `filter="all", sort_by="started_at"` |
| `list --failed` | `list_generations` | `filter="failed"` |

## Status Legend

| Status | Meaning |
|--------|---------|
| IN_PROGRESS | Workflow currently running |
| WAITING_USER_APPROVAL | Paused at Step 3, needs approval |
| COMPLETED | Successfully finished all 7 steps |
| FAILED | Stopped due to error (can resume) |
| CANCELLED | Manually stopped by user (can resume) |

## Generation Steps (7-step workflow)

1. File System Check
2. Blueprint Validation
3. Verification Plan (human approval)
4. Prose Generation (up to 3 attempts)
5. Fast Compliance Check
6. Full Validation (7 validators in parallel)
7. Final Output

## Argument Parsing

1. Extract subcommand: `status`, `resume`, `cancel`, `list`
2. Extract scene_id (4-digit format, if provided)
3. Extract flags: `--force`, `--active`, `--completed`, `--failed`, `--reason "..."`
4. Validate scene_id format
5. Map to MCP tool and call

## Error Messages

Provide clear, actionable errors:

- State not found → suggest checking scene ID, listing all generations, or starting new
- Currently running → suggest waiting, checking status, or cancelling
- Already completed → inform, no action needed
- State corrupted → cannot resume, suggest starting fresh

## Additional Resources

### Reference Files

- **`references/interaction-patterns.md`** — User interaction patterns: happy path,
  recovery from failure, monitoring active generation, cancellation workflow

## Integration

Requires MCP server `generation-state-tracker`. Verify with `/mcp list`.

State files stored at: `workspace/generation-state-{scene_id}.json`

Related: generation-coordinator agent (orchestrates the 7-step workflow).
