# Generation Workflow

**Version**: 3.0 (FEAT-0001 Integrated)
**Last Updated**: 2025
**Related Documents**:
- [Planning Workflow](planning.md)
- [Integration Guide](integration.md)
- [Agents Reference](agents-reference.md)
- [Prose Style Guide](prose-style-guide.md)
- [FEAT-0001 Technical Design](../features/FEAT-0001-reliable-scene-generation/)

---

## Overview

Generation Workflow создаёт готовый литературный текст на основе детального blueprint с гарантированным соблюдением всех критических требований (локации, персонажи, механики мира, scope).

### Core Improvements (FEAT-0001)

**Problem Solved:**
- ❌ **БЫЛО**: ИИ систематически нарушал blueprint (неправильные локации, удалённые персонажи, изменённые механики)
- ✅ **СТАЛО**: Многоступенчатая валидация с автоматической регенерацией при ошибках

**Key Features:**
- **Автор в контроле**: Blueprint = единственный источник сюжетных решений
- **Verification Plan**: Человек утверждает план ПЕРЕД генерацией (прозрачность)
- **Fast-Fail Validation**: Ошибки ловятся за <30 сек, автоматическая регенерация
- **Constraint Compliance**: >95% успех с первой попытки (vs. ~60% раньше)

### Principles

- **Blueprint as Single Source of Truth**: ИИ НЕ добавляет сюжетные решения
- **Human-in-the-Loop**: Verification plan требует человеческого одобрения
- **Fail-Fast**: Ранняя валидация предотвращает дорогие ошибки
- **Artifact System**: Агенты передают file paths, не данные (>100 строк)
- **Isolated Contexts**: Каждый агент получает ТОЛЬКО необходимые файлы
- **Observability**: Все шаги логируются для отладки

---

## When to Use Generation Workflow

### Scenario 1: Generate Scene from Blueprint

**When:**
- Blueprint уже создан (через `/plan-scene` или вручную)
- Файл `acts/act-N/chapters/chapter-NN/scenes/scene-NNNN-blueprint.md` существует

**Trigger:**
```
User: "Сгенерируй сцену 0204"
User: "Generate scene 0204"
```

**Flow:** Starts from **Step 1** (File Check), uses full 7-step FEAT-0001 workflow

### Scenario 2: Attempt Generation Without Blueprint

**When:**
- User requests generation but blueprint doesn't exist

**Behavior:**
```
❌ ERROR: Blueprint not found

File `acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md` does not exist.

Generation without blueprint is prohibited (plot control).

ACTIONS:
1. Create blueprint: /plan-scene 0204
2. Use existing blueprint from another location
3. Cancel generation

What do you want to do?
```

**Result:** User maintains control over plot decisions

---

## 7-Step Generation Workflow (FEAT-0001)

### Architecture Overview

```
USER: "Generate scene 0204"
    ↓
┌─────────────────────────────────────────────────┐
│ ORCHESTRATOR: generation-coordinator            │
│ Manages 7-step process, retry logic, state     │
└─────────────────────────────────────────────────┘
    ↓
[STEP 1: File Check] → Blueprint exists?
    ↓ YES
[STEP 2: Blueprint Validation] → blueprint-validator (AUTO)
    ↓ PASS → constraints-list.json
[STEP 3: Verification Plan] → verification-planner (INTERACTIVE)
    ↓ User reviews plan → APPROVED
[STEP 4: Generation] → prose-writer (AUTO, up to 3 attempts)
    ↓ Draft created
[STEP 5: Fast Compliance Check] → fast-checker (AUTO, <30s)
    ↓ PASS (or auto-retry if FAIL)
[STEP 6: Full Validation] → validation-aggregator (PARALLEL, 7 validators)
    ↓ Results aggregated
[STEP 7: Final Output] → coordinator formats report
    ↓
USER: Scene ready, validation report, next steps
```

### Time Estimates

- **Total**: 5-8 minutes (including ~30s user approval)
- Step 1-3: <1 minute combined
- Step 4: 3-5 minutes (prose generation)
- Step 5: <30 seconds (fast check)
- Step 6: 60-90 seconds (parallel validation)
- Step 7: <10 seconds (formatting)

---

## STEP 1: File System Check

### Agent: generation-coordinator

### Purpose
Verify that blueprint file exists before starting expensive operations.

### Logic

1. **Extract scene ID** from user prompt (e.g., "0204")
2. **Determine location** from ID:
   - Scene 0204 → Act 1, Chapter 02
   - Pattern: `acts/act-{A}/chapters/chapter-{CC}/scenes/scene-{CCSS}-blueprint.md`
3. **Check file existence**:
   - ✅ **Found**: Continue to Step 2
   - ❌ **Not found**: Return error, suggest `/plan-scene {ID}`

### Outputs

**Success:**
```
✅ Blueprint found: scene-0204-blueprint.md
⏳ Validating blueprint...
```

**Failure:**
```
❌ ERROR: Blueprint not found

File not found: acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md

RECOMMENDED ACTION:
Create blueprint first: /plan-scene 0204

Cannot proceed with generation.
```

---

## STEP 2: Blueprint Validation (AUTO)

### Agent: blueprint-validator

### Purpose
Validate blueprint completeness, consistency, and file naming BEFORE expensive generation. Fail-fast principle.

### Inputs

- **blueprint_path**: Path to blueprint file
- **scene_id**: Scene identifier

### Checks Performed

1. **File Naming Standard**
   - ✅ Standard name: `scene-{ID}-blueprint.md` (NO version suffix)
   - ❌ Versioned name: `scene-0204-blueprint-v2.md` → ERROR
   - ❌ Multiple files: `scene-0204-blueprint.md` + `scene-0204-blueprint-revised.md` → CRITICAL ERROR

2. **Plan File Check**
   - ✅ Standard name: `plan.md` exists (NOT `plan-v2.md`, `plan-v3.md`)
   - ❌ Multiple plan files → CRITICAL ERROR: "Only one plan.md allowed"

3. **Required Fields**
   - Location specified (MUST BE + MUST NOT BE)
   - Characters listed (present + absent with reasons)
   - Mechanics defined (required + forbidden)
   - Scope bounded (beats, forbidden content from other scenes)
   - Word count range

4. **Internal Consistency**
   - Absent characters NOT mentioned in beats
   - Location consistent throughout
   - Mechanics described uniformly
   - No scope violations (references to other scenes)

5. **Cross-Reference with Plan**
   - Read current `plan.md`
   - Check for removed characters (e.g., "Себастьян Грей removed in v3")
   - Verify blueprint aligns with plan changes

### Outputs

**PASS: constraints-list.json**
```json
{
  "status": "PASS",
  "scene_id": "0204",
  "constraints": {
    "location": {
      "required": "Башня Книжников, медпалата",
      "forbidden": ["больница", "медицинский центр"]
    },
    "characters": {
      "present": ["Алекса Райт", "Реджинальд Хавенфорд"],
      "absent": ["Себастьян Грей"],
      "absent_reason": ["removed per plan"]
    },
    "mechanics": {
      "required": "Automatic system compensation",
      "forbidden": ["personal gift", "manual compensation"]
    },
    "scope": {
      "beats": [1, 2, 3, 4],
      "forbidden_content": ["scene-0203 memory", "scene-0205 content"]
    },
    "word_count": {"min": 1000, "max": 1100}
  }
}
```

**FAIL: validation-errors.json**
```json
{
  "status": "FAIL",
  "errors": [
    {
      "type": "multiple_files_detected",
      "severity": "CRITICAL",
      "message": "Multiple blueprint files found",
      "fix": "Move old versions to backups/"
    },
    {
      "type": "contradiction",
      "severity": "HIGH",
      "message": "Beat 2 mentions Себастьян but he's in absent list",
      "fix": "Remove Себастьян from Beat 2"
    }
  ]
}
```

### User Sees

**PASS:**
```
✅ Blueprint validation: PASSED
⏳ Creating verification plan...
```

**FAIL:**
```
❌ Blueprint validation: FAILED

Issues found:
1. [CRITICAL] Multiple blueprint files detected
   - Found: scene-0204-blueprint.md, scene-0204-blueprint-v2.md
   - Fix: Move old versions to backups/, keep only scene-0204-blueprint.md

2. [HIGH] Contradiction in character list
   - Beat 2 mentions "Себастьян Грей enters"
   - But characters section lists him as absent
   - Fix: Remove Себастьян from Beat 2 or clarify character list

CANNOT PROCEED until issues are fixed.
```

---

## STEP 3: Verification Plan (INTERACTIVE)

### Agent: verification-planner

### Purpose
Transform technical constraints into human-readable plan for author approval BEFORE generation.

### Inputs

- **constraints-list.json**: Extracted constraints from Step 2
- **blueprint_path**: Original blueprint for reference

### Outputs

**verification-plan.md** (displayed to user):

```markdown
## 🔍 GENERATION PLAN - REVIEW BEFORE PROCEEDING

**Scene**: 0204
**Date**: 2025-10-31
**Status**: Awaiting your approval

---

### 📍 LOCATION
**Setting**: Башня Книжников, медпалата
**NOT using**: Больница, медицинский центр (outdated locations)

### 👥 CHARACTERS
**Present in scene**:
- Алекса Райт (POV character)
- Реджинальд Хавенфорд (patient)

**Explicitly ABSENT**:
- Себастьян Грей (removed per chapter plan - will NOT appear)

### 🎭 PLOT BEATS
**Beat 1**: Продолжение работы в медпалате
- Алекса продолжает сеанс Погружения с Реджинальдом

**Beat 2**: Погружение - память о смерти дочери
- Реджинальд переживает болезненную память
- Алекса профессионально ведёт сеанс

**Beat 3**: Эмоциональная реакция Алексы
- Алекса затронута страданием Реджинальда
- Внутренний конфликт: профессионализм vs эмпатия

**Beat 4**: Завершение с начислением компенсации
- Сеанс завершается
- Система автоматически начисляет +2 месяца компенсации

### ⚙️ WORLD MECHANICS
**Using**: Automatic system compensation (система начисляет автоматически)
**NOT using**: Personal gift, manual compensation from characters

### 📊 TECHNICAL SPECS
- **Word count**: 1000-1100 words
- **POV**: Алекса Райт (third person limited)
- **Emotional tone**: Professional with underlying emotional resonance
- **Continuity**: Follows scene 0203 (Алекса вошла в медпалату)
- **Prose style**: Style 7 (Professional/Psychological) - see prose-style-guide.md

---

### ✅ CONSTRAINT CHECKLIST
- [ ] Location: Башня Книжников медпалата (NOT hospital)
- [ ] Себастьян Грей does NOT appear (removed per plan)
- [ ] Compensation is automatic system, NOT personal gift
- [ ] Scope: Only these 4 beats, no content from other scenes

---

**Is this plan correct?**
- Type **Y** or press Enter to approve and start generation
- Type **n** to cancel
- Specify changes (e.g., "Change emotional tone to more detached")
```

### User Interaction

**Option A: Approve**
```
User: Y
```
→ Coordinator saves `verified-plan.json`, proceeds to Step 4

**Option B: Modify**
```
User: Change emotional tone from "underlying resonance" to "professional detachment with cracks"
```
→ Coordinator updates constraints, re-generates plan, shows updated version for re-approval

**Option C: Cancel**
```
User: n
```
→ Coordinator asks "What's wrong?" for clarification

### Modification Handling

When user requests changes:
1. Coordinator parses request
2. Updates relevant constraint in constraints-list.json
3. Re-invokes verification-planner with updated constraints
4. Shows updated plan for re-approval
5. **No limit** on modification iterations (but after 5+ suggests updating blueprint)

### User Approval Saved

**verified-plan.json** (used by prose-writer):
```json
{
  "scene_id": "0204",
  "approved_timestamp": "2025-10-31T10:35:00Z",
  "constraints": { /* same as constraints-list.json */ },
  "user_modifications": {
    "emotional_tone": "professional detachment with cracks"
  }
}
```

---

## STEP 4: Generation (AUTO with Retry Logic)

### Agent: prose-writer

### Purpose
Generate high-quality literary prose adhering to ALL constraints from verified plan.

### Inputs

**Primary:**
- **verified-plan.json**: User-approved plan (may include modifications)
- **blueprint_path**: Original blueprint for full context
- **scene_id**: Scene identifier

**Context (Minimal - Rule 8):**
- **previous_scene_path**: Last 300-500 words for continuity
- **pov_character_sheet**: POV character voice, knowledge, emotional state
- **world_mechanics_excerpt**: Specific mechanics referenced (if applicable)
- **prose_style_guide**: `.workflows/prose-style-guide.md` for style-specific techniques

**NOT Provided (isolation):**
- Other scene blueprints
- Full plan document
- Unrelated character sheets
- Full world-bible

### Constraint Application (8 Rules from FEAT-0001)

**Rule 1: Constraint Isolation**
```markdown
## ⚠️ CRITICAL CONSTRAINTS (MUST COMPLY - NO EXCEPTIONS)

### LOCATION
- MUST BE: Башня Книжников, медпалата
- MUST NOT BE: Больница, медицинский центр, госпиталь

### CHARACTERS
- MUST BE PRESENT: Алекса Райт, Реджинальд Хавенфорд
- MUST NOT BE PRESENT: Себастьян Грей (removed per plan)

### MECHANICS
- MUST USE: Automatic system compensation notification
- MUST NOT USE: Personal gift, manual compensation

### SCOPE
- MUST INCLUDE ONLY: Beats 1-4 from Scene 0204
- MUST NOT INCLUDE: Content from scenes 0203, 0205
```

**Rule 2: Verification Checkpoint**
→ Uses pre-approved verified-plan.json

**Rule 3: Constraint Repetition**
→ Constraints repeated 3x in prompt: (1) Top block, (2) Inline with beats, (3) Final checklist

**Rule 5: Single Source of Truth**
→ Exact file paths specified, NO version suffixes allowed

**Rule 7: Constraint Echo**
→ Creates compliance-echo.json confirming constraints

**Rule 8: Minimal Context**
→ Receives ONLY 4-5 files, not full project

### Outputs

**scene-{ID}-draft.md** (full prose):
```markdown
[Literary text, 1000-1100 words]
[Adheres to all constraints]
[Written in approved style, POV, tone]
```

**compliance-echo.json** (metadata):
```json
{
  "scene_id": "0204",
  "constraints_acknowledged": {
    "location": "Башня Книжников, медпалата",
    "characters_present": ["Алекса", "Реджинальд"],
    "characters_absent": ["Себастьян Грей"],
    "mechanics": "Automatic system compensation",
    "scope": "Beats 1-4 only",
    "word_count_target": "1000-1100"
  },
  "actual_metrics": {
    "word_count": 1050,
    "beat_structure": ["Beat 1", "Beat 2", "Beat 3", "Beat 4"]
  },
  "compliance_declaration": "All critical constraints met"
}
```

**IMPORTANT**: prose-writer does NOT return full text in response (context conservation). Text saved to file, only metadata returned.

### Retry Logic (Automatic)

If Step 5 (fast-checker) finds violations:

**Attempt 1** (normal): Standard prompt with 3x constraint repetition

**Attempt 2** (enhanced emphasis):
```markdown
⚠️⚠️⚠️ REGENERATION ATTEMPT 2 ⚠️⚠️⚠️

Previous generation failed due to:
[specific violation from fast-checker]

PAY SPECIAL ATTENTION TO:
- [violated constraint repeated 3 more times]
- [ALL CAPS EMPHASIS on critical element]

This is attempt 2 of 3. Critical compliance required.
```

**Attempt 3** (maximum emphasis):
```markdown
🚨 FINAL ATTEMPT (3/3) 🚨

Previous attempts failed: [violations listed]

ABSOLUTE REQUIREMENTS:
[Violated constraints in BOLD, ALL CAPS, repeated 5x]

IF YOU CANNOT COMPLY: Return error, do NOT generate non-compliant text.
```

**Failure after 3 attempts:**
→ Coordinator stops, returns detailed report to user for manual intervention

---

## STEP 5: Fast Compliance Check (AUTO)

### Agent: blueprint-compliance-fast-checker

### Purpose
Catch obvious violations (<30 sec) before expensive full validation. Enable auto-retry without showing failed drafts to user.

### Inputs

- **draft_path**: Generated prose from Step 4
- **constraints-list.json**: Constraints from Step 2
- **scene_id**: Scene identifier

### Checks Performed (Optimized for Speed)

1. **Location Match** (<5s)
   - Search for required location terms
   - Search for forbidden location terms
   - PASS: Required found AND forbidden NOT found

2. **Character Presence** (<5s)
   - Search for required character names
   - Search for forbidden character names
   - PASS: All required present AND all forbidden absent

3. **Mechanics Check** (<5s)
   - Search for required mechanics keywords
   - Search for forbidden mechanics patterns
   - PASS: Required found AND forbidden NOT found

4. **Scope Boundaries** (<10s)
   - Search for content markers from other scenes
   - PASS: No out-of-scope content detected

5. **Word Count** (<5s)
   - Count words
   - PASS: Within target range ±10%

### Outputs

**PASS: fast-compliance-result.json**
```json
{
  "status": "PASS",
  "checks_performed": [
    {"check": "location_match", "result": "PASS"},
    {"check": "forbidden_characters_absent", "result": "PASS"},
    {"check": "required_characters_present", "result": "PASS"},
    {"check": "mechanics_match", "result": "PASS"},
    {"check": "scope_boundaries", "result": "PASS"}
  ],
  "recommendation": "Proceed to full validation"
}
```

**FAIL: fast-compliance-result.json + retry guidance**
```json
{
  "status": "FAIL",
  "violations": [
    {
      "check": "location_match",
      "result": "FAIL",
      "severity": "HIGH",
      "found": "больница (line 45)",
      "required": "Башня Книжников медпалата",
      "message": "Draft uses forbidden location term"
    }
  ],
  "retry_guidance": {
    "emphasis_needed": [
      "Location: Башня Книжников (NOT больница)"
    ]
  }
}
```

### Decision Flow

```
fast-checker result?
    ├─ PASS → Proceed to Step 6
    └─ FAIL →
        ├─ Retry count < 3?
        │   ├─ YES → Back to Step 4 with enhanced constraints (Attempt 2/3)
        │   └─ NO → STOP, report to user (manual intervention needed)
        └─ [User NEVER sees failed drafts - internal retry only]
```

### User Sees

**PASS:**
```
✅ Fast compliance check: PASSED
⏳ Running full validation (7 validators in parallel)...
```

**FAIL (internal retry - user doesn't see):**
```
[Coordinator automatically retries Step 4 with emphasis]
[User sees only final result or critical failure after 3 attempts]
```

**Critical Failure (after 3 attempts):**
```
❌ Generation failed after 3 attempts

Issues detected:
1. Location: Draft consistently uses "больница" instead of "Башня Книжников"

MANUAL INTERVENTION REQUIRED:
- Review blueprint constraints
- Check if location specification is clear
- Consider rewording location description

Blueprint path: acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md
```

---

## STEP 6: Full Validation (PARALLEL)

### Agent: validation-aggregator

### Purpose
Coordinate 7 specialized validators in parallel for deep quality checks (60-90s total vs. 420s sequential).

### Inputs

- **draft_path**: Scene draft from Step 4
- **blueprint_path**: Original blueprint
- **scene_id**: Scene identifier
- **context_references**: Paths to context files for validators

### Validators (Run in Parallel)

1. **world-lorekeeper**: World mechanics, technology, environment accuracy
2. **canon-guardian**: Canon compliance (levels 0-4), hierarchy violations
3. **character-state**: Character knowledge, emotional states, capabilities
4. **plot-architect**: Plot progression, cause/effect, setup/payoff
5. **scene-structure**: Beat structure, pacing, scene goals
6. **chronicle-keeper**: Timeline, chronology, continuity, numbers
7. **dialogue-analyst**: Dialogue quality, character voice, subtext

Each validator returns: **validation-result.json**

### Outputs

**final-validation-report.json**:
```json
{
  "scene_id": "0204",
  "overall_status": "PASS",
  "validators_run": 7,
  "validators_passed": 7,
  "execution_time_seconds": 65,
  "results": [
    {
      "validator": "world-lorekeeper",
      "status": "PASS",
      "warnings": 0,
      "errors": 0
    },
    {
      "validator": "character-state",
      "status": "PASS",
      "warnings": 1,
      "warnings_details": ["Emotional nuance suggestion (non-blocking)"]
    },
    // ... 5 more validators
  ],
  "blocking_issues": [],
  "non_blocking_warnings": [
    "Emotional nuance suggestion",
    "Dialogue depth suggestion"
  ],
  "recommendation": "APPROVE - All critical requirements met. Warnings are suggestions."
}
```

### Error vs. Warning

**ERROR (blocking):**
- Canon violation
- Timeline conflict
- Character knowledge violation
- Plot hole

**WARNING (non-blocking):**
- Dialogue could be improved
- Emotional depth could be enhanced
- Pacing suggestion
- Sensory details suggestion

### User Sees

**PASS:**
```
✅ Full validation: 7/7 PASSED (65 seconds)
⏳ Preparing final report...
```

**PASS with warnings:**
```
✅ Full validation: 7/7 PASSED with suggestions (72 seconds)

Non-blocking suggestions:
- Character emotional nuance could be deeper (character-state)
- Dialogue subtext could be richer (dialogue-analyst)

These are enhancement suggestions, not blockers.
```

**FAIL:**
```
❌ Full validation: FAILED (1 blocking issue)

BLOCKING ISSUE:
- Canon violation (canon-guardian): Compensation system described incorrectly
  - Draft says "manual approval required"
  - Canon states "automatic system"

RECOMMENDATION: Regenerate with corrected mechanics description.
```

---

## STEP 7: Final Output

### Agent: generation-coordinator

### Purpose
Format transparent, actionable report for user with summary, validation results, and next steps.

### Inputs

- **final-validation-report.json**: From Step 6
- **scene-{ID}-draft.md**: Generated prose
- **execution metadata**: Time taken, retry count

### Outputs

**User-facing report:**

```markdown
## ✅ СЦЕНА 0204 ГОТОВА

**📄 File**: acts/act-1/chapters/chapter-02/content/scene-0204.md
**📊 Volume**: 1,050 words
**⏱️ Generation time**: 4 minutes
**🔄 Attempts**: 1 (success on first attempt)

---

### Brief Summary:
Алекса проводит сеанс Погружения для Реджинальда в медпалате Башни Книжников. Во время сеанса Реджинальд переживает болезненную память о смерти дочери. Алекса профессионально ведёт сеанс, но эмоционально затронута его страданием. После завершения система автоматически начисляет Реджинальду +2 месяца жизни как компенсацию. Сцена заканчивается молчаливым пониманием между персонажами.

### Key Moments:
- ✓ Эмоциональная уязвимость Реджинальда раскрыта
- ✓ Профессионализм Алексы под вопросом (внутренний конфликт)
- ✓ Механика компенсации показана в действии
- ✓ Отношения персонажей углублены

### Validation Results:
✅ World-lore: PASS
✅ Canon: PASS
✅ Character-state: PASS (1 suggestion)
✅ Plot: PASS
✅ Scene-structure: PASS
✅ Chronology: PASS
✅ Dialogue: PASS (2 suggestions)

**Suggestions (non-blocking):**
- Character emotional nuance could be deeper
- Dialogue subtext could be richer
- Consider varying dialogue tags

---

### 🎯 Next Steps:
- Generate scene 0205? (next in sequence)
- Edit scene 0204? (manual refinement)
- Move to another chapter?
```

### What User Does NOT See

- Failed generation attempts (if auto-retry succeeded)
- Internal artifact paths
- Technical validation details
- Full prose in chat (saved to file)

---

## Agents in Generation Workflow

### Orchestration
- **generation-coordinator**: 7-step workflow orchestrator (NEW in FEAT-0001)

### Pre-Generation (Steps 1-3)
- **blueprint-validator**: Blueprint compliance checker (NEW in FEAT-0001)
- **verification-planner**: Human-readable plan generator (NEW in FEAT-0001)

### Generation (Step 4)
- **prose-writer**: Literary prose generator (MODIFIED in FEAT-0001)

### Validation (Steps 5-6)
- **blueprint-compliance-fast-checker**: Fast surface checks (NEW in FEAT-0001)
- **validation-aggregator**: Parallel validation coordinator (NEW in FEAT-0001)
- **world-lorekeeper**: World mechanics validator
- **canon-guardian**: Canon compliance validator
- **character-state**: Character logic validator
- **plot-architect**: Plot consistency validator
- **scene-structure**: Beat structure validator
- **chronicle-keeper**: Timeline/chronology validator (NEW in FEAT-0001)
- **dialogue-analyst**: Dialogue quality validator

---

## File Naming Standards (CRITICAL)

### The Real Problem

Multiple files with different names caused ambiguity:
```
plan.md (original)
plan-revised.md (rewrite #1)
plan-v2.md (rewrite #2)
plan-v3.md (rewrite #3)
```
→ Agents didn't know which file was current → constraint violations

### Solution: ONE Canonical File

**✅ ALWAYS use standard names:**
```
acts/act-{N}/chapters/chapter-{NN}/plan.md
acts/act-{N}/chapters/chapter-{NN}/scenes/scene-{NNNN}-blueprint.md
acts/act-{N}/chapters/chapter-{NN}/content/scene-{NNNN}.md
```

**❌ NEVER create version suffixes:**
```
plan-revised.md       ← WRONG
plan-v2.md           ← WRONG
scene-X-blueprint-v2.md  ← WRONG
```

### Versioning Method: Timestamped Backups

**Directory Structure:**
```
acts/act-1/chapters/chapter-02/
├── plan.md                      ← Current version (ONLY this file)
├── scenes/
│   ├── scene-0201-blueprint.md  ← Current blueprint
│   └── scene-0204-blueprint.md
├── content/
│   ├── scene-0201.md
│   └── scene-0204.md
└── backups/                     ← Timestamped old versions
    ├── plan-2025-10-27-14-30.md
    └── scene-0204-blueprint-2025-10-29-16-45.md
```

### Agent Behavior

**Rule 1: Single Source of Truth**
- ALWAYS read `plan.md` (no version suffix)
- NEVER guess which file to use

**Rule 2: Multiple Files = ERROR**
If agent finds multiple plan files → STOP immediately with error

**Rule 3: Automatic Backup**
Before modifying `plan.md` → create timestamped backup in `backups/`

---

## Context Window Management

### Problem (Before FEAT-0001)

Typical scene generation:
- Blueprint: 3000 tokens
- Previous scene: 1500 tokens
- Character sheets: 2000 tokens
- World mechanics: 1000 tokens
- Generated draft: 1500 tokens
- **Total**: ~10,000 tokens

### Solution (FEAT-0001)

- Agents receive **FILE PATHS**, not content (10 tokens vs 3000 tokens)
- prose-writer receives **ONLY 4-5 files** (not full world-bible)
- Validators receive **ONLY relevant context**
- Coordinator sees **summaries**, not full texts
- Full draft **NEVER returned** in response (saved to file)

**Result**: Context window usage reduced by **60-70%**

---

## Execution Patterns

### Sequential Steps (must wait for previous)

1. Step 1 → Step 2 (can't validate before finding blueprint)
2. Step 2 → Step 3 (can't create plan before extracting constraints)
3. Step 3 → Step 4 (can't generate before approval)
4. Step 4 → Step 5 (can't check before generation)
5. Step 5 → Step 6 (can't deep-validate before fast-check passes)

### Parallel Steps (concurrent execution)

- **Step 6**: All 7 validators run in parallel
  - **Time saved**: 60-90 sec (parallel) vs. 420 sec (sequential)

### Total Time

- Sequential portion: ~5-6 min (Steps 1-5)
- Parallel portion: ~1-1.5 min (Step 6)
- **Total**: 6-7.5 min (vs. 10-15 min if all sequential)

---

## Error Handling

### Blueprint Not Found (Step 1)
```
→ Clear error message
→ Suggest /plan-scene {ID}
→ STOP workflow
```

### Validation Fails (Step 2)
```
→ Return specific issues
→ Provide fix recommendations
→ STOP workflow
```

### User Declines Plan (Step 3)
```
→ Ask "What needs to change?"
→ Update plan
→ Re-show for approval
→ Loop until approved or cancelled
```

### Generation Fails (Step 4-5)
```
→ Auto-retry (max 3 attempts) with enhanced constraints
→ User does NOT see failed attempts
→ After 3 failures → STOP with detailed report
```

### Validation Warnings (Step 6)
```
→ Non-blocking warnings shown
→ Workflow proceeds
→ User informed in final report
```

### Validation Errors (Step 6)
```
→ Blocking errors STOP workflow
→ User sees detailed issue
→ Recommendation for fix
```

---

## Observability

### Logging

Each agent logs to: `workspace/logs/{agent-name}/scene-{ID}-{timestamp}.log`

Includes:
- Timestamp start/end
- Files read
- Constraints extracted/applied
- Decisions made
- Execution time

### Tracing

Full execution trace: `workspace/generation-runs/{timestamp}-scene-{ID}/trace.md`

### Metrics Tracked

- Constraint compliance rate (target: >95%)
- Generation time per step
- Retry rate (target: <10%)
- Validation pass rate

---

## Success Metrics (FEAT-0001 Goals)

### Quality
- **Constraint compliance**: >95% (scenes pass fast-check on 1st attempt)
- **Zero scope violations**: Content only from specified beats
- **Blueprint validation**: >90% pass before generation

### Efficiency
- **Generation time**: 4-7 minutes (including verification)
- **Auto-regeneration**: <10% of scenes need retry
- **Human intervention**: <5% require manual fixes

### UX
- **Author in control**: 100% (verification plan always shown)
- **Transparency**: User understands each step
- **No surprises**: ИИ не принимает сюжетных решений без одобрения

---

## Migration from v2.0 to v3.0 (FEAT-0001)

### Breaking Changes

1. **File naming**: Version suffixes no longer allowed
   - **Action**: Rename `plan-v3.md` → `plan.md`
   - **Action**: Move old versions to `backups/`

2. **Blueprint validation**: Now required before generation
   - **Impact**: Invalid blueprints caught earlier
   - **Benefit**: Fewer failed generations

3. **Verification plan**: Human approval now mandatory
   - **Impact**: +30 seconds per scene (user review time)
   - **Benefit**: Full transparency, control over plot

### Backward Compatibility

- **Old blueprints**: Still work if properly named
- **Old agents**: Deprecated (director, sci-fi-world-writer replaced by generation-coordinator, prose-writer)

### Migration Steps

1. **Rename versioned files** to standard names
2. **Move old versions** to `backups/` subdirectories
3. **Verify blueprints** exist for scenes you want to generate
4. **Use new command**: "Generate scene {ID}" (instead of pointing to blueprint file)

---

**Related Documents:**
- [FEAT-0001 README](../features/FEAT-0001-reliable-scene-generation/README.md) - User journey and requirements
- [FEAT-0001 Technical Design Part 1](../features/FEAT-0001-reliable-scene-generation/TECHNICAL_DESIGN_PART1.md) - Architecture and agents
- [Planning Workflow](planning.md) - How to create blueprints
- [Agents Reference](agents-reference.md) - All agent specifications
- [Prose Style Guide](prose-style-guide.md) - Writing style guidelines

---

**Version History:**
- v3.0 (2025) - FEAT-0001 integrated: 7-step workflow, multi-stage validation, human-in-the-loop
- v2.0 (2024) - Multi-agent validation, artifact system
- v1.0 (2024) - Initial workflow
