# FEAT-0006: External AI Context Export

## Problem Statement

При генерации сцен пользователь хочет иметь возможность использовать внешние AI (Gemini, GPT, Claude API и др.) вместо локальной генерации, чтобы сравнивать результаты разных моделей или использовать модели с уникальными характеристиками.

## User Journey

### Starting Point
Пользователь находится в Step 3 Generation Workflow, Verification Plan утверждён.

### Step-by-Step Flow

```
1. Пользователь утверждает Verification Plan (нажимает Y)

2. Система показывает выбор:
   ┌─────────────────────────────────────────────────────┐
   │ ✅ Verification Plan approved                        │
   │                                                     │
   │ Choose generation method:                           │
   │ [G] Generate locally (Claude)                       │
   │ [E] Export for external AI                          │
   │ [C] Cancel                                          │
   └─────────────────────────────────────────────────────┘

3. Пользователь нажимает E (Export)

4. Система показывает настройки пакета:
   ┌─────────────────────────────────────────────────────┐
   │ 📦 Configure Export Package                         │
   │                                                     │
   │ Include in package:                                 │
   │ [x] Blueprint (required)                            │
   │ [x] Constraints                                     │
   │ [x] Style guide                                     │
   │ [x] Main prompt                                     │
   │ [ ] Character cards                                 │
   │ [ ] Previous scene(s)                               │
   │ [ ] World bible excerpts                            │
   │                                                     │
   │ [P]roceed | [A]ll | [M]inimal | [C]ancel           │
   └─────────────────────────────────────────────────────┘

5. Пользователь выбирает компоненты и нажимает P

6. Система создаёт пакет и показывает:
   ┌─────────────────────────────────────────────────────┐
   │ ✅ Export package created                           │
   │                                                     │
   │ 📁 Location:                                        │
   │ workspace/.../generation-scene-XXXX/external/       │
   │                                                     │
   │ 📄 Files:                                           │
   │ ├── 00-QUICK-START.md     (start here)             │
   │ ├── 01-MAIN-PROMPT.md     (copy to AI)             │
   │ ├── 02-constraints.json                            │
   │ ├── 03-blueprint.md                                │
   │ ├── 04-style-guide.md                              │
   │ └── output/               (put result here)        │
   │                                                     │
   │ 📋 Next steps:                                      │
   │ 1. Open 01-MAIN-PROMPT.md                          │
   │ 2. Copy content to your AI                         │
   │ 3. Get generated text                              │
   │ 4. Save as output/scene-XXXX-external.md           │
   │ 5. Return here and type "ready"                    │
   │                                                     │
   │ Type "ready" when result is in output/ folder      │
   └─────────────────────────────────────────────────────┘

7. Пользователь работает с внешним AI (вне системы)

8. Пользователь возвращается, копирует результат в output/, пишет "ready"

9. Система обнаруживает файл и запускает валидацию:
   ┌─────────────────────────────────────────────────────┐
   │ 📥 Found: scene-0101-external.md (2,847 words)     │
   │                                                     │
   │ Running validation (Step 5-6)...                   │
   │ ├── Fast compliance check...  ✅                    │
   │ └── Full validation...        🔄                    │
   └─────────────────────────────────────────────────────┘

10. Система показывает результаты валидации (как для локальной генерации)

11. Пользователь принимает или отклоняет результат
```

### End State
Сцена от внешнего AI валидирована и сохранена в `content/scene-XXXX.md`, workflow продолжается к Step 7 (Context Integration).

---

## Package Contents

### Required (always included)
| File | Description |
|------|-------------|
| `00-QUICK-START.md` | Instructions for the user |
| `01-MAIN-PROMPT.md` | Main generation prompt (copy to AI) |
| `02-constraints.json` | Hard constraints that MUST be met |
| `03-blueprint.md` | Scene blueprint |

### Optional (user selects)
| File | Description |
|------|-------------|
| `04-style-guide.md` | Prose style instructions |
| `05-character-cards.md` | Relevant character information |
| `06-previous-scenes.md` | Context from earlier scenes |
| `07-world-bible.md` | Relevant world-building info |
| `08-verification-plan.md` | Detailed verification checklist |

### Output
| File | Description |
|------|-------------|
| `output/scene-XXXX-external.md` | Generated scene (user creates) |
| `output/compliance.json` | Optional self-assessment by AI |

---

## Edge Cases & Behaviors

| Scenario | Expected Behavior |
|----------|-------------------|
| User types "ready" but no file in output/ | Show error: "No file found in output/. Please save your result as scene-XXXX-external.md" |
| Multiple files in output/ | Ask user to choose which one to use |
| File exists but empty | Show error: "File is empty. Please add generated content." |
| User cancels after export | Workflow state preserved, can resume later with `/generation-state resume` |
| User wants to re-export with different options | Allow `/export-context` command to regenerate package |
| Validation fails | Same flow as local generation: show issues, allow retry or manual fix |
| User generates locally AFTER export | Export folder preserved, user can choose which result to use |

---

## Definition of Done (DoD)

### Must Have
- [ ] After Step 3 approval, user sees [G]/[E]/[C] choice
- [ ] Export creates structured package in `generation-runs/.../external/`
- [ ] Package includes configurable components
- [ ] `00-QUICK-START.md` has clear step-by-step instructions
- [ ] `01-MAIN-PROMPT.md` is self-contained prompt for external AI
- [ ] System detects file in output/ when user types "ready"
- [ ] Imported result goes through full validation (Step 5-6)
- [ ] Workflow state tracks "waiting_for_external" status

### Polish
- [ ] Package includes word count target in prompt
- [ ] Constraints are formatted for easy copy-paste
- [ ] QUICK-START includes troubleshooting tips
- [ ] System suggests filename format if user uses wrong name

---

## Visual Description

### Before (current)
After Verification Plan approval:
```
✅ Verification Plan approved
Proceeding to generation...
```

### After (with feature)
After Verification Plan approval:
```
✅ Verification Plan approved

Choose generation method:
[G] Generate locally (Claude)
[E] Export for external AI
[C] Cancel

>
```

---

## Technical Notes

### Skill Structure
```
.claude/skills/external-ai-export/
├── SKILL.md              # Skill definition
├── templates/
│   ├── 00-quick-start.md
│   ├── 01-main-prompt.md
│   └── ...
└── examples/
    └── gemini-package/   # Reference implementation
```

### Integration Points
- **Generation Coordinator**: Add [E]xport option after Step 3
- **Workflow State**: New status `waiting_for_external`
- **Validation Pipeline**: Reuse Step 5-6 for external results

### State Flow
```
Step 3 (approved)
    ↓
[User chooses E]
    ↓
export_package_created
    ↓
waiting_for_external
    ↓
[User types "ready"]
    ↓
Step 5 (Fast Check)
    ↓
Step 6 (Full Validation)
    ↓
Step 7 (Final Output)
```

---

## Open Questions

1. **Multiple attempts**: Should we support multiple external AI attempts (like attempt1, attempt2 for local)?
   - **Proposed**: Yes, allow `scene-XXXX-external-v2.md` etc.

2. **Mixing local and external**: Can user generate locally AND externally for same scene?
   - **Proposed**: Yes, both stored in workflow, user chooses which to accept

3. **Re-export**: If user already exported, should we warn about overwriting?
   - **Proposed**: Yes, ask "Package already exists. [O]verwrite | [K]eep both | [C]ancel"

---

## Ready for Technical Design: ✅ Yes

### Handoff Summary
- **Trigger**: After Step 3 verification plan approval
- **User choice**: [G]enerate | [E]xport | [C]ancel
- **Package**: Configurable (minimal to full context)
- **Format**: Universal (works with any AI)
- **Return**: User manually copies file to output/
- **Validation**: Full Step 5-6 pipeline
- **Integration**: Uses existing generation-coordinator, adds new state

---

## References

- Existing implementation: `workspace/.../gemini/` package from Scene 0101
- Generation workflow: `.workflows/generation.md`
- Skill template: `.claude/skills/` examples
