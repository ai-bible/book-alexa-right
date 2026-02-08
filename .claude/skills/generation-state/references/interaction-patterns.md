# Generation State Interaction Patterns

## Pattern 1: Happy Path Generation

```
User: "Generate scene 0204"
→ generation-coordinator starts workflow
→ State auto-tracked via MCP
→ Workflow runs Steps 1-7

User: /generation-state status 0204
→ Shows "Step 4/7, Attempt 2/3, 3m 15s elapsed"

(workflow completes)

User: /generation-state status 0204
→ Shows "COMPLETED, 7/7, 7m 42s total"
```

## Pattern 2: Recovery from Failure

```
User: /generation-state list --failed
→ Shows scene 0202 failed at Step 4

User: /generation-state status 0202
→ Shows error details: "Max attempts reached (3/3) - location constraint violated"

User fixes blueprint

User: /generation-state resume 0202
→ Recovery plan shown:
  - Steps 1-3: SKIP (already completed, ~52s saved)
  - Step 4: RESUME (reset attempts, re-read blueprint)
  - Steps 5-7: PENDING

→ "Proceed with resume?"

User: yes
→ generation-coordinator continues from Step 4
```

## Pattern 3: Monitoring Active Generation

```
User: /generation-state status 0204
→ "Step 4/7, Attempt 2/3, 3m 15s elapsed"

User waits 2 minutes

User: /generation-state status 0204
→ "Step 5/7, Fast Compliance Check, 5m 42s elapsed"
```

## Pattern 4: Cancellation

```
User realizes blueprint has error mid-generation

User: /generation-state cancel 0204
→ State saved with CANCELLED status
→ Shows work completed before cancellation:
  - Step 1: File System Check (1s)
  - Step 2: Blueprint Validation (19s)
  - Step 3: Verification Plan (12s)
  - Step 4: Prose Generation (2m 15s, INTERRUPTED)

User fixes blueprint

User: /generation-state resume 0204
→ Workflow restarts from last completed step
```

## Pattern 5: List and Triage

```
User: /generation-state list
→ Table of all generations:

  Scene  | Status       | Step | Started     | Duration
  0204   | IN_PROGRESS  | 4/7  | 14:30 (6m)  | 6m 15s
  0203   | COMPLETED    | 7/7  | 11:22 (3h)  | 7m 42s
  0202   | FAILED       | 4/7  | Yesterday   | 11m 05s
  0201   | COMPLETED    | 7/7  | 2025-11-01  | 6m 33s
  0105   | CANCELLED    | 2/7  | 2025-10-31  | 0m 22s

User: /generation-state list --failed
→ Only shows scene 0202 (FAILED)

Quick actions:
   - Check details: /generation-state status 0202
   - Resume: /generation-state resume 0202
```

## Example Output: Detailed Status

```markdown
GENERATION STATUS: Scene 0204

Session ID: 2025-11-03-143045-scene-0204
Started: 2025-11-03T14:30:45Z (6 minutes ago)

Progress: Step 4/7 (IN_PROGRESS)
Current Phase: Generation

Detailed Progress:

  [done] File System Check (COMPLETED) - 1s
  [done] Blueprint Validation (COMPLETED) - 19s
  [done] Verification Plan (COMPLETED) - 12s
  [running] Prose Generation (IN_PROGRESS) - 3m 15s
  [pending] Fast Compliance Check (PENDING)
  [pending] Full Validation (PENDING)
  [pending] Final Output (PENDING)

Generation Attempts: 2/3

Artifacts:
- blueprint_path: acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md
- constraints_list_path: workspace/artifacts/scene-0204-constraints.json
- draft_path: workspace/artifacts/scene-0204-draft.md
```

## Example Output: Resume Plan

```markdown
RESUMING GENERATION: Scene 0204

Loading state: workspace/generation-state-0204.json

State loaded:
  - Session ID: 2025-11-03-143045-scene-0204
  - Failed at: Step 4 (Prose Generation)
  - Reason: Max attempts reached (3/3) - location constraint violated

Recovery Plan:

  [skip] Step 1: File System Check (already completed, 1s)
  [skip] Step 2: Blueprint Validation (already completed, 19s)
  [skip] Step 3: Verification Plan (already completed, user approved)
  [resume] Step 4: Prose Generation (RESUME)
     → Will reset attempts counter
     → Will re-read blueprint (may have been fixed)
  [pending] Step 5: Fast Compliance Check
  [pending] Step 6: Full Validation
  [pending] Step 7: Final Output

Time saved: ~52 seconds (Steps 1-3 already completed)

Proceed with resume?
```
