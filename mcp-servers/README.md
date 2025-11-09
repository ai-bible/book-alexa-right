# Generation State Tracker MCP Server

**Feature:** FEAT-0002 Workflow State Tracking
**Version:** 1.0.0
**Language:** Python
**Framework:** FastMCP (MCP Python SDK)

---

## Overview

This MCP server provides tools to manage FEAT-0001 scene generation workflow states. It enables tracking, resuming, and monitoring of generation workflows through persistent state files.

### Key Features

**Read-Only Operations:**
- ✅ **Resume failed workflows** from saved state (skips completed steps)
- 📊 **Real-time status** tracking with detailed progress
- 🛑 **Cancel running workflows** with state preservation
- 📋 **List all generations** with filtering and sorting

**Write Operations (NEW):**
- 🚀 **Initialize workflows** with `start_generation`
- ⏱️ **Track step progress** with `start_step` and `complete_step`
- ⚠️ **Record errors** without failing workflow (`record_error`)
- ❌ **Fail workflows** gracefully (`fail_generation`)
- ✅ **Complete workflows** with metrics (`complete_generation`)
- 💬 **Log user questions** for audit trail (`log_question_answer`)

---

## Tools

### Read-Only Tools (Status & Monitoring)

#### 1. `resume_generation`

Resume a failed or interrupted scene generation workflow from saved state.

**Parameters:**
- `scene_id` (string, required): Scene ID to resume (4 digits, e.g., '0204')
- `force` (boolean, optional): Force resume even if warnings present (default: false)

**Returns:** Markdown-formatted resume plan with:
- Loaded state summary
- Resume point (which step to continue from)
- Completed steps (will be skipped)
- Time saved by resuming

**Example:**
```python
resume_generation(scene_id="0204", force=False)
```

---

#### 2. `get_generation_status`

Get current status and progress of a scene generation workflow.

**Parameters:**
- `scene_id` (string, required): Scene ID to check (4 digits, e.g., '0204')
- `detailed` (boolean, optional): Include detailed step breakdown (default: false)

**Returns:** Markdown-formatted status report with:
- Current step (X/7) and phase
- Time elapsed since start
- Step-by-step progress (if detailed=true)
- Artifact paths
- Error messages (if any)

**Example:**
```python
get_generation_status(scene_id="0204", detailed=True)
```

---

#### 3. `cancel_generation`

Cancel a currently running scene generation workflow.

**Parameters:**
- `scene_id` (string, required): Scene ID to cancel (4 digits, e.g., '0204')
- `reason` (string, optional): Optional reason for cancellation

**Returns:** Markdown-formatted cancellation report with:
- Cancellation confirmation
- Completed steps (preserved)
- State file path (for future resume)

**Example:**
```python
cancel_generation(scene_id="0204", reason="Blueprint has error")
```

---

#### 4. `list_generations`

List all scene generations with their current status.

**Parameters:**
- `filter` (enum, optional): Filter by status - 'all', 'active', 'failed', 'completed' (default: 'all')
- `sort_by` (string, optional): Sort by field - 'scene_id', 'started_at', 'status' (default: 'started_at')

**Returns:** Markdown-formatted table with:
- Scene ID
- Status
- Current step
- Started time
- Duration
- Quick actions

**Example:**
```python
list_generations(filter="failed", sort_by="started_at")
```

---

### Write Tools (State Management)

#### 5. `start_generation`

Initialize a new scene generation workflow by creating state file.

**Parameters:**
- `scene_id` (string, required): Scene ID to initialize (4 digits, e.g., '0204')
- `blueprint_path` (string, required): Path to blueprint file
- `initiated_by` (string, optional): Name of initiator (default: 'generation-coordinator')
- `metadata` (dict, optional): Optional tracking metadata

**Returns:** Markdown initialization report with:
- Session ID (unique identifier)
- Initial workflow status
- State file path
- Next steps guidance

**Idempotency:** Returns warning if state file already exists (doesn't fail)

**Example:**
```python
start_generation(
    scene_id="0204",
    blueprint_path="acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md",
    initiated_by="generation-coordinator"
)
```

---

#### 6. `start_step`

Mark a workflow step as IN_PROGRESS and record start timestamp.

**Parameters:**
- `scene_id` (string, required): Scene ID (4 digits)
- `step_number` (int, required): Step to start (1-7)
- `phase_name` (string, required): Human-readable phase name (e.g., 'Blueprint Validation')
- `agent_name` (string, optional): Name of executing agent

**Returns:** Markdown confirmation with current step status

**Idempotency:** Updates timestamp if step already IN_PROGRESS

**Example:**
```python
start_step(
    scene_id="0204",
    step_number=1,
    phase_name="File System Check",
    agent_name="generation-coordinator"
)
```

---

#### 7. `complete_step`

Mark a workflow step as COMPLETED, record duration, and advance workflow.

**Parameters:**
- `scene_id` (string, required): Scene ID
- `step_number` (int, required): Step to complete (1-7)
- `duration_seconds` (float, required): Step execution time
- `artifacts` (dict, optional): Artifact paths produced by this step
- `metadata` (dict, optional): Additional step metadata

**Returns:** Markdown summary with completed step info and next step guidance

**Idempotency:** Returns info message if step already COMPLETED

**Example:**
```python
complete_step(
    scene_id="0204",
    step_number=1,
    duration_seconds=45.2,
    artifacts={"constraints_list_path": "workspace/artifacts/scene-0204-constraints.json"}
)
```

---

#### 8. `record_error`

Record an error in the errors array WITHOUT changing workflow_status (non-terminal).

**Parameters:**
- `scene_id` (string, required): Scene ID
- `step_number` (int, required): Step where error occurred (1-7)
- `error_type` (string, required): Error category (e.g., 'location_constraint_violated')
- `error_message` (string, required): Detailed error description
- `severity` (enum, required): 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'
- `retry_count` (int, optional): Retry attempt number

**Returns:** Markdown confirmation with error count and severity

**Idempotency:** NOT idempotent - each call adds new error to array

**Difference from fail_generation:**
- `record_error`: Logs error, keeps workflow IN_PROGRESS, allows retry
- `fail_generation`: Logs error, sets workflow_status=FAILED (terminal)

**Example:**
```python
record_error(
    scene_id="0204",
    step_number=4,
    error_type="location_constraint_violated",
    error_message="Location constraint violated: Found больница, required Башня Книжников",
    severity="HIGH",
    retry_count=1
)
```

---

#### 9. `fail_generation`

Mark workflow as FAILED (terminal state) after all retry attempts exhausted.

**Parameters:**
- `scene_id` (string, required): Scene ID
- `step_number` (int, required): Step where failure occurred (1-7)
- `failure_reason` (string, required): Detailed failure explanation
- `final_errors` (list, optional): All error dicts to record

**Returns:** Markdown failure report with resume instructions

**Idempotency:** Updates failure_reason if already FAILED

**Example:**
```python
fail_generation(
    scene_id="0204",
    step_number=4,
    failure_reason="Location constraint violated - max attempts reached (3/3)",
    final_errors=[]
)
```

---

#### 10. `complete_generation`

Mark workflow as COMPLETED (terminal state) after successful generation.

**Parameters:**
- `scene_id` (string, required): Scene ID
- `final_scene_path` (string, required): Path to generated scene file
- `validation_report_path` (string, required): Path to validation report
- `word_count` (int, required): Final word count
- `total_duration_seconds` (float, required): Total workflow duration
- `retry_count` (int, optional): Number of retries (default: 0)

**Returns:** Markdown success report with final metrics

**Idempotency:** Returns success message if already COMPLETED

**Example:**
```python
complete_generation(
    scene_id="0204",
    final_scene_path="acts/act-1/chapters/chapter-02/content/scene-0204.md",
    validation_report_path="workspace/artifacts/scene-0204-validation-report.md",
    word_count=2847,
    total_duration_seconds=324.5,
    retry_count=1
)
```

---

#### 11. `log_question_answer` (BONUS)

Log QuestionTool interaction to state for audit trail and decision tracking.

**Parameters:**
- `scene_id` (string, required): Scene ID
- `question` (string, required): Question asked to user via QuestionTool
- `answer` (string, required): User's answer
- `timestamp` (string, optional): ISO format timestamp (auto-generated if not provided)

**Returns:** Markdown confirmation with question/answer summary

**Idempotency:** NOT idempotent - each call adds new Q&A entry

**Use Cases:**
- Audit trail for user decisions during workflow
- Context preservation for future workflow steps
- Analytics on user interaction patterns

**Example:**
```python
log_question_answer(
    scene_id="0204",
    question="Approve verification plan for Step 3?",
    answer="Yes, proceed with generation"
)
```

---

## Installation

### 1. Install Dependencies

```bash
pip install -r mcp-servers/requirements.txt
```

Requirements:
- `mcp>=1.0.0` - MCP Python SDK with FastMCP
- `pydantic>=2.0.0` - Input validation

### 2. Configure Claude Code

Add to your Claude Code config file (`~/.claude/config.json` or project-specific config):

```json
{
  "mcpServers": {
    "generation-state-tracker": {
      "command": "python",
      "args": [
        "E:\\sources\\book-alexa-right\\mcp-servers\\generation_state_mcp.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

**Important:** Adjust the path to match your installation location.

### 3. Restart Claude Code

After adding the configuration, restart Claude Code to load the MCP server.

---

## Usage

### State Lifecycle

**Complete workflow state lifecycle:**

```
┌──────────────────────────────────────────────────────────────┐
│  1. start_generation(scene_id, blueprint_path)               │
│     → Creates state file, initializes workflow               │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  2. For each step (1-7):                                     │
│     a) start_step(scene_id, step_number, phase_name)         │
│        → Marks step IN_PROGRESS                              │
│     b) Perform step operations                               │
│     c) complete_step(scene_id, step_number, duration)        │
│        → Marks step COMPLETED, advances workflow             │
│                                                              │
│     On error during step:                                    │
│     - record_error(scene_id, step, error_type, message)      │
│       → Logs error, keeps workflow IN_PROGRESS               │
│     - Retry or...                                            │
│     - fail_generation(scene_id, failure_reason)              │
│       → Sets workflow_status=FAILED (terminal)               │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼ (all 7 steps completed)
┌──────────────────────────────────────────────────────────────┐
│  3. complete_generation(scene_id, paths, metrics)            │
│     → Sets workflow_status=COMPLETED (terminal)              │
└──────────────────────────────────────────────────────────────┘

Optional: log_question_answer() - anytime during workflow
```

### Basic Workflow

**Automatic (via generation-coordinator):**
1. **Start generation**:
   ```
   User: "Generate scene 0204"
   ```
   Coordinator automatically calls: `start_generation` → `start_step` → operations → `complete_step` → ... → `complete_generation`

**Manual monitoring:**
2. **Check progress** during generation:
   ```python
   get_generation_status(scene_id="0204")
   ```

3. **If generation fails**, resume from checkpoint:
   ```python
   resume_generation(scene_id="0204")
   ```

4. **List all generations** to see overview:
   ```python
   list_generations(filter="active")
   ```

---

## State File Structure

State files are JSON, located at: `workspace/generation-state-{scene_id}.json`

**Key fields:**
```json
{
  "scene_id": "0204",
  "session_id": "2025-11-03-143045-scene-0204",
  "workflow_status": "IN_PROGRESS",
  "current_step": 4,
  "started_at": "2025-11-03T14:30:45Z",
  "updated_at": "2025-11-03T14:36:24Z",

  "steps": {
    "step_1_file_check": {
      "status": "COMPLETED",
      "started_at": "...",
      "completed_at": "...",
      "duration_seconds": 1
    }
    // ... steps 2-7
  },

  "generation_attempts": {
    "current_attempt": 2,
    "max_attempts": 3
  },

  "artifacts": {
    "blueprint_path": "...",
    "draft_path": "...",
    "final_scene_path": "..." // Added on completion
  },

  "errors": [],

  "user_questions": [  // NEW: QuestionTool logging
    {
      "question": "Approve verification plan for Step 3?",
      "answer": "Yes, proceed",
      "timestamp": "2025-11-03T14:32:15Z"
    }
  ],

  "completion_metrics": {  // Added on completion
    "final_scene_path": "...",
    "validation_report_path": "...",
    "word_count": 2847,
    "total_duration_seconds": 324.5,
    "retry_count": 1
  }
}
```

---

## Error Handling

All tools return clear, actionable error messages:

### File Not Found
```
❌ ERROR: No state found for scene 0204

Possible reasons:
  1. Scene never generated
  2. State file deleted
  3. Wrong scene ID

💡 Next steps:
  - Check scene exists: acts/.../scene-0204-blueprint.md
  - List all generations: Use list_generations tool
  - Start new generation: "Generate scene 0204"
```

### Corrupted State
```
Error: State file corrupted: workspace/generation-state-0204.json. JSON error: Expecting property name...
```

### Wrong Status
```
❌ ERROR: Scene 0204 already completed

Completed at: 2025-11-03T15:42:33Z
Session ID: 2025-11-03-143045-scene-0204

💡 View final output: acts/act-1/chapters/chapter-02/content/scene-0204.md
```

---

## Testing

### Manual Testing

```bash
# 1. Run server in background (for manual testing)
# Note: MCP servers are long-running processes
python mcp-servers/generation_state_mcp.py
```

### Testing with Claude Code

Once configured, test by:

1. Start a generation that will fail:
   ```
   User: "Generate scene 9999"  # Non-existent scene
   ```

2. Check list:
   ```python
   list_generations()
   ```

3. Resume:
   ```python
   resume_generation(scene_id="0204")
   ```

---

## Integration

### With generation-coordinator

The `generation-coordinator` agent must be updated to:

1. **Create state.json** at workflow start (Step 1)
2. **Update state.json** after each step completion
3. **Check for existing state** before starting new generation
4. **Resume from state** if state exists and workflow failed

See: `.claude/agents/generation/generation-coordinator.md`

### With Claude Code Skill

A companion skill provides user-friendly commands:

- `/generation-state status 0204`
- `/generation-state resume 0204`
- `/generation-state cancel 0204`
- `/generation-state list --failed`

See: `.claude/skills/generation-state.md`

---

## Architecture

```
┌─────────────────────────────────────────┐
│  USER / CLAUDE CODE                     │
└─────────────┬───────────────────────────┘
              │
              ├─────────────────────┐
              │                     │
              ▼                     ▼
┌─────────────────────┐  ┌──────────────────────┐
│  MCP SERVER         │  │  SKILL               │
│  (Backend)          │  │  (Frontend)          │
│                     │  │                      │
│  Tools:             │  │  Commands:           │
│  - resume           │◀─┤  /generation-state   │
│  - status           │  │                      │
│  - cancel           │  │  Formats output      │
│  - list             │  │  for users           │
│                     │  │                      │
│  Manages:           │  └──────────────────────┘
│  - State files      │
│  - File I/O         │
│  - Validation       │
└─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  STATE FILES                            │
│  workspace/generation-state-*.json      │
└─────────────────────────────────────────┘
```

---

## Performance

- **resume_generation**: 100-200ms (reads one JSON file)
- **get_generation_status**: <100ms (reads one JSON file)
- **cancel_generation**: <200ms (updates one JSON file)
- **list_generations**: <500ms (reads all state files, typically <50)

State files are small (<100KB), so performance is fast.

---

## Troubleshooting

### MCP server not loading

1. Check config path is correct
2. Verify Python is in PATH
3. Check dependencies installed: `pip list | grep mcp`
4. Restart Claude Code

### Tools not appearing

1. Check MCP server is running: `ps aux | grep generation_state_mcp`
2. Check logs (if configured)
3. Restart Claude Code

### State file errors

1. Check workspace/ directory exists
2. Verify write permissions
3. Check for corrupted JSON: `python -m json.tool workspace/generation-state-0204.json`

---

## Development

### Adding New Tools

1. Define Pydantic input model
2. Create tool function with `@mcp.tool` decorator
3. Add comprehensive docstring
4. Test with sample inputs
5. Update README

### Code Quality Checklist

- [ ] All tools have Pydantic input models
- [ ] All tools have comprehensive docstrings
- [ ] All tools have error handling
- [ ] All tools return markdown-formatted output
- [ ] Shared logic extracted into utility functions
- [ ] Type hints used throughout
- [ ] Async/await for all I/O operations

---

## License

Proprietary - for personal use in book writing project

---

## Version History

**v2.0.0** (2025-11-03) - Phase 1: Write Operations
- ✅ Added 7 new state management tools
- 🚀 `start_generation` - Initialize workflow
- ⏱️ `start_step` / `complete_step` - Track step progress
- ⚠️ `record_error` - Non-terminal error logging
- ❌ `fail_generation` - Terminal failure state
- ✅ `complete_generation` - Terminal success state
- 💬 `log_question_answer` - QuestionTool audit trail (BONUS)
- 📊 Total: 11 tools (4 read-only + 7 write)
- 🔧 Added helper functions for state management
- 📝 Enhanced state file schema with `user_questions` and `completion_metrics`

**v1.0.0** (2025-11-03) - Initial Release
- Initial release
- 4 read-only tools: resume, status, cancel, list
- State file persistence
- Markdown-formatted outputs
- Comprehensive error handling

---

**Last Updated:** 2025-11-03
**Author:** AI-Assisted Writing System
**Status:** Production Ready
