# AI-Assisted Writing System for Sci-Fi Novel

Система автоматизированного создания литературного текста с использованием специализированных ИИ-агентов и Model Context Protocol для научно-фантастического романа

---

## КРИТИЧНЫЕ ПРАВИЛА (ЧИТАЙ ПЕРВЫМ!)

### File Naming Standards - СТРОГО ОБЯЗАТЕЛЬНО

**✅ ВСЕГДА используй:**
```
acts/act-{N}/chapters/chapter-{NN}/plan.md
acts/act-{N}/chapters/chapter-{NN}/scenes/scene-{NNNN}-blueprint.md
acts/act-{N}/chapters/chapter-{NN}/content/scene-{NNNN}.md
```

**❌ НИКОГДА не создавай:**
```
plan-v2.md, plan-v3.md, plan-revised.md          ← WRONG
scene-X-blueprint-v2.md, scene-X-revised.md      ← WRONG
```

**Если нашёл несколько файлов (например, plan.md И plan-v2.md):**
→ **STOP IMMEDIATELY**
→ ERROR: "Multiple files detected. Move old versions to backups/ subdirectory"
→ DO NOT proceed until only ONE canonical file exists

**Versioning Method:**
- Старые версии → `backups/plan-2025-11-02-14-30.md` (timestamped)
- Текущая версия → ВСЕГДА стандартное имя без суффиксов

---

### Session Management - КРИТИЧНО!

**⚠️ ОБЯЗАТЕЛЬНАЯ ПРОВЕРКА ПЕРЕД ЛЮБЫМИ ОПЕРАЦИЯМИ WRITE/EDIT:**

**Шаг 1: ВСЕГДА проверяй активную сессию ПЕРЕД записью файлов:**
```bash
# Проверить активную сессию
ls workspace/session.lock && cat workspace/session.lock
```

**Шаг 2: Если сессия НЕ активна:**
```
❌ STOP IMMEDIATELY!
❌ НЕ создавай файлы напрямую в acts/, context/, или других директориях!
❌ НЕ используй Write/Edit без активной сессии!

✅ ПРАВИЛЬНЫЕ действия:
1. Спроси пользователя создать сессию:
   "Нужно создать сессию для изоляции изменений. Создать сессию?"
2. После создания сессии - продолжай работу
```

**Шаг 3: С активной сессией - все файлы идут в сессию:**
```
✅ Правильно (с сессией "revision-act1"):
workspace/sessions/revision-act1/acts/act-1/strategic-plan.md
workspace/sessions/revision-act1/acts/act-1/chapters/chapter-01/plan.md

❌ НЕПРАВИЛЬНО (напрямую в глобальные файлы):
acts/act-1/strategic-plan.md           ← БЕЗ СЕССИИ = ОШИБКА!
acts/act-1/chapters/chapter-01/plan.md ← БЕЗ СЕССИИ = ОШИБКА!
```

**Почему это критично:**
- **Изоляция**: Изменения должны быть в сессии до коммита
- **Откат**: Без сессии невозможно откатить изменения
- **Copy-on-Write**: Сессии используют CoW для эффективности
- **Hooks блокируют**: session_guard_hook.py должен блокировать Write/Edit без сессии

**Если hook НЕ сработал:**
→ Это критическая ошибка системы
→ НЕ обходи проверку вручную
→ Сообщи пользователю о сбое hook

**Команды управления сессиями:**
```bash
# Создать сессию
mcp__session_management__create_session(name="...", description="...")

# Проверить активную
mcp__session_management__get_active_session()

# Закоммитить (перенести в глобальные файлы)
mcp__session_management__commit_session(name="...")

# Отменить
mcp__session_management__cancel_session(name="...")
```

**КРИТИЧНО: Без активной сессии - НЕ пиши файлы!**

---

## Workflow Router

**Когда пользователь запрашивает генерацию сцены:**
→ См. `.workflows/generation.md` (полная документация)
→ Используй агент `generation-coordinator` (оркестратор)

**Когда пользователь запрашивает планирование:**
→ См. `.workflows/planning.md` (полная документация)
→ Используй команду `/plan-story`

**Когда пользователь проверяет consistency:**
→ Используй команду `/check-consistency`

**Когда пользователь управляет workflow state:**
→ Используй команды `/generation-state` (status, resume, cancel, list)

---

## Generation Workflow - ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА

### Trigger Detection
```
User: "Сгенерируй сцену 0204"
User: "Generate scene 0204"
User: "Создай сцену {ID}"
```

→ **ВСЕГДА используй `generation-coordinator`** (НЕ пытайся генерировать напрямую!)

### Процесс (7 шагов - НЕ пропускай!)

1. **File Check**: Проверь существование blueprint
2. **Blueprint Validation**: Автоматическая проверка корректности
3. **Verification Plan**: **ОБЯЗАТЕЛЬНО покажи план пользователю и ЖДИ одобрения**
4. **Generation**: Создание текста (до 3 попыток с auto-retry)
5. **Fast Compliance Check**: Быстрая поверхностная проверка (<30s)
6. **Full Validation**: Глубокая валидация (7 валидаторов параллельно)
7. **Final Output**: Финальный отчёт

**Recovery**: Если workflow упал - используй `/generation-state resume {scene_id}` для продолжения с места падения

### КРИТИЧНЫЕ Моменты

**❌ НИКОГДА:**
- НЕ генерируй без blueprint (Step 1 проверяет это)
- НЕ пропускай Step 3 (Verification Plan - human approval REQUIRED)
- НЕ показывай полный текст в чате (сохрани в файл, верни только путь)
- НЕ используй файлы с version suffixes

**✅ ВСЕГДА:**
- Используй `generation-coordinator` для оркестрации
- Жди одобрения пользователя перед генерацией (Step 3)
- Сохраняй результат в файл `acts/.../content/scene-{ID}.md`
- Возвращай краткий отчёт (не полный текст!)

### Детальная Документация
См. `.workflows/generation.md` для:
- Полного описания всех 7 шагов
- Спецификаций агентов
- Error handling
- Context management
- Примеры взаимодействия

---

## Planning Workflow - ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА

### Trigger Detection
```
User: "/plan-story"
```

→ Интерактивное планирование на 4 уровнях:
- Strategic (весь акт)
- Storylines (сюжетные линии персонажей)
- Chapters (планы глав)
- Scenes (blueprints для генерации)

### Детальная Документация
См. `.workflows/planning.md`

---

## Архитектура системы

```
PLANNING WORKFLOW          GENERATION WORKFLOW
    ↓                           ↓
Планирование               Генерация текста
    ↓                           ↓
Blueprints ─────────────→  Финальные сцены
```

---

## Структура проекта

```
/project-root
├── CLAUDE.md                   # Этот файл (router + критичные правила)
├── .workflows/                  # Детальная документация
│   ├── planning.md             # Planning Workflow (актуальная версия)
│   ├── generation.md           # Generation Workflow (актуальная версия)
│   ├── integration.md          # Связь между workflows
│   ├── agents-reference.md     # Справочник всех агентов
│   └── prose-style-guide.md    # Руководство по стилям прозы
│
├── .claude/agents/             # Агенты Claude Code
│   ├── planning/               # Агенты планирования
│   ├── generation/             # Агенты генерации
│   └── shared/                 # Общие агенты (валидаторы)
│
├── context/                    # Контекст мира
│   ├── characters/             # Персонажи (timeline, knowledge)
│   ├── world-bible/            # Библия мира
│   ├── canon-levels/           # Уровни канона (0-4)
│   └── plot-graph/             # Сюжетный граф
│
├── acts/                       # Структура книги
│   └── act-1/
│       ├── strategic-plan.md   # План акта
│       ├── storylines/         # Сюжетные линии
│       └── chapters/
│           └── chapter-01/
│               ├── plan.md             ← Текущая версия (БЕЗ суффиксов!)
│               ├── scenes/
│               │   └── scene-0101-blueprint.md  ← Текущая версия
│               ├── content/
│               │   └── scene-0101.md           ← Готовый текст
│               └── backups/            ← Старые версии (timestamped)
│                   ├── plan-2025-10-27-14-30.md
│                   └── scene-0101-blueprint-2025-10-29.md
│
└── workspace/                  # Временные файлы
    ├── artifacts/              # Промежуточные выходы агентов
    ├── logs/                   # Логи выполнения
    └── generation-runs/        # Артефакты генерации (по session)
```

---

## Ключевые Концепции

### Artifact System
Агенты НЕ передают большие данные в промптах. Всё через файлы:
- Агент пишет результат → файл
- Передаёт следующему агенту → путь к файлу
- Предотвращает context overflow и потерю информации

**КРИТИЧНО:**
- Передача контекста >100 строк ТОЛЬКО через файлы
- Если агент генерирует текст в файл → читай файл, НИКОГДА не проси вернуть текст
- Экономь контекстное окно!

**Context Management Best Practices:**
- Держи контекст <60% лимита для agent thinking space
- Используй `/compact` между фазами, `/clear` перед новым workflow
- Агенты должны быть <3k tokens (используй external references вместо inline content)
- Сохраняй output в файлы, возвращай только metadata

### Isolated Contexts
Каждый агент работает в своём изолированном контексте. Получает только необходимое, возвращает только результат.

### Human-in-the-Loop
Критические решения ВСЕГДА за человеком:
- Утверждение verification plan перед генерацией (Step 3)
- Утверждение новых элементов мира
- Определение уровней канона
- Разрешение противоречий
- Финальное одобрение текста

### Parallel Execution
Независимые задачи выполняются параллельно:
- Planning: проработка деталей (world, characters, dialogue)
- Generation: валидация (7 агентов параллельно в Step 6)
- Integration: обновление контекстов (4 агента параллельно)

### Observability
Полное логирование для отладки и оптимизации:
- Каждый агент логирует входы/выходы
- Трассировка выполнения
- Метрики производительности
- Логи в `workspace/logs/{agent-name}/`

---

## Принципы работы

### Do's ✅
- **Single Responsibility**: Один агент = одна задача
- **Use Artifacts**: Передавайте файлы, не данные
- **Human Oversight**: Критические решения за человеком
- **Single Source of Truth**: ОДИН файл с каноническим именем
- **Test Systematically**: Проверяйте каждый уровень
- **Log Everything**: Observability критична
- **Manage Context**: Держи <60%, используй /compact, /clear

### Don'ts ❌
- **Don't Create Versions**: НИКАКИХ файлов с суффиксами -v2, -revised, -final
- **Don't Over-complicate**: Не создавайте лишних агентов
- **Don't Share State**: Агенты общаются через файлы
- **Don't Ignore Limits**: Мониторьте размер контекста
- **Don't Skip Validation**: Всегда проверяйте изменения
- **Don't Skip Human Approval**: Step 3 ОБЯЗАТЕЛЕН
- **Don't Return Full Text**: Save to file, return metadata only
- **Don't Embed Guides**: Reference external docs, не дублируй

---

## Основные Команды

### Планирование
```bash
/plan-story          # Интерактивное планирование сюжета
/storyline           # Управление сюжетными линиями персонажей
/check-consistency   # Проверка согласованности после изменений
```

### Генерация
```
"Сгенерируй сцену 0204"
"Generate scene 0204"
```
→ Автоматически использует generation-coordinator (7-step workflow)

### Workflow State Management
```bash
/generation-state status [scene_id]    # Проверить прогресс
/generation-state resume <scene_id>    # Продолжить после падения
/generation-state cancel <scene_id>    # Отменить workflow
/generation-state list [--failed]      # Список всех генераций
```

### Context Management
```bash
/compact    # Сжать историю контекста
/clear      # Очистить контекст перед новым workflow
```

---

## Документация

### Основные документы (актуальные версии)
- [`.workflows/generation.md`](.workflows/generation.md) - Generation Workflow (полная документация)
- [`.workflows/planning.md`](.workflows/planning.md) - Planning Workflow
- [`.workflows/integration.md`](.workflows/integration.md) - Связь между workflows
- [`.workflows/agents-reference.md`](.workflows/agents-reference.md) - Справочник всех агентов
- [`.workflows/prose-style-guide.md`](.workflows/prose-style-guide.md) - Стили написания прозы

### Дополнительные материалы
- `context/world-bible/README.md` - Структура библии мира
- `context/canon-levels/README.md` - Система уровней канона
- `context/characters/README.md` - Формат карточек персонажей
- `features/` - Технические спецификации фич

---

## Техническая информация

### Требования
- Claude Code с поддержкой sub-agents
- MCP (Model Context Protocol)
- Доступ к файловой системе

### Производительность (ориентировочно)
- Planning: ~2-5 минут на сцену
- Generation: ~5-8 минут на сцену (включая human approval ~30 сек)
- Full cycle (planning + generation): ~7-13 минут

### Масштабирование
- До 6 агентов параллельно в Planning (фаза 2-3)
- До 7 агентов параллельно в Generation (Step 6: валидация)
- До 4 агентов параллельно в Integration

---

## Отладка и Логирование

### Логи
Все логи сохраняются в `workspace/logs/{agent-name}/`

### Трассировка
Полная трассировка выполнения в `workspace/generation-runs/{timestamp}-scene-{ID}/`

### Артефакты
Промежуточные результаты в `workspace/artifacts/`

---

## Contributing

При добавлении новых агентов:
1. Создайте агента в `.claude/agents/`
2. Добавьте описание в `.workflows/agents-reference.md`
3. Обновите соответствующий workflow (`.workflows/generation.md` или `.workflows/planning.md`)
4. НЕ ОБНОВЛЯЙТЕ CLAUDE.md (если не меняются критичные правила)

При обновлении workflows:
1. Обновите `.workflows/{workflow}.md` (актуальная версия)
2. CLAUDE.md обновляется ТОЛЬКО если меняются критичные правила

---

## License

Proprietary - для личного использования в работе над романом

---

**Last Updated**: 2025
**Основано на**: Anthropic Claude Code best practices, multi-agent orchestration patterns

- Для решения сложных задач, планирования, придумывания и ПЕРЕД отправкой пользователю для принятия решения ИТОГОВОГО РЕШЕНИЯ используй hat-thinks (sequentialthinking tool). ВСЕГДА!
- Учти что sequentialthinking хуже тебя разбирается в вопросах, но с разных сторон. Поэтому ищи у него помощи в многогранной проработке, но дообдумывай решения самостоятельно
- Итоговая генерация текста всегда на русском языке, промпты и другие вещи можешь делать на английском, но все термины из книги должны быть на русском как и её текст
- Ты не должен использовать hat-thinks (sequentialthinking) для генерации сложных текстов, но ты ДОЛЖЕН проерять их через него, отдавать ему на оценку, и САМОСТОЯТЕЛЬНО исправлять по рекомендациям
- ALWAYS FIRST read files in current session folder, otherwise in global
- HAT-THINKS RULE: Планирование это твой удел, hat-thinks нужен только для поиска потенциальных упущений. Всегда планируй всё сам, с hat-thinks только консультируйся. Проси найти его узкие места, но всегда четко формулируй вопросы и предоставляй необходимый контекст