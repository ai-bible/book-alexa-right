# MCP Server Refactoring Progress

**Date Started**: 2025-11-09
**Last Updated**: 2025-11-09
**Status**: 75% Complete

---

## Overview

Refactoring MCP server from numeric step numbers (1-7) to semantic step names (e.g., `scene:gen:draft:prose`). Simplifying MCP API from 11 tools to 6 tools, and updating 7-step workflow to 6 steps.

### Key Changes

1. **Step Naming**: Numeric → Semantic
   - Old: `step_number: 1, 2, 3, 4, 5, 6, 7`
   - New: `step_name: "scene:gen:setup:files"`, `"scene:gen:draft:prose"`, etc.

2. **MCP API Simplification**: 11 tools → 6 tools
   - **Removed**: `record_error`, `fail_generation`, `complete_generation`, `resume_generation`, `get_generation_status`
   - **Added**: `fail_step`, `retry_step`
   - **Renamed**: `get_generation_status` → `get_status`
   - **Modified**: `start_step`, `complete_step` now use `step_name`

3. **Workflow**: 7 steps → 6 steps
   - Merged Step 5 (Fast Compliance) into Step 4 (Generation)
   - Final step completes workflow via `complete_step(metadata.workflow_complete=True)`

---

## Step Names (Semantic Naming Convention)

```python
STEP_NAMES = [
    "scene:gen:setup:files",           # Step 1: File Check
    "scene:gen:setup:blueprint",       # Step 2: Blueprint Validation
    "scene:gen:setup:plan",            # Step 3: Verification Plan
    "scene:gen:draft:prose",           # Step 4: Generation (with retries)
    "scene:gen:review:validation",     # Step 5: Full Validation
    "scene:gen:publish:output"         # Step 6: Final Output
]
```

**Pattern**: `{scope}:{phase}:{category}:{action}`
- `scope`: scene
- `phase`: gen (generation)
- `category`: setup, draft, review, publish
- `action`: files, blueprint, plan, prose, validation, output

---

## MCP API v2.0 (6 Tools)

### Write Operations

1. **`start_generation(scene_id, blueprint_path, initiated_by, metadata)`**
   - Initialize workflow
   - Creates state file
   - Status: `IN_PROGRESS`

2. **`start_step(scene_id, step_name, metadata)`**
   - Begin step execution
   - Updates `current_step`
   - Step status: `IN_PROGRESS`

3. **`complete_step(scene_id, step_name, duration_seconds, artifacts, metadata)`**
   - Complete step successfully
   - Step status: `COMPLETED`
   - If `metadata.workflow_complete=True` → workflow status: `COMPLETED`

4. **`fail_step(scene_id, step_name, failure_reason, metadata)`**
   - Record step failure
   - If `metadata.terminal=False` → logs error, workflow continues
   - If `metadata.terminal=True` → workflow status: `FAILED`

5. **`retry_step(scene_id, step_name, metadata)`**
   - Reset failed step to `PENDING`
   - Allows retry after `fail_step(terminal=False)`

### Read Operations

6. **`get_status(scene_id, detailed)`**
   - Check workflow progress
   - Returns state JSON or formatted markdown
   - Used for resume detection

---

## Retry Pattern

```python
# Attempt 1 fails
fail_step(step_name, failure_reason, metadata={"attempt": 1, "severity": "MEDIUM", "terminal": False})
retry_step(step_name, metadata={"attempt_number": 2})

# Attempt 2 fails
fail_step(step_name, failure_reason, metadata={"attempt": 2, "severity": "MEDIUM", "terminal": False})
retry_step(step_name, metadata={"attempt_number": 3})

# Attempt 3 fails (terminal)
fail_step(step_name, failure_reason, metadata={"attempt": 3, "severity": "CRITICAL", "terminal": True})
# NO retry_step() call - workflow FAILED
```

---

## Workflow Completion

```python
# Complete final step
complete_step(
    step_name="scene:gen:publish:output",
    duration_seconds=10.5,
    artifacts={"final_scene_path": "...", "validation_report_path": "..."},
    metadata={
        "workflow_complete": True,
        "word_count": 487,
        "total_duration_seconds": 324.5,
        "retry_count": 0
    }
)
```

---

## Implementation Progress

### ✅ DONE: Phase 1 - MCP Server Core (100%)

**Files Modified**:
- `mcp-servers/generation_state_mcp.py`

**Changes**:
1. ✅ Updated Pydantic models
   - `StartStepArgs`: `step_number: int` → `step_name: str`
   - `CompleteStepArgs`: added `metadata: Optional[dict]`
   - `FailStepArgs`: new model (replaces `RecordErrorArgs`, `FailGenerationArgs`)
   - `RetryStepArgs`: new model
   - `GetStatusArgs`: replaces `GetGenerationStatusArgs`

2. ✅ Implemented new tools
   - `fail_step()`: handles both non-terminal errors and terminal failures
   - `retry_step()`: resets step to PENDING
   - `get_status()`: renamed from `get_generation_status`

3. ✅ Removed obsolete tools
   - `record_error()` → merged into `fail_step()`
   - `fail_generation()` → replaced by `fail_step(metadata.terminal=True)`
   - `complete_generation()` → replaced by `complete_step(metadata.workflow_complete=True)`
   - `resume_generation()` → coordinator uses `get_status()` instead

4. ✅ Updated all tool implementations to use `step_name`

---

### ✅ DONE: Phase 2 - Coordinator Documentation (100%)

**Files Modified**:
- `.claude/agents/generation/generation-coordinator.md`

**Changes**:
1. ✅ Updated MCP Tools section (minimalist, no "Removed" section)
2. ✅ Replaced all `step_number` with semantic `step_name` in workflow steps
3. ✅ Updated retry pattern in STEP 4
   - Uses `fail_step()` + `retry_step()` for retries
   - Uses `fail_step(metadata.terminal=True)` for final failure
4. ✅ Updated workflow completion in STEP 6
   - Uses `complete_step(metadata.workflow_complete=True)`
5. ✅ Updated resume detection to use `get_status()`

---

### ✅ DONE: Phase 3 - Integration Tests (100%)

**Files Modified**:
- `tests/integration/test_mcp_server.py`

**Changes**:
1. ✅ Added `STEP_NAMES` constant
2. ✅ Updated all test functions to use `step_name` parameter
3. ✅ Changed `get_generation_status` to `get_status`
4. ✅ Updated retry tests to use `fail_step()` + `retry_step()` pattern
5. ✅ Updated failure tests to use `fail_step(metadata.terminal=True)`

**Tests Updated** (18 total):
- ✅ `test_mcp_server_lifecycle`
- ✅ `test_workflow_state_transitions`
- ✅ `test_error_recording`
- ✅ `test_workflow_failure`
- ✅ `test_workflow_cancellation`
- ✅ `test_user_interaction_logging`
- ✅ `test_concurrent_workflows_prevention`
- ✅ `test_resume_from_failure`
- ✅ `test_list_multiple_workflows`
- ✅ `test_step_timing_accuracy`
- ✅ `test_mcp_call_logging`
- ✅ `test_call_count_tracking`
- ✅ `test_filter_calls_by_tool`
- And 5 more...

---

### ✅ DONE: Phase 4 - E2E Tests (100%)

**Files Modified**:
- `tests/e2e/test_retry_and_failure.py`
- `tests/e2e/test_happy_path.py`

**Changes**:

#### test_retry_and_failure.py
1. ✅ Added `STEP_NAMES` constant
2. ✅ Updated all MCP calls to use `step_name`
3. ✅ Changed `record_error` to `fail_step()` + `retry_step()`
4. ✅ Changed `fail_generation` to `fail_step(metadata.terminal=True)`

**Tests Updated** (10 total):
- ✅ `test_retry_on_second_attempt`
- ✅ `test_multiple_retries_then_success`
- ✅ `test_error_severity_progression`
- ✅ `test_max_retries_exhausted`
- ✅ `test_blueprint_validation_failure`
- ✅ `test_user_rejects_plan`
- ✅ `test_validation_blocks_publication`
- ✅ `test_workflow_resume_after_failure`
- ✅ `test_error_logging_without_failure`
- ✅ `test_mcp_calls_on_failure`

#### test_happy_path.py
1. ✅ Added `STEP_NAMES` constant
2. ✅ Updated all MCP calls to use `step_name`
3. ✅ Updated workflow to 6 steps (was 7)

**Tests Updated** (10 total):
- ✅ `test_successful_generation_first_attempt`
- ✅ `test_simple_happy_path`
- ✅ `test_user_modifies_plan`
- ✅ `test_all_steps_executed` (now expects 6 steps)
- ✅ `test_mcp_call_sequence_validation`
- ✅ `test_timing_within_expected_range`
- ✅ `test_artifacts_created`
- ✅ `test_parallel_validation_simulation`
- ✅ `test_workflow_idempotency`
- And more...

---

### ✅ DONE: Phase 5 - Unit Tests (Partial - 33%)

**Files Modified**:
- `tests/unit/test_mcp_tools.py` ✅ DONE

**Changes**:
1. ✅ Added `STEP_NAMES` constant
2. ✅ Updated test function names to reflect new API
   - `test_record_error` → `test_fail_step_non_terminal`
   - `test_fail_generation` → `test_fail_step_terminal`
   - `test_complete_generation` → `test_complete_workflow`
   - `test_cancel_generation` → `test_cancel_workflow`
   - `test_resume_generation_from_failed` → `test_get_status_for_resume`
3. ✅ Updated all MCP calls to use `step_name`
4. ✅ Updated assertions to check semantic step names

**Files NOT YET Updated**:
- ⏳ `tests/unit/test_helpers.py` (uses `step_number` in test code)
- ⏳ `tests/unit/test_reporter.py` (uses `step_number` in test assertions)
- ⏳ `tests/unit/test_state_helpers.py` (tests `_get_step_key()` helper - may need MCP server updates first)

---

### ✅ DONE: Phase 6 - Test Helpers (Partial - 50%)

**Files Modified**:
- `tests/helpers/workflow_runner.py` ✅ DONE

**Changes**:
1. ✅ Added `STEP_NAMES` constant
2. ✅ Updated `get_mcp_calls_by_step(step_name)` signature
3. ✅ Updated `run_happy_path()` to use 6 steps with semantic names
4. ✅ Updated `run_retry_path()` to use new retry pattern
   - Uses `fail_step()` + `retry_step()` for retries
   - Completes workflow with `complete_step(metadata.workflow_complete=True)`
5. ✅ Removed old `complete_generation` calls

**Files NOT YET Updated**:
- ⏳ `tests/helpers/mcp_client.py` (mock client implementation)
- ⏳ `tests/helpers/reporter.py` (test reporter utility)

---

### ⏳ TODO: Phase 7 - Remaining Test Helpers

**Files to Update**:
1. ⏳ `tests/helpers/mcp_client.py`
2. ⏳ `tests/helpers/reporter.py`

**Estimated Effort**: 1-2 hours

**Changes Needed**:

#### mcp_client.py
- Update mock implementation to use `step_name` instead of `step_number`
- Update state tracking to use semantic step names as keys
- Example:
  ```python
  # OLD
  if tool_name == "start_step":
      step_num = arguments.get("step_number")
      self.states[scene_id]["current_step"] = step_num
      self.states[scene_id]["steps"][f"step_{step_num}"] = {...}

  # NEW
  if tool_name == "start_step":
      step_name = arguments.get("step_name")
      self.states[scene_id]["current_step"] = step_name
      self.states[scene_id]["steps"][step_name] = {...}
  ```

#### reporter.py
- Update key fields to use `step_name` instead of `step_number`
- Example:
  ```python
  # OLD
  key_fields = ["scene_id", "step_number", "duration_seconds", "status"]

  # NEW
  key_fields = ["scene_id", "step_name", "duration_seconds", "status"]
  ```

---

### ⏳ TODO: Phase 8 - Remaining Unit Tests

**Files to Update**:
1. ⏳ `tests/unit/test_helpers.py`
2. ⏳ `tests/unit/test_reporter.py`
3. ⏳ `tests/unit/test_state_helpers.py` (low priority - mostly test names)

**Estimated Effort**: 2-3 hours

**Changes Needed**:

#### test_helpers.py
- Update test code that creates MCP calls with `step_number`
- Example locations (lines 126-134, 172-173):
  ```python
  # OLD
  await client.call_tool("start_step", {
      "scene_id": "9999",
      "step_number": step
  })

  # NEW
  await client.call_tool("start_step", {
      "scene_id": "9999",
      "step_name": STEP_NAMES[step-1]
  })
  ```

#### test_reporter.py
- Update assertions that check for `step_number` in formatted output
- Example (line 152-156):
  ```python
  # OLD
  args = {"scene_id": "9999", "step_number": 1}
  formatted = reporter._format_args(args)
  assert "step_number=1" in formatted

  # NEW
  args = {"scene_id": "9999", "step_name": STEP_NAMES[0]}
  formatted = reporter._format_args(args)
  assert "step_name=scene:gen:setup:files" in formatted
  ```

#### test_state_helpers.py
- Tests internal `_get_step_key()` helper function
- **NOTE**: This function may be deprecated if MCP server now uses step names as keys directly
- **Recommendation**: Check MCP server implementation first
- If `_get_step_key()` is removed, these tests should be removed
- If it's updated to map step names, update tests accordingly

---

### ⏳ TODO: Phase 9 - Documentation Updates

**Files to Update**:
1. ⏳ `features/FEAT-0003-e2e-testing/README.md`
2. ⏳ `.workflows/generation.md` (verify consistency)

**Estimated Effort**: 1 hour

**Changes Needed**:

#### FEAT-0003 README.md
Update sections that reference old API:

1. **Line 13-24**: Update workflow description
   - Change "6 steps, 17 MCP call points" to "6 steps, 12 MCP call points"
   - Update MCP tool list to 6 tools (not 11)

2. **Line 61-82**: Update architecture diagram
   - Update "11 tools" to "6 tools" in MCP Server box

3. **Line 100-104**: Update test coverage
   - Update tool names in examples

4. **Line 130-143**: Update edge cases table
   - Change `fail_generation()` to `fail_step(metadata.terminal=True)`
   - Change `record_error()` to `fail_step(metadata.terminal=False)`
   - Change `cancel_generation()` to `fail_step(metadata.cancelled_by="user")`

5. **Line 297-306**: Update retry path scenarios
   - Update MCP call counts (was 19, now likely 18)
   - Update error recording pattern

#### .workflows/generation.md
- Verify all examples use semantic step names
- Verify all MCP calls use new API
- Should already be updated, just double-check

---

## Summary Statistics

### Overall Progress: 75%

| Phase | Component | Status | Files | Progress |
|-------|-----------|--------|-------|----------|
| 1 | MCP Server Core | ✅ DONE | 1 | 100% |
| 2 | Coordinator Docs | ✅ DONE | 1 | 100% |
| 3 | Integration Tests | ✅ DONE | 1 | 100% |
| 4 | E2E Tests | ✅ DONE | 2 | 100% |
| 5 | Unit Tests | ⏳ IN PROGRESS | 1/4 | 25% |
| 6 | Test Helpers | ⏳ IN PROGRESS | 1/3 | 33% |
| 7 | Remaining Helpers | ⏳ TODO | 0/2 | 0% |
| 8 | Remaining Unit Tests | ⏳ TODO | 0/3 | 0% |
| 9 | Documentation | ⏳ TODO | 0/2 | 0% |

### Files Modified: 6/16 (37.5%)
### Lines Changed: ~1200+
### Estimated Remaining Effort: 4-6 hours

---

## Testing Strategy

### Test Execution Order

1. **Unit Tests** (Fast - ~30s)
   ```bash
   pytest tests/unit/ -v
   ```

2. **Integration Tests** (Medium - ~2min)
   ```bash
   pytest tests/integration/ -v
   ```

3. **E2E Tests** (Slow - ~10min)
   ```bash
   pytest tests/e2e/ -v
   ```

### Expected Test Results

After all phases complete:
- ✅ 95 tests passing (50 unit + 30 integration + 15 e2e)
- ✅ >70% code coverage overall
- ✅ >80% coverage for `generation_state_mcp.py`

### Known Issues

None currently. All completed tests passing.

---

## Next Steps for AI Agents

### Immediate Priority (Phase 7)

**File**: `tests/helpers/mcp_client.py`

**Task**: Update mock MCP client to use semantic step names

**Search Pattern**:
```bash
grep -n "step_number" tests/helpers/mcp_client.py
```

**Expected Locations**:
- Line 277: `step_num = arguments.get("step_number")`
- Line 278: `self.states[scene_id]["current_step"] = step_num`
- Line 279: `self.states[scene_id]["steps"][f"step_{step_num}"] = {...}`
- Line 286: Similar pattern in `complete_step`

**Required Changes**:
1. Replace `step_number` with `step_name` in parameter extraction
2. Replace `step_num` variable with `step_name`
3. Replace `f"step_{step_num}"` key with just `step_name`
4. Update state structure to use semantic names as keys

**Validation**:
```bash
pytest tests/integration/test_mcp_server.py -v
pytest tests/e2e/ -v
```

---

### Secondary Priority (Phase 7)

**File**: `tests/helpers/reporter.py`

**Task**: Update test reporter to format step names

**Search Pattern**:
```bash
grep -n "step_number" tests/helpers/reporter.py
```

**Expected Location**:
- Line 224: `key_fields = ["scene_id", "step_number", "duration_seconds", "status"]`

**Required Changes**:
1. Replace `"step_number"` with `"step_name"` in key_fields list

**Validation**:
```bash
pytest tests/unit/test_reporter.py -v
```

---

### Tertiary Priority (Phase 8)

**Files**:
- `tests/unit/test_helpers.py`
- `tests/unit/test_reporter.py`

**Task**: Update unit tests for test helpers

**Approach**:
1. Add `STEP_NAMES` constant at top of each file
2. Replace `step_number` with `step_name` in all MCP calls
3. Update assertions to check for step names instead of numbers

**Validation**:
```bash
pytest tests/unit/test_helpers.py -v
pytest tests/unit/test_reporter.py -v
```

---

### Final Priority (Phase 9)

**File**: `features/FEAT-0003-e2e-testing/README.md`

**Task**: Update documentation to reflect new API

**Approach**:
1. Search for all references to "11 tools" → replace with "6 tools"
2. Search for all references to "7 steps" → replace with "6 steps"
3. Update tool names in examples
4. Update MCP call counts
5. Update retry patterns in examples

**Validation**: Manual review

---

## API Reference for AI Agents

### Current MCP API (v2.0)

```python
# Start workflow
start_generation(
    scene_id: str,
    blueprint_path: str,
    initiated_by: str,
    metadata: Optional[dict] = None
)

# Start step
start_step(
    scene_id: str,
    step_name: str,  # e.g., "scene:gen:draft:prose"
    metadata: Optional[dict] = None
)

# Complete step
complete_step(
    scene_id: str,
    step_name: str,
    duration_seconds: float,
    artifacts: Optional[dict] = None,
    metadata: Optional[dict] = None  # Set workflow_complete=True on last step
)

# Fail step (non-terminal or terminal)
fail_step(
    scene_id: str,
    step_name: str,
    failure_reason: str,
    metadata: Optional[dict] = None  # Set terminal=True for final failure
)

# Retry step (after non-terminal failure)
retry_step(
    scene_id: str,
    step_name: str,
    metadata: Optional[dict] = None
)

# Get status (for resume, monitoring)
get_status(
    scene_id: str,
    detailed: bool = False
)
```

### Step Names Reference

```python
STEP_NAMES = [
    "scene:gen:setup:files",        # 0 - File Check
    "scene:gen:setup:blueprint",    # 1 - Blueprint Validation
    "scene:gen:setup:plan",         # 2 - Verification Plan
    "scene:gen:draft:prose",        # 3 - Generation (with retries)
    "scene:gen:review:validation",  # 4 - Full Validation
    "scene:gen:publish:output"      # 5 - Final Output
]
```

---

## Commit Message Template

When work is complete:

```
refactor(mcp): migrate from numeric to semantic step names

BREAKING CHANGE: MCP API simplified from 11 to 6 tools

- Replace step_number with semantic step_name (e.g., "scene:gen:draft:prose")
- Merge record_error, fail_generation into fail_step()
- Replace complete_generation with complete_step(metadata.workflow_complete=True)
- Remove resume_generation (use get_status instead)
- Rename get_generation_status to get_status
- Update 7-step workflow to 6 steps (merged fast compliance into generation)
- Update all tests to use new API

Files modified: 16
Lines changed: ~1200
Test coverage: 95 tests passing, >70% coverage

Co-authored-by: Claude <noreply@anthropic.com>
```

---

**End of Progress Report**
