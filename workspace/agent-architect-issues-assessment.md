# Agent-Architect Issues Assessment

## Issue Analysis: Are They Mitigated by Agents in Loop?

### ❌ CRITICAL: Step 5 State Machine Conflict (Lines 475-590)

**Problem**: Step 5 executes INSIDE Step 4 retry loop
- Step 5 completes multiple times (once per retry attempt)
- State shows: Step 5 → Step 4 → Step 5 (backwards progression)
- Resume breaks (which Step 5 to resume from?)

**Mitigated by agents?**: **NO**
- This is architectural workflow design issue
- Agents cannot fix state machine semantics
- Coordinator must be refactored

**Fix required**: Merge Step 5 into Step 4 as sub-operation, not separate step

---

### ❌ HIGH: Missing TTL Enforcement

**Problem**: No timeout enforcement for long-running steps
- Documentation mentions "Generation timeout (>6 minutes)" (line search result)
- No actual enforcement mechanism in code
- Workflow could hang indefinitely

**Mitigated by agents?**: **NO**
- Individual agents have their own timeouts (Claude Code's agent system)
- But coordinator doesn't enforce workflow-level TTL
- If agent hangs, coordinator waits forever

**Fix required**: Add timeout checks after each agent invocation:
```python
start_time = time.time()
result = await agent.run(...)
if time.time() - start_time > MAX_STEP_DURATION:
    fail_generation(reason="Step timeout exceeded")
```

---

### ❌ HIGH: Resume Lacks Idempotency Checks (Lines 127-136)

**Problem**: Resume doesn't validate artifacts from completed steps still exist
- Just calls `resume_generation()` and jumps to step number
- If artifacts deleted (e.g., verification plan from Step 3), resume breaks

**Mitigated by agents?**: **NO**
- Individual agents don't know about resume state
- Coordinator is responsible for validating resume prerequisites
- No agent in loop validates "can we actually resume from step N?"

**Fix required**: Before resume, validate artifacts:
```python
resume_response = mcp_call("resume_generation", ...)
restart_step = resume_response["restart_step"]

# Validate artifacts for all completed steps
for step in range(1, restart_step):
    artifacts = get_expected_artifacts(step)
    for artifact_path in artifacts:
        if not Path(artifact_path).exists():
            return error("Cannot resume: missing artifact {artifact_path}")
```

---

### ⚠️ MEDIUM: Other Issues

**4. Step 3 Modification Persistence**
- User modifications to plan may not be logged
- **Partially mitigated**: `log_question_answer()` captures Q&A, but not structured modifications
- **Fix**: Explicit `metadata` field in Step 3 completion

**5. Step 6 Doesn't Check Step 5 Result**
- Jumps straight to validation without confirming Step 5 passed
- **Mitigated by workflow logic**: Step 5 must pass to exit Step 4 loop
- **No fix needed** (implicit dependency)

**6. Error Recovery Assumes Step 4 is Problem**
- All errors routed to "retry Step 4"
- **Partially mitigated**: Coordinator can fail at Steps 2, 4, 6 explicitly
- **Acceptable** (Step 4 is main failure point)

---

## Summary

**3/6 issues require explicit fixes** (all HIGH/CRITICAL):
1. Step 5 state machine → Refactor workflow
2. TTL enforcement → Add timeout checks
3. Resume idempotency → Validate artifacts before resume

**0/3 are mitigated by agents in loop** - all need coordinator changes

**3/6 issues are acceptable** (MEDIUM or already handled):
1. Modification persistence → Add metadata field (minor enhancement)
2. Step 6 dependency → Already handled by workflow logic
3. Error recovery scope → Acceptable design choice
