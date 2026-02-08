# Generation Workflow

Создание литературного текста из blueprint с валидацией и retry-логикой.

---

## Overview

Generation Workflow создаёт готовый литературный текст на основе blueprint. Многоступенчатая валидация гарантирует соблюдение требований. Автор утверждает план ПЕРЕД генерацией.

**Orchestrator**: `generation-coordinator` agent

---

## 7-Step Flow

### Step 0: Parse & Initialize
- Extract scene_id from user request
- Check for existing workflows (resume/fresh)
- Create workflow state in `workspace/workflow-state/`

### Step 1: File Check
- Verify blueprint exists at `acts/act-{N}/chapters/chapter-{NN}/scenes/scene-{ID}-blueprint.md`
- If missing → error, suggest `/plan-scene`

### Step 2: Blueprint Validation
- **Agent**: `blueprint-validator`
- Extracts constraints from blueprint
- Output: `constraints-list.json` or `validation-errors.json`
- If errors → show to user, STOP

### Step 3: Verification Plan (HUMAN APPROVAL)
- **Agent**: `verification-planner`
- Transforms constraints into human-readable plan
- **WAIT for user approval** before proceeding
- User can request modifications (max 5 iterations)

### Step 4: Generation + Fast Check (Retry Loop)
- **Agents**: `prose-writer` + `blueprint-compliance-fast-checker`
- Up to 3 attempts:
  - Attempt 1: Standard prompt
  - Attempt 2: Enhanced prompt with violation warnings
  - Attempt 3: Maximum emphasis, ALL CAPS on violations
- Each attempt → fast compliance check (<30 sec)
- If pass → continue. If fail after 3 → failure report, STOP

### Step 5: (Embedded in Step 4)
Fast compliance check runs inside Step 4 retry loop.

### Step 6: Full Validation
- **Agent**: `validation-aggregator`
- Performs 7 checks in one pass:
  1. World consistency (vs world bible)
  2. Canon compliance (levels 0-4)
  3. Character state (knowledge, emotions, capabilities)
  4. Timeline & continuity
  5. Dialogue quality (voice, subtext)
  6. Plot structure (cause-effect, purpose)
  7. Scene structure (beats, pacing, hooks)
- Output: `final-validation-report.json`

### Step 7: Final Output
- Copy draft to `acts/.../content/scene-{ID}.md`
- Generate summary, key moments, metrics
- Return metadata to user (NOT full text)

---

## Agents

| Agent | Step | Purpose |
|-------|------|---------|
| generation-coordinator | All | Orchestration, retries, state |
| blueprint-validator | 2 | Extract & validate constraints |
| verification-planner | 3 | Human-readable plan |
| prose-writer | 4 | Text generation |
| blueprint-compliance-fast-checker | 4 | Fast constraint check (<30s) |
| validation-aggregator | 6 | Full 7-check validation |

---

## Retry Logic

```
Attempt 1: Standard prompt → fast check
  PASS → continue to Step 6
  FAIL → collect violations

Attempt 2: Enhanced prompt (violations highlighted) → fast check
  PASS → continue to Step 6
  FAIL → collect violations

Attempt 3: Maximum emphasis (ALL CAPS, 5x repeat) → fast check
  PASS → continue to Step 6 (with warning flag)
  FAIL → failure report, STOP
```

---

## Error Handling

| Error | Action |
|-------|--------|
| Blueprint not found | Suggest `/plan-scene` |
| Blueprint validation fails | Show errors, STOP |
| User rejects plan | Cancel workflow |
| 3 failed attempts | Save drafts, failure report |
| Generation timeout (>6 min) | Return partial state |
| MCP unavailable | Log warning, continue |

---

## File Locations

```
Input:  acts/.../scenes/scene-{ID}-blueprint.md
Output: acts/.../content/scene-{ID}.md
State:  workspace/workflow-state/{workflow_id}.json
Drafts: workspace/artifacts/scene-{ID}/
Logs:   workspace/logs/generation-coordinator/
```

---

## Timing (approximate)

| Step | Time |
|------|------|
| Validation (Step 2) | <30 sec |
| Verification plan (Step 3) | <15 sec |
| Generation + fast check (Step 4) | 3-5 min |
| Full validation (Step 6) | 1-2 min |
| **Total** | **5-8 min** |
