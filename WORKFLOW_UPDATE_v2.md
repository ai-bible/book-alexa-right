# WORKFLOW UPDATE v2.0: Preventing Blueprint Compliance Errors

**Date**: 2025-10-27
**Status**: PROPOSED CHANGES
**Context**: После обнаружения систематических ошибок prose-writer в сценах 0202 и 0204

---

## EXECUTIVE SUMMARY

**Problem**: prose-writer систематически игнорирует критические требования blueprint v3:
- Scene 0202: Включил материал для 0203 (воспоминание о Диане)
- Scene 0204: Использовал неправильную локацию (больница вместо Башни Книжников), включил удалённого персонажа (Себастьян Грей), изменил механику компенсации

**Root Causes**:
1. Критические constraints "растворены" в длинных промптах
2. Нет pre-generation verification checkpoint
3. Нет fail-fast validation перед полной генерацией
4. Blueprint compliance не проверяется ПЕРЕД генерацией

**Solution**: 8 правил + изменения в Generation Workflow на основе Anthropic best practices

---

## PART 1: 8 ПРАВИЛ ДЛЯ ПРЕДОТВРАЩЕНИЯ ОШИБОК

### Rule 1: Constraint Isolation Principle

**Суть**: Критические constraints ВСЕГДА выделяются в отдельный блок в начале промпта.

**Формат для prose-writer промпта:**
```markdown
## ⚠️ CRITICAL CONSTRAINTS (MUST COMPLY - NO EXCEPTIONS)

These are NON-NEGOTIABLE requirements. If you cannot comply, STOP and return error.

### LOCATION
- MUST BE: [точная локация из blueprint]
- MUST NOT BE: [запрещённые локации]

### CHARACTERS
- MUST BE PRESENT: [список обязательных]
- MUST NOT BE PRESENT: [список запрещённых - особенно удалённые в v3]

### MECHANICS
- MUST USE: [конкретные механики из blueprint]
- MUST NOT USE: [запрещённые механики]

### SCOPE
- MUST INCLUDE ONLY: Beats [X-Y] from THIS scene
- MUST NOT INCLUDE: Content from other scenes [перечислить какие]
```

**Rationale**: Anthropic best practice - явное выделение constraints в начале промпта улучшает compliance.

**Priority**: **HIGH** - простое изменение, большой эффект

---

### Rule 2: Pre-Generation Verification Checkpoint

**Суть**: Перед генерацией полного текста, агент СНАЧАЛА возвращает verification plan.

**New Workflow для Generation Stage 6:**
```
CURRENT:
User prompt → prose-writer → Full text (1500 words) → Validation

PROPOSED:
User prompt → prose-writer (verification mode) → Verification plan (150 words)
→ [User/Director approval] → prose-writer (generation mode) → Full text → Validation
```

**Verification Plan Format:**
```markdown
## GENERATION PLAN VERIFICATION

Before I generate the full text, let me confirm the key elements:

**Location**: [точная локация] ✓/✗
**Characters present**: [список] ✓/✗
**Characters absent**: [список] ✓/✗
**Mechanics**: [описание] ✓/✗
**Scene scope**: Beats [X-Y] as per blueprint ✓/✗
**Word count target**: [X-Y] words ✓/✗

**CONSTRAINTS COMPLIANCE CHECK**:
- [ ] Location matches blueprint exactly
- [ ] No removed v3 characters present
- [ ] Mechanics match blueprint
- [ ] Scope limited to this scene only

If all ✓, I will proceed with full generation.
If any ✗, please clarify before I generate.
```

**Implementation**:
- Добавить `verification_mode` параметр в prose-writer
- Если `verification_mode=true`: return plan, не генерировать текст
- После approval: вызвать prose-writer с `verification_mode=false`

**Rationale**: Anthropic best practice - verification before expensive operations. Позволяет поймать ошибку до генерации 1500 слов.

**Priority**: **HIGH** - предотвращает дорогие ошибки

---

### Rule 3: Constraint Repetition Protocol

**Суть**: Критические constraints повторяются в 3 местах промпта.

**Места:**
1. **В начале**: Блок CRITICAL CONSTRAINTS (см. Rule 1)
2. **Inline reminders**: Перед каждым релевантным блоком
3. **В конце**: FINAL CHECKLIST

**Пример:**
```markdown
## ⚠️ CRITICAL CONSTRAINTS
[блок из Rule 1]

## STRUCTURE

**Beat 1**: Продолжение работы в медпалате
**REMINDER**: Location is Башня Книжников медпалата, NOT hospital or medical center

**Beat 2**: Погружение - память о смерти дочери
**REMINDER**: Себастьян Грей does NOT appear in this scene (removed in v3)

**Beat 4**: Завершение сеанса, начисление компенсации
**REMINDER**: Compensation is AUTOMATIC system notification, NOT personal gift

## FINAL CHECKLIST BEFORE GENERATION

Check these before returning your output:
- [ ] Location: Башня Книжников ✓
- [ ] No Себастьян Грей ✓
- [ ] Automatic compensation (not personal gift) ✓
- [ ] Only Beats 1-4 of THIS scene (no content from 0203 or 0205) ✓
```

**Rationale**: Repetition improves constraint adherence, особенно в длинных промптах (proven Anthropic pattern).

**Priority**: **MEDIUM** - усиливает Rule 1

---

### Rule 4: Fail-Fast Validation Rule

**Суть**: Добавить нового агента **blueprint-validator** который проверяет compliance ПЕРЕД prose-writer.

**New Agent Specification:**

**File**: `.claude/agents/generation/blueprint-validator.md`
```markdown
# blueprint-validator

## Role
Pre-generation blueprint compliance checker - validates that scene requirements are clear and consistent before expensive generation.

## When to Use
ALWAYS run before prose-writer in Generation Workflow Stage 6.

## Inputs
- Blueprint file path
- Scene ID
- Critical constraints list from plan-v3

## Tasks
1. Read blueprint file
2. Extract critical requirements:
   - Location
   - Characters (present/absent)
   - Mechanics
   - Scope (which beats)
3. Check for internal contradictions
4. Check for conflicts with plan-v3 documented changes
5. Verify all critical constraints are clearly specified
6. Return GO/NO-GO decision

## Outputs
### If PASS (GO):
```
✅ BLUEPRINT VALIDATION PASSED

Scene: [ID]
Blueprint: [file path]
Version: [extracted from blueprint]

VALIDATED CONSTRAINTS:
- Location: [exact location]
- Characters present: [list]
- Characters absent: [list]
- Mechanics: [description]
- Scope: Beats [X-Y]

READY FOR GENERATION
```

### If FAIL (NO-GO):
```
❌ BLUEPRINT VALIDATION FAILED

Scene: [ID]
Blueprint: [file path]

ISSUES FOUND:
1. [Specific issue with location/characters/etc]
2. [...]

REQUIRED ACTIONS:
- Fix: [specific fix needed]
- Then: Re-run blueprint-validator

DO NOT PROCEED TO GENERATION until validation passes.
```

## Priority
Run FIRST in Stage 6, before prose-writer is invoked.
```

**New Workflow:**
```
Planning → blueprint-validator → [PASS] → prose-writer → Validation
                              ↓
                           [FAIL] → Fix blueprint → Retry validation
```

**Rationale**: Anthropic Skills pattern - specialized validator before expensive operation. Fail-fast principle.

**Priority**: **HIGH** - prevents wasted generation

---

### Rule 5: Single Source of Truth Principle

**Суть**: Всегда явно указывать ОДИН файл как источник истины в промпте.

**Format for prose-writer prompt:**
```markdown
## 📄 SOURCE OF TRUTH

**PRIMARY BLUEPRINT**:
File: E:\sources\book-alexa-right\acts\act-1\chapters\chapter-02\scenes\scene-0204-blueprint.md
Version: v3.0 FINAL (post plan-v3 corrections)
Status: APPROVED FOR GENERATION

⚠️ DO NOT USE:
- scene-0204-revised.md (outdated, pre-v3)
- scene-0204-draft.md (draft, not blueprint)
- Any "v1" or "v2" versions
- Any files in /workspace/

**IF THE FILE PATH ABOVE DOES NOT EXIST OR IS UNCLEAR:**
STOP and return error: "Cannot locate primary blueprint: [path]"
DO NOT proceed with generation.
DO NOT guess or use alternative files.
```

**Implementation**:
- В director или координирующем агенте: всегда передавать EXACT file path
- В prose-writer: проверять существование файла перед чтением
- Если файл не найден: STOP, не угадывать

**Rationale**: Устраняет ambiguity. Single source of truth - fundamental engineering principle.

**Priority**: **HIGH** - простое, эффективное

---

### Rule 6: Version Tagging Protocol

**Суть**: Все blueprints помечаются версией и содержат changelog.

**Required Blueprint Header Format:**
```markdown
# Scene [ID] Blueprint

**Version**: v3.0 (FINAL)
**Date**: 2025-10-27
**Status**: APPROVED FOR GENERATION
**Previous versions**: v2.0 (revised.md), v1.0 (original)

---

## 🔄 V3 CRITICAL CHANGES (from v2)

### REMOVED in v3:
- ❌ Себастьян Грей (all mentions, all scenes 0201-0204)

### CHANGED in v3:
- ✅ Location: NOW Башня Книжников (WAS: unspecified/various)
- ✅ Compensation: NOW automatic system (WAS: personal gift)
- ✅ Navigation: NOW automated (WAS: personal escort)

### ADDED in v3:
- ✅ [Any new requirements]

---

## ⚠️ GENERATION REQUIREMENTS

IF YOU ARE GENERATING THIS SCENE:
- YOU MUST COMPLY WITH ALL V3 CHANGES ABOVE
- YOU MUST NOT use any elements marked REMOVED
- YOU MUST use elements marked CHANGED with their NEW form
- IF UNSURE: Stop and request clarification

---

[rest of blueprint content]
```

**Action Required**: Update all blueprints in `/acts/act-1/chapters/chapter-02/scenes/` with this header.

**Rationale**: Explicit version control reduces confusion about which requirements apply. Self-documenting.

**Priority**: **MEDIUM** - помогает clarity, но требует manual work

---

### Rule 7: Constraint Echo Requirement

**Суть**: prose-writer ОБЯЗАН эхом повторить критические constraints в своём финальном ответе.

**Required Output Format for prose-writer:**
```markdown
## ✅ CONSTRAINTS ACKNOWLEDGED AND COMPLIED

Before generation, I confirmed:
- ✅ Location: [exact location from blueprint]
- ✅ Characters present: [list]
- ✅ Characters absent: [list - including removed v3 characters]
- ✅ Mechanics: [description]
- ✅ Scope: Beats [X-Y] only, no content from other scenes
- ✅ Word count: [actual] words (target: [range])

---

## GENERATION COMPLETE

✅ Сцена [ID] сгенерирована
Файл: workspace/scene-[ID]-draft.md
Объём: [X] слов
Статус: Готова к валидации

**Blueprint Compliance**: All critical constraints met ✓
```

**Implementation**:
- Добавить в prose-writer промпт: "You MUST echo constraints in your response"
- В validation: проверять наличие этого блока
- Если блок отсутствует: warning (агент не подтвердил compliance)

**Rationale**: Forcing echo improves attention to constraints (proven Anthropic prompting pattern).

**Priority**: **MEDIUM** - усиливает awareness

---

### Rule 8: Minimal Context Principle

**Суть**: prose-writer получает ТОЛЬКО необходимый контекст, не весь проект.

**BAD (current approach):**
```
prose-writer has access to:
- All blueprints (риск: выбирает неправильный)
- All scenes (риск: путает scope)
- Full plan-v3 (риск: теряется в деталях)
- All character sheets (риск: использует ненужные)
```

**GOOD (proposed approach):**
```
prose-writer receives ONLY:
1. Scene [ID] blueprint (THIS FILE ONLY)
2. Previous scene content (for continuity)
3. Character sheet for POV character
4. Extracted critical constraints list
5. World-bible excerpts (if needed for this scene)

NOT accessible:
- Other scene blueprints
- Old versions (revised, v1, v2)
- Full plan-v3 (only relevant excerpts)
- Unrelated character sheets
```

**Implementation**:
- В director: готовить isolated context package
- Передавать prose-writer только необходимые file paths
- Не давать access to full directories

**Rationale**: Context isolation reduces errors from wrong sources (Anthropic Skills isolation pattern).

**Priority**: **MEDIUM** - архитектурное улучшение

---

## PART 2: ОБНОВЛЁННЫЙ GENERATION WORKFLOW

### Current Stage 6: Text Generation

```
INPUT: Blueprint, previous scene
↓
prose-writer generates full text (1500 words)
↓
OUTPUT: Draft file
↓
Stage 7: Validation (7 agents in parallel)
```

**Problems**:
- No pre-check of blueprint clarity
- No verification before expensive generation
- Constraints buried in long prompt
- No fail-fast mechanism

---

### Proposed Stage 6: Text Generation (REVISED)

```
INPUT: Blueprint, previous scene, plan-v3 constraints

↓ STEP 1: Pre-Generation Validation (NEW)
blueprint-validator
├─ Reads blueprint
├─ Checks clarity and consistency
├─ Validates v3 compliance
└─ Returns GO/NO-GO

↓ [IF NO-GO: Stop, fix blueprint, retry]
↓ [IF GO: Continue]

↓ STEP 2: Verification Plan (NEW)
prose-writer (verification_mode=true)
├─ Reads blueprint
├─ Extracts constraints
├─ Returns verification plan (150 words)
└─ Waits for approval

↓ [Director or User reviews plan]
↓ [IF issues: Clarify and retry]
↓ [IF approved: Continue]

↓ STEP 3: Full Generation (EXISTING, IMPROVED)
prose-writer (verification_mode=false)
├─ Uses approved constraints
├─ Generates full text (target words)
├─ Echoes constraints in output
└─ Saves to draft file

↓
OUTPUT: Draft file + Compliance confirmation
↓
Stage 7: Validation (8 agents, see below)
```

**Benefits**:
- Catches blueprint issues BEFORE generation
- Verifies understanding BEFORE expensive work
- Confirms compliance AFTER generation
- Saves tokens and time on errors

---

### Proposed Stage 7: Validation (ADD 8th Validator)

**Current validators (7):**
1. world-lorekeeper
2. canon-guardian
3. character-state
4. plot-architect
5. scene-structure
6. chronicle-keeper
7. dialogue-analyst

**ADD: 8th validator (runs FIRST):**
8. **blueprint-compliance-fast-checker**

**Specification:**

**File**: `.claude/agents/generation/blueprint-compliance-fast-checker.md`
```markdown
# blueprint-compliance-fast-checker

## Role
Fast blueprint compliance checker - catches obvious violations immediately before deep validation.

## When to Use
Stage 7, runs FIRST before other validators (parallel execution).

## Speed Target
< 30 seconds (fast read, simple checks)

## Checks
### Location Check
- Draft mentions: [extract location mentions]
- Blueprint requires: [required location]
- Match: ✓/✗

### Character Presence Check
- Draft includes: [list characters found]
- Blueprint requires present: [list]
- Blueprint requires absent: [list]
- Match: ✓/✗

### Mechanics Check
- Draft uses: [extract mechanics description]
- Blueprint requires: [required mechanics]
- Match: ✓/✗

### Scope Check
- Draft content: Beats [detected]
- Blueprint scope: Beats [X-Y]
- Match: ✓/✗

## Output Format

### If PASS:
```
✅ FAST COMPLIANCE CHECK: PASSED

Scene: [ID]
All critical constraints met at surface level.
Proceed with deep validation.
```

### If FAIL:
```
❌ FAST COMPLIANCE CHECK: FAILED

Scene: [ID]

VIOLATIONS DETECTED:
- Location: ✗ Found "[X]", Required "[Y]"
- Character: ✗ "[Name]" present, should be absent (v3 removal)
- Mechanics: ✗ [description of mismatch]
- Scope: ✗ Contains content from Scene [other ID]

RECOMMENDATION:
STOP deep validation. Return to prose-writer with corrections.

DO NOT proceed with other validators until this is fixed.
```

## Priority
ALWAYS runs first. If FAIL, other validators should not run (waste of resources).
```

**Workflow integration:**
```
Stage 7:
├─ blueprint-compliance-fast-checker (runs FIRST)
│  ├─ [PASS] → Continue to parallel validation
│  └─ [FAIL] → STOP, return to Stage 6 with errors
│
└─ [If PASS] Parallel validation (7 agents):
   ├─ world-lorekeeper
   ├─ canon-guardian
   ├─ character-state
   ├─ plot-architect
   ├─ scene-structure
   ├─ chronicle-keeper
   └─ dialogue-analyst
```

**Benefits**:
- Fast-fail prevents wasted validation on fundamentally broken drafts
- Saves tokens/time on obvious errors
- Clear signal to prose-writer about what's wrong

---

## PART 3: UPDATED PROSE-WRITER PROMPT TEMPLATE

**File**: `.workflows/prompts/prose-writer-template-v2.md`

```markdown
# PROSE-WRITER PROMPT TEMPLATE v2.0

Use this template when calling prose-writer agent.

---

## ⚠️ CRITICAL CONSTRAINTS (MUST COMPLY - NO EXCEPTIONS)

These are NON-NEGOTIABLE. If you cannot comply, STOP and return error.

### LOCATION
- MUST BE: [Insert exact location from blueprint]
- MUST NOT BE: [List forbidden locations, especially from old versions]

### CHARACTERS
- MUST BE PRESENT: [List required characters]
- MUST NOT BE PRESENT: [List forbidden characters, especially removed in v3]
  * Special attention: [List v3 removals]

### MECHANICS
- MUST USE: [Describe required mechanics from blueprint]
- MUST NOT USE: [Describe forbidden mechanics]

### SCOPE
- MUST INCLUDE ONLY: Beats [X-Y] from Scene [ID]
- MUST NOT INCLUDE:
  * Content from Scene [list other scenes]
  * Content from Events [list if applicable]
  * [Other scope restrictions]

---

## 📄 SOURCE OF TRUTH

**PRIMARY BLUEPRINT**:
Path: [Insert EXACT file path]
Version: [Insert version from blueprint header]
Status: APPROVED FOR GENERATION

⚠️ DO NOT USE:
- [List other files that might be confused with this blueprint]
- Any files in /workspace/
- Any "draft" or "revised" versions unless explicitly specified above

**IF THE FILE PATH ABOVE DOES NOT EXIST:**
STOP and return: "ERROR: Cannot locate primary blueprint at [path]"

---

## 🎯 TASK: Two-Stage Generation

### STAGE 1: Verification Plan (REQUIRED FIRST)

Before generating full text, you MUST return a verification plan.

**Output format:**
```
## VERIFICATION PLAN

**Location**: [State exact location]
**Characters present**: [List]
**Characters absent**: [List, including v3 removals]
**Mechanics**: [Describe]
**Scope**: Beats [X-Y]
**Word count target**: [X-Y] words

**CONSTRAINTS COMPLIANCE CHECK**:
- [ ] Location matches blueprint exactly
- [ ] No removed v3 characters present
- [ ] Mechanics match blueprint
- [ ] Scope limited to this scene only
- [ ] [Any other scene-specific constraints]

**Status**: Ready for approval
```

**STOP HERE. Wait for approval before Stage 2.**

---

### STAGE 2: Full Text Generation (After approval)

**Only proceed if Stage 1 was approved.**

#### ВХОДНЫЕ ФАЙЛЫ
- PRIMARY BLUEPRINT: [path from above]
- PREVIOUS SCENE: [path for continuity]
- CHARACTER SHEET: [path for POV character]
- PLAN EXCERPT: [relevant constraints only]

#### ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ
- **Length**: [X-Y] words
- **POV**: [Specify POV style]
- **Tone**: [Specify tone]
- **Style**: [Specify style]

#### СТРУКТУРА (from blueprint)
[Insert beat structure from blueprint]

#### КЛЮЧЕВЫЕ МОМЕНТЫ
[Insert key moments from blueprint]

#### SENSORY PALETTE
[Insert sensory details from blueprint]

#### CONTINUITY
- **From previous scene**: [What happened]
- **To next scene**: [What should lead to]

#### INLINE REMINDERS
[Insert reminders for specific beats that relate to critical constraints]

Example:
- **Beat 2**: [Description]
  * REMINDER: Location is [X], NOT [Y]
- **Beat 3**: [Description]
  * REMINDER: [Character] does NOT appear

#### ВЫХОДНОЙ ФАЙЛ
SAVE RESULT TO: [Insert exact file path]

---

## ✅ FINAL CHECKLIST (Check before returning)

Before you return your output, verify:
- [ ] Location matches blueprint exactly
- [ ] No removed v3 characters present
- [ ] Mechanics match blueprint specification
- [ ] Scope is only this scene (no content from other scenes)
- [ ] Word count within target range
- [ ] File saved to correct path
- [ ] [Any scene-specific checks]

---

## 📤 OUTPUT FORMAT (REQUIRED)

You MUST return your output in this format:

```
## ✅ CONSTRAINTS ACKNOWLEDGED AND COMPLIED

Before generation, I confirmed:
- ✅ Location: [exact location]
- ✅ Characters present: [list]
- ✅ Characters absent: [list including v3 removals]
- ✅ Mechanics: [description]
- ✅ Scope: Beats [X-Y] only
- ✅ Word count: [actual] words (target: [range])

---

## GENERATION COMPLETE

✅ Сцена [ID] сгенерирована
Файл: [path where saved]
Объём: [X] слов
Статус: Готова к валидации

**Blueprint Compliance**: All critical constraints met ✓
```

DO NOT return the full text in your response. Save to file only.

---

## 🔄 CONSTRAINT REPETITION

[Key constraints repeated here for reinforcement]

---

END OF TEMPLATE
```

---

## PART 4: IMPLEMENTATION CHECKLIST

### Immediate Actions (Before Next Generation)

- [ ] **Create blueprint-validator agent**
  - File: `.claude/agents/generation/blueprint-validator.md`
  - Copy specification from Rule 4 above
  - Test on existing blueprint

- [ ] **Create blueprint-compliance-fast-checker agent**
  - File: `.claude/agents/generation/blueprint-compliance-fast-checker.md`
  - Copy specification from Stage 7 section
  - Test on existing draft

- [ ] **Update prose-writer prompt template**
  - File: `.workflows/prompts/prose-writer-template-v2.md`
  - Copy template from Part 3 above
  - Use for scene 0204 regeneration

- [ ] **Add version headers to all blueprints**
  - Directory: `/acts/act-1/chapters/chapter-02/scenes/`
  - Add header from Rule 6 to each blueprint
  - Document v3 changes in each

- [ ] **Update Generation Workflow documentation**
  - File: `.workflows/generation.md`
  - Add new Stage 6 steps (3-step process)
  - Add 8th validator to Stage 7
  - Reference these 8 rules

### Testing (On Scene 0204 Regeneration)

- [ ] **Run blueprint-validator first**
  - Input: scene-0204-blueprint.md
  - Expected: PASS with extracted constraints
  - If FAIL: Fix blueprint before generation

- [ ] **Run prose-writer with new template**
  - Stage 1: Get verification plan
  - Review plan for compliance
  - Stage 2: Approve and generate full text
  - Check for constraint echo in output

- [ ] **Run fast-checker before other validators**
  - Input: scene-0204-draft.md
  - Expected: PASS (if generation followed constraints)
  - If FAIL: Immediate stop, review errors

- [ ] **Full validation cycle**
  - If fast-checker PASS: run all 7 validators
  - Aggregate results
  - Compare error rate vs. old workflow

### Documentation

- [ ] **Update .workflows/generation.md**
  - Section: "Stage 6: Text Generation"
  - Add 3-step process
  - Add blueprint-validator
  - Add verification checkpoint

- [ ] **Update .workflows/generation.md**
  - Section: "Stage 7: Validation"
  - Add 8th validator (fast-checker)
  - Update parallel execution diagram
  - Add fail-fast logic

- [ ] **Create .workflows/rules/constraint-compliance.md**
  - Document all 8 rules
  - Provide examples
  - Link to agent specifications
  - Link to prompt templates

- [ ] **Update .workflows/agents-reference.md**
  - Add blueprint-validator
  - Add blueprint-compliance-fast-checker
  - Update prose-writer entry (now 2-stage)

### Long-term Improvements

- [ ] **Create constraint extraction tool**
  - Automate extraction of constraints from plan-v3
  - Feed directly to blueprint-validator
  - Reduce manual error

- [ ] **Add version control to artifacts**
  - Track which blueprint version generated which draft
  - Enable rollback if needed
  - Audit trail

- [ ] **Metrics tracking**
  - Count blueprint validation failures
  - Count fast-checker catches
  - Measure time saved by fail-fast
  - Track constraint compliance rate

---

## PART 5: EXAMPLE - Scene 0204 Regeneration

### Step-by-step with new workflow

#### Step 1: Run blueprint-validator

```bash
Task: blueprint-validator
Input:
  - Blueprint: acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md
  - Scene ID: 0204
  - Plan v3 constraints: [extracted list]
```

**Expected Output:**
```
✅ BLUEPRINT VALIDATION PASSED

Scene: 0204
Blueprint: scene-0204-blueprint.md
Version: v3.0 FINAL

VALIDATED CONSTRAINTS:
- Location: Башня Книжников, медпалата
- Characters present: Алекса, Реджинальд
- Characters absent: Себастьян Грей (removed in v3)
- Mechanics: Automatic system compensation (not personal gift)
- Scope: Beats 1-4 (продолжение работы, погружение, эмоциональная реакция, завершение)

READY FOR GENERATION
```

**If NO-GO**: Fix blueprint, retry

---

#### Step 2: Run prose-writer (verification mode)

```bash
Task: prose-writer
Mode: verification
Input:
  - Blueprint: [path from step 1]
  - Constraints: [validated list from step 1]
  - Previous scene: acts/act-1/chapters/chapter-02/content/scene-0203.md
```

**Prompt** (using template v2.0):
```markdown
## ⚠️ CRITICAL CONSTRAINTS

### LOCATION
- MUST BE: Башня Книжников, медпалата (where Alexa is treating Reginald)
- MUST NOT BE: Больница, медицинский центр, госпиталь, any other location

### CHARACTERS
- MUST BE PRESENT: Алекса Райт, Реджинальд Хавенфорд
- MUST NOT BE PRESENT:
  * Себастьян Грей (REMOVED IN V3 - do not include)
  * Any doctors, nurses, or medical staff
  * Any other characters

### MECHANICS
- MUST USE: Automatic system notification for compensation (+2 months)
- MUST NOT USE: Personal gift from any character, dialogue about giving time

### SCOPE
- MUST INCLUDE ONLY: Beats 1-4 of Scene 0204
- MUST NOT INCLUDE: Content from Scene 0203 or 0205

---

## SOURCE OF TRUTH
PRIMARY BLUEPRINT: acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md
Version: v3.0 FINAL

⚠️ DO NOT USE: scene-0204-revised.md (outdated)

---

## TASK: STAGE 1 - Verification Plan

Return verification plan before generating full text.
```

**Expected Output:**
```
## VERIFICATION PLAN

**Location**: Башня Книжников, медпалата
**Characters present**: Алекса Райт, Реджинальд Хавенфорд
**Characters absent**: Себастьян Грей (removed v3), medical staff
**Mechanics**: Automatic system compensation notification (+2 months)
**Scope**: Beats 1-4 only (продолжение работы, погружение в память о дочери, эмоциональная реакция Алексы, завершение с автоматическим начислением)
**Word count target**: 1000-1100 words

CONSTRAINTS COMPLIANCE CHECK:
- [✓] Location: Башня Книжников медпалата (NOT hospital)
- [✓] No Себастьян Грей present
- [✓] Automatic system compensation (NOT personal gift)
- [✓] Scope: This scene only, no content from 0203/0205

Status: Ready for approval
```

**Action**: Review plan, approve if correct

---

#### Step 3: Run prose-writer (generation mode)

```bash
Task: prose-writer
Mode: generation
Input:
  - Approved plan: [from step 2]
  - Blueprint: [same as step 2]
  - Previous scene: [same as step 2]
```

**Prompt**: [Full template with all details, STAGE 2 section]

**Expected Output:**
```
## ✅ CONSTRAINTS ACKNOWLEDGED AND COMPLIED

Before generation, I confirmed:
- ✅ Location: Башня Книжников медпалата
- ✅ Characters present: Алекса, Реджинальд
- ✅ Characters absent: Себастьян Грей (v3 removal)
- ✅ Mechanics: Automatic system compensation
- ✅ Scope: Beats 1-4 only
- ✅ Word count: 1050 words (target: 1000-1100)

---

## GENERATION COMPLETE

✅ Сцена 0204 сгенерирована
Файл: workspace/scene-0204-v2-draft.md
Объём: 1050 слов
Статус: Готова к валидации

Blueprint Compliance: All critical constraints met ✓
```

---

#### Step 4: Run fast-checker

```bash
Task: blueprint-compliance-fast-checker
Input:
  - Draft: workspace/scene-0204-v2-draft.md
  - Blueprint: scene-0204-blueprint.md
  - Constraints: [from step 1]
```

**Expected Output (if compliant):**
```
✅ FAST COMPLIANCE CHECK: PASSED

Scene: 0204
All critical constraints met at surface level.
Proceed with deep validation.
```

**Expected Output (if non-compliant):**
```
❌ FAST COMPLIANCE CHECK: FAILED

Scene: 0204

VIOLATIONS DETECTED:
- [Specific violations found]

RECOMMENDATION: STOP deep validation, return to prose-writer.
```

---

#### Step 5: Full validation (if fast-check passed)

Run all 7 validators in parallel as usual.

---

## PART 6: SUCCESS METRICS

After implementing these changes, track:

### Process Metrics
- **Blueprint validation failures**: Count NO-GO from blueprint-validator
- **Verification plan rejections**: Count plans rejected in Step 2
- **Fast-checker catches**: Count failures caught by fast-checker
- **Full regenerations needed**: Count scenes requiring regeneration after full validation

### Quality Metrics
- **Constraint compliance rate**: % of drafts passing fast-checker on first try
- **Blueprint clarity**: % passing blueprint-validator without fixes
- **Time to first valid draft**: Average time from start to compliant draft

### Efficiency Metrics
- **Tokens saved**: Estimate tokens saved by fail-fast (avoided deep validation)
- **Time saved**: Estimate time saved by catching errors early
- **Rework reduction**: Compare regeneration rate before/after

### Target Improvements
- Blueprint validation pass rate: **>90%** (catch issues early)
- Constraint compliance on first generation: **>80%** (prose-writer follows constraints)
- Fast-checker catch rate if non-compliant: **100%** (all obvious violations caught)

---

## PART 7: ROLLOUT PLAN

### Phase 1: Create Infrastructure (1 session)
1. Create blueprint-validator agent
2. Create blueprint-compliance-fast-checker agent
3. Create prose-writer-template-v2.md
4. Update one blueprint (0204) with version header

### Phase 2: Test on Scene 0204 (1 session)
1. Run full new workflow on scene 0204
2. Validate each step works as expected
3. Collect feedback and refine
4. Document any issues or improvements

### Phase 3: Update Documentation (1 session)
1. Update .workflows/generation.md
2. Create .workflows/rules/constraint-compliance.md
3. Update .workflows/agents-reference.md
4. Add examples and troubleshooting

### Phase 4: Backfill Blueprints (1 session)
1. Add version headers to all chapter 2 blueprints
2. Document v3 changes in each
3. Verify consistency across all scenes

### Phase 5: Deploy for Remaining Scenes (ongoing)
1. Use new workflow for scene 0205
2. Monitor metrics
3. Refine based on experience
4. Expand to other chapters as validated

---

## APPENDIX A: Quick Reference

### When to Use Each Rule

| Rule | When | Priority |
|------|------|----------|
| 1. Constraint Isolation | Every prose-writer call | HIGH |
| 2. Verification Checkpoint | Every prose-writer call | HIGH |
| 3. Constraint Repetition | Long prompts (>500 words) | MEDIUM |
| 4. Fail-Fast Validation | Before every generation | HIGH |
| 5. Single Source of Truth | Every file reference | HIGH |
| 6. Version Tagging | Blueprint creation/update | MEDIUM |
| 7. Constraint Echo | Every prose-writer output | MEDIUM |
| 8. Minimal Context | Agent design | MEDIUM |

### Workflow Summary

```
Old: Plan → Generate → Validate → Fix if needed
New: Plan → Validate blueprint → Verify plan → Generate → Fast-check → Validate → Fix if needed
           ↑ FAIL-FAST     ↑ FAIL-FAST    ↑ FAIL-FAST
```

### Critical Files

- Blueprint validator: `.claude/agents/generation/blueprint-validator.md`
- Fast checker: `.claude/agents/generation/blueprint-compliance-fast-checker.md`
- Prompt template: `.workflows/prompts/prose-writer-template-v2.md`
- Rules doc: `.workflows/rules/constraint-compliance.md`
- Workflow doc: `.workflows/generation.md` (updated)

---

## APPENDIX B: Troubleshooting

### Problem: prose-writer still ignores constraints

**Check:**
1. Are constraints in CRITICAL CONSTRAINTS block at top?
2. Are constraints repeated inline where relevant?
3. Is SOURCE OF TRUTH clearly specified?
4. Did verification plan match blueprint?

**Solution**: Add more repetition, use ALL CAPS for critical items

---

### Problem: blueprint-validator gives NO-GO

**Check:**
1. Does blueprint have version header?
2. Are v3 changes documented in blueprint?
3. Are all required fields present (location, characters, mechanics, scope)?

**Solution**: Fix blueprint before generation, don't override validator

---

### Problem: Fast-checker gives false positives

**Check:**
1. Is fast-checker looking for exact string matches? (May need fuzzy matching)
2. Are there legitimate variations in how something is described?

**Solution**: Refine fast-checker logic, or skip fast-check if too noisy

---

## FINAL NOTES

These 8 rules are based on:
- **Anthropic best practices** for agent design and prompting
- **Fail-fast principle** from software engineering
- **Single source of truth** from system design
- **Verification before execution** from quality assurance
- **Actual errors** observed in scenes 0202 and 0204

They are designed to be:
- **Practical**: Can be implemented immediately
- **Scalable**: Work for any number of scenes
- **Measurable**: Have clear success metrics
- **Maintainable**: Self-documenting and consistent

**Priority for implementation:**
1. Rules 1, 2, 4, 5 (HIGH) - These catch most errors
2. Rules 3, 7 (MEDIUM) - These reinforce compliance
3. Rules 6, 8 (MEDIUM) - These improve maintainability

**Next session**: Use this document to implement changes and regenerate scene 0204.

---

END OF DOCUMENT
