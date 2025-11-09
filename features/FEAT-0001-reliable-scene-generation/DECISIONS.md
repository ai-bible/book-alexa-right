# Implementation Decisions for FEAT-0001

**Date**: 2025-10-31
**Status**: APPROVED
**Last Updated**: 2025-10-31 (added versioning system)

---

## CRITICAL: File Versioning System

### Problem That Led to This Feature

The real issue wasn't "plan v3 vs v2" - it was that **plans were rewritten 3 times into DIFFERENT FILES**:
- `plan.md` → `plan-revised.md` → `plan-v2.md` → `plan-v3.md`
- Agents got confused about which file was current
- Same problem with blueprints: `scene-0204-blueprint.md`, `scene-0204-blueprint-revised.md`, etc.

### Solution: ONE Canonical File

**File Naming Standard:**
```
✅ CORRECT (always use these names):
- acts/act-1/chapters/chapter-02/plan.md
- acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md

❌ WRONG (never create these):
- plan-revised.md, plan-v2.md, plan-v3.md
- scene-0204-blueprint-revised.md, scene-0204-blueprint-v2.md
```

**Versioning Method: Timestamped Backups**
```
acts/act-1/chapters/chapter-02/
├── plan.md                     ← Current/active file (ONLY this one)
├── scenes/
│   └── scene-0204-blueprint.md ← Current/active blueprint (ONLY this one)
└── backups/                    ← Automatic timestamped copies
    ├── plan-2025-10-27-14-30.md
    ├── plan-2025-10-25-09-15.md
    └── scene-0204-blueprint-2025-10-29-16-45.md
```

**Rules for Agents:**
1. **ALWAYS** read `plan.md` and `scene-{ID}-blueprint.md` (NO version suffixes)
2. **IF multiple files found** (`plan.md` AND `plan-revised.md`) → **ERROR + STOP**
   - Message: "Multiple plan files detected. Keep ONLY plan.md. Move others to backups/"
3. **BEFORE modifying** a file → create timestamped backup in `backups/`
4. **Automatic migration** at first run: if `plan-v3.md` exists but not `plan.md` → rename it

**Version History:** Use git history or timestamped backups/, NOT separate versioned files.

---

## Answers to Open Questions from TECHNICAL_DESIGN_PART2.md

### Q1: Verification Plan Modification Limits
**Decision**: Без ограничений на количество модификаций. После 5 итераций спросить: "Может, лучше обновить blueprint через /revise-blueprint?"

**Rationale**: Творческий процесс не должен быть искусственно ограничен, но мягкая подсказка после 5 итераций поможет автору понять что проблема может быть в blueprint, а не в плане.

---

### Q2: Fast-Checker False Positive Handling
**Decision**: После 3 неудачных retry с одной и той же ошибкой от fast-checker → skip fast-check, перейти сразу к full validation (7 агентов).

**Rationale**: Если fast-checker 3 раза находит "ошибку", но prose-writer не может её исправить, скорее всего это false positive. Full validation даст более точную картину.

**Implementation**:
```
Attempt 1: fast-check → FAIL (location)
Attempt 2: fast-check → FAIL (location, same issue)
Attempt 3: fast-check → FAIL (location, same issue)
→ Skip fast-check, run full validation
→ If full validation PASSES location check → mark fast-checker for review
```

---

### Q3: Validation Aggregator Timeout Handling
**Decision**: Если validator не отвечает >5 минут → timeout, mark result as WARNING (не FAIL), продолжить с остальными.

**Rationale**: Один зависший validator не должен блокировать весь процесс. WARNING позволяет автору принять решение.

**Implementation**:
```
validation-aggregator:
  - Launch 7 validators in parallel
  - Wait up to 5 minutes per validator
  - If timeout:
    - Mark as WARNING: "validator [name] timed out"
    - Continue with other results
  - Final report includes warnings
```

---

### Q4: Failed Draft Storage Policy
**Decision**: Сохранять неудачные drafts в `workspace/failed-attempts/scene-[ID]/attempt-[N]-draft.md` для debugging.

**Rationale**: Debugging критически важен для улучшения системы. Failed drafts показывают паттерны ошибок.

**Structure**:
```
workspace/
└── failed-attempts/
    └── scene-0204/
        ├── attempt-1-draft.md
        ├── attempt-1-violations.json
        ├── attempt-2-draft.md
        ├── attempt-2-violations.json
        └── metadata.json
```

**Retention**: Хранить до успешной генерации, затем опционально архивировать.

---

### Q5: Auto-Approve Verification Plans Mode
**Decision**: Опциональный флаг `--skip-verification` для batch processing. По умолчанию OFF (verification всегда показывается).

**Usage**:
```bash
# Normal (verification required)
"Сгенерируй сцену 0204"

# Batch mode (skip verification)
"Сгенерируй сцену 0204 --skip-verification"
```

**Safety**:
- Флаг работает только если blueprint version >= v3.0
- Автор получает отчёт после генерации с кратким содержанием того, что было сгенерировано
- Если auto-generated сцена fails validation → останов, требуется ручная проверка

**Use Case**: Когда автор хочет сгенерировать 5-10 сцен подряд за одну сессию (batch processing).

---

### Q6: Context Files for prose-writer (Minimal Context)
**Decision**: prose-writer получает ТОЛЬКО:
1. **Scene blueprint** (primary, required)
2. **Previous scene content** (для continuity, последние 300-500 слов)
3. **POV character sheet** (для этой сцены)
4. **World-bible excerpts** (только упомянутые в blueprint локации/механики)
5. **Verified plan** (утверждённый автором, если есть изменения от blueprint)

**НЕ передавать**:
- Другие scene blueprints
- Old versions (revised, v1, v2)
- Full plan-v3 (только relevant constraints)
- Unrelated character sheets
- Full world-bible

**Implementation**: generation-coordinator собирает minimal context package перед вызовом prose-writer.

---

### Q7: Retry Constraint Enhancement Aggressiveness
**Decision**: Current level из TECHNICAL_DESIGN_PART2.md достаточен (Attempt 1: normal, Attempt 2: warnings, Attempt 3: ALL CAPS + emojis + 5x repetition).

**Monitoring**: После первых 10 сцен проверить:
- Если success rate Attempt 1 < 70% → усилить constraints уже в Attempt 1
- Если success rate Attempt 3 < 95% → добавить Attempt 4 с ещё более агрессивными constraints

**Current approach is research-backed**: CoS research показывает что iterative constraint refinement эффективен. 3 попытки с усилением - balanced approach.

---

## Default Parameters

Также фиксируем параметры из roadmap:

### Timeouts
- blueprint-validator: 30 seconds
- verification-planner: 45 seconds
- prose-writer: 4 minutes
- fast-checker: 30 seconds
- Each validator: 5 minutes
- Total workflow: 10 minutes max

### Retry Limits
- prose-writer attempts: 3 max
- verification plan modifications: unlimited (warning after 5)

### Context Limits
- Blueprint: full file
- Previous scene: last 300-500 words
- Character sheet: full file
- World-bible excerpts: <2000 words total

### Storage
- Success drafts: `acts/act-[N]/chapters/chapter-[NN]/content/scene-[NNNN].md`
- Failed attempts: `workspace/failed-attempts/scene-[NNNN]/`
- Artifacts: `workspace/artifacts/scene-[NNNN]/`
- Logs: `workspace/logs/generation-coordinator/scene-[NNNN].log`

---

## Implementation Ready

Все открытые вопросы решены. Можно начинать Week 1 Day 1.

**Next**: Create agent files с промптами из TECHNICAL_DESIGN_PART2.md.

---

**Approved by**: User
**Date**: 2025-10-31
