# FEAT-0005: Context Integration After Generation

**Status**: ✅ Implementation Complete (v1.0)
**Created**: 2025-11-28
**Author**: Six Hats Analysis (White, Black, Yellow, Green)
**Technical Design**: [technical-design.md](./technical-design.md)
**Implementation**: 2025-11-28

---

## Problem Statement

После реализации FEAT-0003 (Hierarchical Planning) осталась нереализованной интеграционная часть workflow из `integration.md`. Generation Workflow заканчивается на Step 7 (Final Output), но **контексты НЕ обновляются автоматически** после генерации сцены.

Это приводит к:
- Разрыву цикла Planning ↔ Generation
- Ручному отслеживанию знаний персонажей
- Риску continuity errors в последующих сценах
- Устареванию storylines

---

## User Journey

### Starting Point
Пользователь завершил генерацию сцены 0204 (Step 7: Final Output). Видит:
```
✅ СЦЕНА 0204 ГОТОВА
📄 File: acts/act-1/chapters/chapter-02/content/scene-0204.md
```

### Current State (Problem)
После этого:
- Character knowledge timelines **НЕ обновляются**
- Storylines **НЕ отмечают прогресс**
- При планировании сцены 0205 система **не знает** что персонажи узнали в 0204

### Desired State (Solution)
После Step 7 автоматически запускается **Step 8: Context Synthesis**:

1. **Система анализирует** сгенерированную сцену
2. **Извлекает изменения** (knowledge, emotions, relationships)
3. **Показывает diff** пользователю:
   ```
   ALEXA WRIGHT - Knowledge Update:
   + "Узнала о смерти дочери Реджинальда" (Сцена 0204)
   + "Видела работу системы компенсации" (Сцена 0204)

   EMOTIONAL STATE:
   БЫЛО: "Холодна и расчётлива (маска)"
   СТАНЕТ: "Маска с трещинами сочувствия"

   [✅ Approve All] [⚙️ Edit] [❌ Skip]
   ```
4. **Пользователь подтверждает** (или редактирует)
5. **Контексты обновляются**
6. **При планировании 0205** система знает актуальное состояние персонажей

### End State
Пользователь видит:
```
✅ СЦЕНА 0204 ГОТОВА
✅ КОНТЕКСТЫ ОБНОВЛЕНЫ
   - Alexa: +2 knowledge items, emotional shift
   - Reginald: +1 knowledge item

🎯 Next: Сгенерировать сцену 0205?
```

---

## Edge Cases & Behaviors

| Scenario | Expected Behavior |
|----------|-------------------|
| Пользователь отклоняет все обновления | Контексты не меняются, workflow завершается |
| ИИ извлёк неверную информацию | Пользователь редактирует перед подтверждением |
| Сцена без новых знаний персонажей | Система показывает "No significant changes detected" |
| Конфликт с existing knowledge | Warning: "Alexa уже знала X в сцене 0102" |
| Новый элемент мира (world-bible) | CRITICAL: Требует canon level assignment |
| Race condition (2 генерации параллельно) | Queue updates, apply sequentially |
| Ошибка во время записи | Rollback to snapshot, show error |

---

## Definition of Done (DoD)

### Must Have
- [ ] Step 8 добавлен в Generation Workflow после Step 7
- [ ] context-extractor agent анализирует сцену и извлекает changes
- [ ] Diff preview показывает пользователю proposed changes
- [ ] Character knowledge-timeline файлы создаются/обновляются
- [ ] Human approval required для CRITICAL changes (new characters, world elements)
- [ ] Routine changes (timestamps, interaction logs) применяются автоматически
- [ ] Snapshot создаётся перед изменениями (rollback capability)
- [ ] Integration report показывает что было обновлено

### Should Have
- [ ] Tiered classification (CRITICAL / SIGNIFICANT / ROUTINE)
- [ ] Confidence scores для extracted information
- [ ] Storyline progress tracking updates
- [ ] Health check после применения (detect contradictions)

### Nice to Have
- [ ] Batch mode для обработки нескольких сцен
- [ ] Interactive Explorer mode для исследования персонажей
- [ ] Learning user preferences (auto-approve high-confidence routine)

---

## Technical Scope

### New Files to Create
```
context/characters/{character-name}/
└── knowledge-timeline.md    # НОВЫЙ - хронология знаний персонажа

.claude/agents/generation/
├── context-extractor.md     # НОВЫЙ - извлечение информации из сцены
└── context-integrator.md    # НОВЫЙ - применение обновлений
```

### Files to Modify
```
.workflows/generation.md     # Добавить Step 8
ARCHITECTURE.md              # Обновить Generation Workflow diagram
```

### Knowledge Timeline Format
```markdown
# Knowledge Timeline: [Character Name]

## До Главы 1
**Знает:**
- [факт 1]
- [факт 2]

**Не знает:**
- [скрытая информация 1]

## Глава 1

### Сцена 0101
**Узнаёт:**
- [новое знание]

### Сцена 0102
**Узнаёт:**
- [новое знание]
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ИИ неправильно извлекает информацию | Human review для SIGNIFICANT+ changes |
| Hallucination в контексте | Confidence scores + evidence quotes |
| Silent cascading failures | Health check + contradiction detection |
| Race conditions | Sequential queue processing |
| World Bible modified without approval | ALWAYS require human approval for world elements |
| Увеличение времени на 30-50% | Tiered automation (80% routine = auto) |

---

## Recommended Approach

**Step 8: Context Synthesis** (5 phases, ~2-3 min):

```
Phase 1: Auto-Scan (30s)
├─ context-extractor анализирует сцену
├─ Извлекает changes с confidence scores
└─ Классифицирует: CRITICAL / SIGNIFICANT / ROUTINE

Phase 2: Categorized Preview (instant)
├─ 🔴 CRITICAL: Requires approval (new chars, world elements)
├─ 🟡 SIGNIFICANT: AI suggests, user confirms (emotions, knowledge)
└─ 🟢 ROUTINE: Auto-apply with notification (timestamps, logs)

Phase 3: Interactive Confirmation (30-60s)
├─ User approves/rejects/edits each category
└─ CRITICAL requires explicit decision

Phase 4: Health Check (10s)
├─ Check for contradictions with previous scenes
└─ Warn if conflicts detected

Phase 5: Integration Report (instant)
├─ Summary of applied changes
├─ Visual timeline update
└─ Suggestions for next scene
```

---

## Out of Scope (Future Features)

- Automatic World Bible updates (always manual)
- Multi-scene batch processing (v2)
- AI learning user preferences (v2)
- Automatic storyline arc completion detection (v2)

---

## Design Decisions (Resolved)

1. **Где хранить knowledge-timeline?**
   - ✅ **РЕШЕНО**: `context/characters/{name}/knowledge-timeline.md` (отдельный файл)

2. **Как часто запускать Step 8?**
   - ✅ **РЕШЕНО**: Опционально - предлагать после Step 7, пользователь может пропустить
   - UX: "Обновить контексты? [Y/n/skip]"

3. **Интеграция с FEAT-0003 (Hierarchical Planning)?**
   - TBD в техническом дизайне

---

## Success Metrics

- **Context accuracy**: >95% extracted information correct (validated by user)
- **User approval rate**: >80% of SIGNIFICANT changes approved without edit
- **Time overhead**: <3 min per scene (vs 10+ min manual tracking)
- **Continuity errors**: Reduction in "character knows X but shouldn't" issues

---

## Related Documents

- [Integration Guide](../../.workflows/integration.md) - Original specification
- [Generation Workflow](../../.workflows/generation.md) - Current 7-step process
- [FEAT-0003 Implementation](../FEAT-0003-hierarchical-planning/) - Hierarchical Planning

---

**Ready for Technical Design:** Yes (after questions resolved)
