# Scene Generation Workflow v2.0

**Status**: Draft (для review перед рефакторингом)
**Date**: 2025-11-08
**Changes from v1**: Step naming convention с поддержкой иерархической структуры workflows

---

## Naming Convention

### Pattern:
```
{scope}:{phase}[:{category}][:{action}]
```

**Scope**: уровень workflow (act, chapter, scene)
**Phase**: тип операции (plan, gen)
**Category**: группировка шагов (setup, draft, review, publish)
**Action**: конкретное действие (files, blueprint, prose, etc.)

### Categories (литературные термины):
- **setup** - подготовка, проверки, настройка
- **draft** - создание черновика
- **review** - валидация, проверка качества
- **publish** - финализация, публикация

---

## Workflow Steps (6 steps)

### Overview Table

| Step | Step Name | Category | Agent | Duration | Human Interaction |
|------|-----------|----------|-------|----------|-------------------|
| 1 | `scene:gen:setup:files` | Setup | None (coordinator) | <2s | No |
| 2 | `scene:gen:setup:blueprint` | Setup | blueprint-validator | 15-30s | No |
| 3 | `scene:gen:setup:plan` | Setup | verification-planner | 15-45s | **Yes (approval required)** |
| 4 | `scene:gen:draft:prose` | Draft | prose-writer + fast-checker | 3-5min | No |
| 5 | `scene:gen:review:validation` | Review | validation-aggregator | 1-2min | No |
| 6 | `scene:gen:publish:output` | Publish | None (coordinator) | <10s | No |

**Total Duration**: 5-8 minutes (including ~30s human approval)

---

## STEP 1: File System Check

**Step Name**: `scene:gen:setup:files`
**Category**: Setup
**Phase Name**: "File System Check"
**Agent**: None (coordinator executes)

### Purpose
Проверить существование blueprint файла перед началом генерации.

### Process
1. Parse scene_id from user request (e.g., "0204")
2. Determine paths:
   ```
   blueprint: acts/act-{N}/chapters/chapter-{NN}/scenes/scene-{ID}-blueprint.md
   output: acts/act-{N}/chapters/chapter-{NN}/content/scene-{ID}.md
   ```
3. Check blueprint file exists
4. **IF NOT FOUND** → FAIL with message: "Blueprint not found. Run /plan-story first."

### MCP Calls
```python
# Start
mcp_call("start_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:files",
    "phase_name": "File System Check"
})

# Success
mcp_call("complete_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:files",
    "duration_seconds": 0.5
})

# Failure
mcp_call("fail_generation", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:files",
    "failure_reason": "Blueprint not found at {path}"
})
```

### Outputs
- None (just validation)

### Dependencies
- **Requires**: `scene:plan:blueprint` (blueprint must exist)

---

## STEP 2: Blueprint Validation

**Step Name**: `scene:gen:setup:blueprint`
**Category**: Setup
**Phase Name**: "Blueprint Validation"
**Agent**: `blueprint-validator`

### Purpose
Валидировать корректность и полноту blueprint перед генерацией.

### Process
1. Launch `blueprint-validator` agent
2. Agent checks:
   - All required sections present
   - Constraints are valid
   - World-bible references exist
   - Character references exist
   - No conflicting constraints
3. Agent outputs: `workspace/artifacts/scene-{ID}/validation-result.json`
4. Coordinator reads result
5. **IF FAIL** → STOP workflow, show errors to user
6. **IF PASS** → Extract constraints to `constraints-list.json`

### MCP Calls
```python
# Start
mcp_call("start_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:blueprint",
    "phase_name": "Blueprint Validation",
    "agent_name": "blueprint-validator"
})

# Success
mcp_call("complete_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:blueprint",
    "duration_seconds": 18.3,
    "artifacts": {
        "validation_result_path": "workspace/artifacts/scene-{ID}/validation-result.json",
        "constraints_path": "workspace/artifacts/scene-{ID}/constraints-list.json"
    }
})

# Failure
mcp_call("fail_generation", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:blueprint",
    "failure_reason": "Blueprint validation failed: {errors}",
    "final_errors": [...]
})
```

### Outputs
- `validation-result.json` - validation status + extracted constraints
- `constraints-list.json` - structured constraints for prose-writer

### Dependencies
- **Requires**: `scene:gen:setup:files` completed

---

## STEP 3: Verification Plan

**Step Name**: `scene:gen:setup:plan`
**Category**: Setup
**Phase Name**: "Verification Plan"
**Agent**: `verification-planner`

### Purpose
Создать human-readable план проверок и получить одобрение пользователя.

### Process
1. Launch `verification-planner` agent
2. Agent transforms technical constraints → readable verification plan
3. Agent outputs: `workspace/artifacts/scene-{ID}/verification-plan.md`
4. **Coordinator shows plan to user**
5. **HUMAN APPROVAL LOOP** (max 5 iterations):
   ```
   User input:
   - "Y" / "yes" → approve, continue
   - "n" / "no" → cancel workflow
   - "modify: {request}" → agent updates plan, show again
   ```
6. **IF APPROVED** → continue to Step 4
7. **IF CANCELLED** → `cancel_generation()`, STOP

### MCP Calls
```python
# Start
mcp_call("start_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:plan",
    "phase_name": "Verification Plan",
    "agent_name": "verification-planner"
})

# Log each user interaction (1-6 times)
mcp_call("log_question_answer", {
    "scene_id": scene_id,
    "question": "Approve verification plan?",
    "answer": "Y"  # or "modify: add more sensory details"
})

# Success
mcp_call("complete_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:setup:plan",
    "duration_seconds": 45.0,
    "artifacts": {
        "verification_plan_path": "workspace/artifacts/scene-{ID}/verification-plan.md"
    },
    "metadata": {
        "user_approved": true,
        "modification_iterations": 2
    }
})

# Cancellation
mcp_call("cancel_generation", {
    "scene_id": scene_id,
    "reason": "User rejected verification plan",
    "cancelled_by": "user"
})
```

### Outputs
- `verification-plan.md` - human-readable verification plan (approved by user)

### Dependencies
- **Requires**: `scene:gen:setup:blueprint` completed
- **Blocks on**: Human approval (critical path)

---

## STEP 4: Prose Generation (with Retry Loop)

**Step Name**: `scene:gen:draft:prose`
**Category**: Draft
**Phase Name**: "Prose Generation"
**Agents**:
- `prose-writer` (main)
- `blueprint-compliance-fast-checker` (sub-operation)

### Purpose
Генерировать литературный текст сцены с автоматическими retry при нарушении constraints.

### Process

**Initialize retry loop:**
```python
retry_count = 0
max_attempts = 3
violations_history = []
```

**Start step once:**
```python
mcp_call("start_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:draft:prose",
    "phase_name": "Prose Generation",
    "agent_name": "prose-writer"
})
```

**RETRY LOOP** (while retry_count < 3):

### Attempt 1 (retry_count = 0)
1. Launch `prose-writer` with standard prompt
2. Wait for outputs:
   - `draft-attempt1.md` (scene text)
   - `compliance-echo.json` (self-check)
3. **Sub-operation: Fast Compliance Check**
   - Launch `blueprint-compliance-fast-checker`
   - Check: draft vs constraints
   - Output: `fast-compliance-result-attempt1.json`
4. Read result:
   - **IF PASS** → Exit loop, complete step
   - **IF FAIL** → Store violations, increment retry_count, continue

### Attempt 2 (retry_count = 1)
1. Enhanced prompt:
   ```
   ⚠️⚠️⚠️ REGENERATION ATTEMPT 2 OF 3 ⚠️⚠️⚠️

   Previous violations:
   - {violation_1}
   - {violation_2}

   PAY SPECIAL ATTENTION TO: {critical_constraints}
   ```
2. Launch `prose-writer` → `draft-attempt2.md`
3. Fast compliance check
4. **IF PASS** → Exit loop
5. **IF FAIL** → Record error (severity=HIGH), increment retry_count

```python
mcp_call("record_error", {
    "scene_id": scene_id,
    "step_name": "scene:gen:draft:prose",
    "error_type": "constraint_violation",
    "error_message": f"Attempt 2 failed: {violation_summary}",
    "severity": "HIGH",
    "retry_count": 2
})
```

### Attempt 3 (retry_count = 2)
1. Maximum emphasis prompt:
   ```
   🚨🚨🚨 FINAL ATTEMPT (3/3) 🚨🚨🚨

   ABSOLUTE REQUIREMENTS (NO EXCEPTIONS):

   ❌ DO NOT USE: {forbidden_items} (repeat 5x)
   ✅ ONLY USE: {required_items} (repeat 5x)
   ```
2. Launch `prose-writer` → `draft-attempt3.md`
3. Fast compliance check
4. **IF PASS** → Exit loop (add warning flag)
5. **IF FAIL** → FAIL workflow (max retries exhausted)

```python
mcp_call("record_error", {
    "scene_id": scene_id,
    "step_name": "scene:gen:draft:prose",
    "error_type": "constraint_violation",
    "error_message": f"Attempt 3 failed: {violation_summary}",
    "severity": "CRITICAL",
    "retry_count": 3
})

mcp_call("fail_generation", {
    "scene_id": scene_id,
    "step_name": "scene:gen:draft:prose",
    "failure_reason": f"Max generation attempts reached (3/3). Persistent violations: {violations_list}",
    "final_errors": [...]
})
```

**After successful compliance:**
```python
# Rename draft
os.rename(
    f"draft-attempt{retry_count+1}.md",
    f"scene-{scene_id}-draft.md"
)

# Complete step
mcp_call("complete_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:draft:prose",
    "duration_seconds": time.time() - step_start_time,
    "artifacts": {
        "final_draft_path": f"workspace/artifacts/scene-{scene_id}/scene-{scene_id}-draft.md",
        "compliance_result_path": f"workspace/artifacts/scene-{scene_id}/fast-compliance-result-attempt{retry_count+1}.json"
    },
    "metadata": {
        "attempts_made": retry_count + 1,
        "success_on_attempt": retry_count + 1,
        "compliance_checks_performed": retry_count + 1
    }
})
```

### Outputs
- `scene-{ID}-draft.md` - final prose (passed compliance)
- `fast-compliance-result-attempt{N}.json` - compliance check results
- `compliance-echo.json` - self-check from prose-writer

### Dependencies
- **Requires**: `scene:gen:setup:plan` completed

### Notes
- Fast compliance check is **sub-operation**, NOT separate step
- No `start_step()` call for fast-checker
- Retry logic handled by coordinator

---

## STEP 5: Full Validation

**Step Name**: `scene:gen:review:validation`
**Category**: Review
**Phase Name**: "Full Validation"
**Agent**: `validation-aggregator`

### Purpose
Глубокая валидация сгенерированного текста по всем аспектам (world, canon, characters, plot, etc.)

### Process
1. Launch `validation-aggregator` agent
2. Aggregator launches **7 validators in parallel**:
   ```
   ├─ world-lorekeeper      (world consistency)
   ├─ canon-guardian        (canon compliance, levels 0-4)
   ├─ character-state       (character behavior, knowledge, emotions)
   ├─ chronicle-keeper      (timeline, numbers, chronology)
   ├─ dialogue-analyst      (dialogue quality, voice)
   ├─ plot-architect        (plot structure, pacing)
   └─ scene-structure       (scene beats, transitions)
   ```
3. Aggregator collects results
4. Aggregator creates: `final-validation-report.json`
5. Coordinator reads report
6. Count: passed, warned, failed validators
7. Store counts in metadata

### MCP Calls
```python
# Start
mcp_call("start_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:review:validation",
    "phase_name": "Full Validation",
    "agent_name": "validation-aggregator"
})

# Success (даже если есть warnings/failures)
mcp_call("complete_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:review:validation",
    "duration_seconds": 85.2,
    "artifacts": {
        "final_validation_report_path": "workspace/artifacts/scene-{ID}/final-validation-report.json"
    },
    "metadata": {
        "validators_passed": 5,
        "validators_warned": 2,
        "validators_failed": 0
    }
})
```

### Outputs
- `final-validation-report.json` - aggregated validation results

### Dependencies
- **Requires**: `scene:gen:draft:prose` completed

### Notes
- Validation **does not block** publication
- Warnings/failures are informational
- Step always completes successfully (unless validator crashes)

---

## STEP 6: Final Output

**Step Name**: `scene:gen:publish:output`
**Category**: Publish
**Phase Name**: "Final Output"
**Agent**: None (coordinator executes)

### Purpose
Финализация сцены, копирование в целевую директорию, создание summary.

### Process
1. Read validation report
2. Generate summary (2-3 sentences from draft)
3. Extract key moments
4. Calculate metrics:
   - Word count
   - Total duration (workflow start → now)
   - Retry count
   - Validation pass rate (passed/7)
5. Copy draft to final location:
   ```
   workspace/artifacts/scene-{ID}/scene-{ID}-draft.md
       →
   acts/act-{N}/chapters/chapter-{NN}/content/scene-{ID}.md
   ```
6. Create `final-summary.md` with:
   - Metrics
   - Validation status
   - Warnings (if any)
   - Path to final file
7. Show to user:
   ```
   ✅ Scene 0204 generated successfully!

   📄 File: acts/act-1/chapters/chapter-02/content/scene-0204.md
   📊 Word count: 487
   ⏱️  Duration: 6m 23s
   🔄 Attempts: 1/3
   ✅ Validation: 5/7 passed, 2 warnings

   ⚠️  Warnings:
   - dialogue-analyst: Some dialogue lacks subtext
   - scene-structure: Pacing slightly rushed in middle
   ```

### MCP Calls
```python
# Start
mcp_call("start_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:publish:output",
    "phase_name": "Final Output"
})

# Complete step
mcp_call("complete_step", {
    "scene_id": scene_id,
    "step_name": "scene:gen:publish:output",
    "duration_seconds": 3.2,
    "artifacts": {
        "final_scene_path": "acts/act-1/chapters/chapter-02/content/scene-0204.md",
        "final_summary_path": "workspace/artifacts/scene-0204/final-summary.md"
    }
})

# Complete workflow (terminal success)
mcp_call("complete_generation", {
    "scene_id": scene_id,
    "final_scene_path": "acts/act-1/chapters/chapter-02/content/scene-0204.md",
    "validation_report_path": "workspace/artifacts/scene-0204/final-validation-report.json",
    "word_count": 487,
    "total_duration_seconds": 383.5,
    "retry_count": 1
})
```

### Outputs
- `scene-{ID}.md` - final published scene (in acts/ directory)
- `final-summary.md` - metrics and summary

### Dependencies
- **Requires**: `scene:gen:review:validation` completed

---

## MCP Call Summary

### Guaranteed Calls (17 total)

| Phase | Call | Count |
|-------|------|-------|
| Resume Check | `get_generation_status()` | 1 |
| Resume | `resume_generation()` | 0-1 (conditional) |
| Initialize | `start_generation()` | 1 |
| Step Tracking | `start_step()` | 6 |
| Step Tracking | `complete_step()` | 6 |
| Terminal | `complete_generation()` OR `fail_generation()` | 1 |

**Subtotal**: 15 guaranteed

### Conditional Calls

| Event | Call | Count |
|-------|------|-------|
| User interactions (Step 3) | `log_question_answer()` | 1-6 |
| Retry errors (Step 4) | `record_error()` | 0-3 |
| Cancellation | `cancel_generation()` | 0-1 |

**Total Range**: 17-26 calls

---

## State Structure

```json
{
  "scene_id": "0204",
  "workflow_status": "IN_PROGRESS",
  "current_step": "scene:gen:draft:prose",
  "started_at": "2025-11-08T10:30:00Z",
  "initiated_by": "generation-coordinator",

  "steps": {
    "scene:gen:setup:files": {
      "status": "COMPLETED",
      "started_at": "2025-11-08T10:30:00Z",
      "completed_at": "2025-11-08T10:30:01Z",
      "duration_seconds": 0.5
    },
    "scene:gen:setup:blueprint": {
      "status": "COMPLETED",
      "started_at": "2025-11-08T10:30:01Z",
      "completed_at": "2025-11-08T10:30:18Z",
      "duration_seconds": 17.3,
      "agent_name": "blueprint-validator",
      "artifacts": {
        "validation_result_path": "workspace/artifacts/scene-0204/validation-result.json",
        "constraints_path": "workspace/artifacts/scene-0204/constraints-list.json"
      }
    },
    "scene:gen:setup:plan": {
      "status": "COMPLETED",
      "started_at": "2025-11-08T10:30:18Z",
      "completed_at": "2025-11-08T10:31:03Z",
      "duration_seconds": 45.0,
      "agent_name": "verification-planner",
      "metadata": {
        "user_approved": true,
        "modification_iterations": 2
      }
    },
    "scene:gen:draft:prose": {
      "status": "IN_PROGRESS",
      "started_at": "2025-11-08T10:31:03Z",
      "agent_name": "prose-writer",
      "metadata": {
        "current_attempt": 2,
        "max_attempts": 3
      }
    }
  },

  "errors": [
    {
      "step_name": "scene:gen:draft:prose",
      "error_type": "constraint_violation",
      "error_message": "Attempt 1 failed: location constraint violated",
      "severity": "MEDIUM",
      "retry_count": 1,
      "timestamp": "2025-11-08T10:33:45Z"
    }
  ],

  "user_questions": [
    {
      "question": "Approve verification plan?",
      "answer": "modify: add more sensory details",
      "timestamp": "2025-11-08T10:30:25Z"
    },
    {
      "question": "Approve verification plan?",
      "answer": "Y",
      "timestamp": "2025-11-08T10:31:00Z"
    }
  ]
}
```

---

## Error Handling

### Blueprint Not Found (Step 1)
```
❌ Blueprint not found: acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md

Suggestion: Run /plan-story to create blueprint first.
```

### Blueprint Invalid (Step 2)
```
❌ Blueprint validation failed:
- Missing required section: "Constraints"
- Character reference not found: "Alex" (mentioned in POV)
- Invalid constraint: location "Upper-45" does not exist in world-bible

Workflow stopped. Fix blueprint and try again.
```

### User Rejects Plan (Step 3)
```
🚫 Workflow cancelled: User rejected verification plan

State saved. Use /generation-state resume 0204 to restart with modified plan.
```

### Max Retries Exhausted (Step 4)
```
❌ Generation failed after 3 attempts

Persistent violations:
- Attempt 1: Location constraint violated (used "Upper-50" instead of "Upper-45")
- Attempt 2: Character knowledge violated (Alex knows about time manipulation before revelation)
- Attempt 3: Word count exceeded (520 words, limit 500)

Suggestion: Review blueprint constraints or retry with /generation-state resume 0204 --force
```

---

## Resume Capability

### Resume Detection (Step 0A)
Before starting new generation, check for existing state:

```python
status = mcp_call("get_generation_status", {
    "scene_id": scene_id,
    "detailed": False
})

if status["workflow_status"] == "IN_PROGRESS":
    return error("Generation already running. Use /generation-state status 0204")

if status["workflow_status"] in ["FAILED", "CANCELLED"]:
    # Show resume options
    show_resume_prompt(status)

if status["workflow_status"] == "COMPLETED":
    return error("Scene already generated. Delete or archive to regenerate.")
```

### Resume Options
```
⚠️  Found existing workflow for scene 0204 in state: FAILED

Last updated: 2025-11-08 10:35:00
Completed: 3/6 steps
Failed at: scene:gen:draft:prose

Options:
1. RESUME - Continue from checkpoint (saves ~2 minutes)
2. FRESH - Archive old state and start new generation

What would you like to do? [resume/fresh]
```

### Resume Execution
```python
resume_response = mcp_call("resume_generation", {
    "scene_id": scene_id,
    "force": False
})

restart_step = resume_response["restart_step"]  # e.g., "scene:gen:draft:prose"

# Jump to restart_step, skip completed steps
```

---

## Dependencies with Other Workflows

### Scene Planning → Scene Generation
```
scene:plan:blueprint (completed)
    ↓
scene:gen:setup:files (checks blueprint exists)
```

### Chapter Planning → Scene Planning
```
chapter:scenes (completed)
    ↓
scene:plan:context (scene must be in chapter plan)
```

### Act Planning → Chapter Planning
```
act:structure (completed)
    ↓
chapter:context (chapter must be in act structure)
```

---

## Performance Targets

| Step | Target Duration | Actual (typical) |
|------|-----------------|------------------|
| scene:gen:setup:files | <2s | ~1s |
| scene:gen:setup:blueprint | <30s | 15-20s |
| scene:gen:setup:plan | <1min | 20-45s (+ ~30s human) |
| scene:gen:draft:prose | 3-5min | 3-4min (1 attempt), 8-12min (3 attempts) |
| scene:gen:review:validation | 1-2min | 1-1.5min |
| scene:gen:publish:output | <10s | 3-5s |

**Total**: 5-8 minutes (happy path) | 10-15 minutes (worst case with 3 retries)

---

## Next Steps

1. **Review this document** - confirm workflow is correct
2. **Plan refactoring** - identify all files to change
3. **Implement changes**:
   - MCP server (Pydantic models, state structure)
   - generation-coordinator.md (all MCP calls)
   - Tests (6 files)
   - Helpers (constants, validators)
4. **Migration** - handle existing state files (if any)
5. **Documentation** - update FEAT-0003, README, etc.

---

**Status**: Ready for review and approval before refactoring
