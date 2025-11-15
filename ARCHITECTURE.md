# System Architecture

Архитектурный обзор AI-Assisted Writing System для создания научно-фантастического романа.

## 🏗️ Общая архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Interface                          │
│                         (Claude Code)                            │
└────────────────┬────────────────────────────────┬────────────────┘
                 │                                │
                 ▼                                ▼
    ┌────────────────────────┐      ┌────────────────────────┐
    │    Planning Workflow    │      │  Generation Workflow   │
    │   (5 phases, human      │      │  (7 steps, auto-retry, │
    │    approval Phase 2)    │      │   human approval Step 3)│
    └───────────┬─────────────┘      └────────────┬───────────┘
                │                                  │
                ▼                                  ▼
    ┌───────────────────────────────────────────────────────┐
    │           Workflow Orchestration Layer                │
    │  - Sequential enforcement (validate_prerequisites)    │
    │  - State persistence (JSON files)                     │
    │  - Human-in-the-loop checkpoints                      │
    │  - Resume/recovery capability                         │
    └───────────┬───────────────────────────────────────────┘
                │
                ▼
    ┌───────────────────────────────────────────────────────┐
    │              MCP Servers Layer                        │
    │  - session_management_mcp.py (CoW sessions)           │
    │  - workflow_orchestration_mcp.py (workflow state)     │
    │  - generation_state_mcp.py (legacy, deprecated)       │
    └───────────┬───────────────────────────────────────────┘
                │
                ▼
    ┌───────────────────────────────────────────────────────┐
    │              Agent Execution Layer                    │
    │  - 40+ specialized agents                             │
    │  - Isolated contexts                                  │
    │  - Artifact-based communication                       │
    │  - Parallel execution support                         │
    └───────────┬───────────────────────────────────────────┘
                │
                ▼
    ┌───────────────────────────────────────────────────────┐
    │              Data & Context Layer                     │
    │  - World Bible (canon levels 0-4)                     │
    │  - Character timelines & knowledge                    │
    │  - Plot graph & storylines                            │
    │  - Generated content                                  │
    └───────────────────────────────────────────────────────┘
```

## 🔄 Workflow Orchestration

### Planning Workflow (5 фаз)

```
Phase 0: Initialize
    ↓
Phase 1: Exploration (анализ контекста)
    ↓
Phase 2: Scenarios (3-5 вариантов) → **HUMAN APPROVAL**
    ↓
Phase 3: Path Planning (события и сцены)
    ↓
Phase 4: Detailing (детализация сцен)
    ↓
Phase 5: Integration (сюжетные линии)
    ↓
Output: Blueprint (scene-XXXX-blueprint.md)
```

### Generation Workflow (7 шагов)

```
Step 0A: Resume Detection (проверка failed workflows)
Step 0B: Initialize State
    ↓
Step 1: File Check (blueprint exists?)
    ↓
Step 2: Blueprint Validation
    ↓
Step 3: Verification Plan → **HUMAN APPROVAL**
    ↓
Step 4: Generation (до 3 попыток с retry)
    ↓
Step 5: Fast Compliance Check (<30s)
    ↓
Step 6: Full Validation (7 validators || )
    ↓
Step 7: Final Output
    ↓
Output: Scene (scene-XXXX.md)
```

### Sequential Enforcement Pattern

Каждый step/phase проверяется перед выполнением:

```python
# BEFORE STEP N
result = validate_prerequisites(workflow_id, step=N)
if not result["can_start_step"]:
    return error(result["blocking_issues"])

# START STEP N
update_workflow_state(workflow_id, step=N, status="in_progress")

# [WORK]

# ON SUCCESS
update_workflow_state(
    workflow_id,
    step=N,
    status="completed",
    artifacts={...}
)
```

## 🏛️ Hierarchical Planning Architecture (FEAT-0003)

### Трёхуровневая иерархия

```
Act (Акт)
  ↓
Chapter (Глава)
  ↓
Scene (Сцена)
```

**Ключевые принципы**:
- **Parent-Child Validation**: нельзя планировать child без approved parent
- **Cascade Invalidation**: изменение parent автоматически инвалидирует всех descendants
- **Version Tracking**: SHA-256 хэши для отслеживания изменений
- **Status Flow**: draft → approved → requires-revalidation → invalid

### Entity Status Flow

```
draft                    (создан, но не утверждён)
  ↓ approve_entity()
approved                 (утверждён, можно планировать children)
  ↓ parent version changed
requires-revalidation    (требует пересмотра после изменения parent)
  ↓ manual mark
invalid                  (помечен как недействительный)
```

### Hierarchical Commands

```bash
# Planning (top-down)
/plan-act 1                    # План всего акта (root level)
/plan-chapter 1 --act 1        # План главы (requires approved act)
/plan-scene 0101 --chapter 1   # Blueprint сцены (requires approved chapter)

# Approval
/approve-plan act-1            # Утвердить акт
/approve-plan chapter-01       # Утвердить главу (parent must be approved)
/approve-plan scene-0101       # Утвердить сцену

# Revalidation
/revalidate-scene 0101         # Интерактивная ревалидация
/revalidate-all --act 1        # Batch ревалидация

# Version Management
/list-versions scene scene-0101      # История версий
/restore-version scene scene-0101 5  # Восстановить версию
/diff-version 5 6                    # Сравнить версии

# Utilities
/rebuild-state                 # Восстановить состояние из файлов
/show-hierarchy --act 1        # Визуализация иерархии
```

### State Storage

**SQLite Database** (`workspace/planning-state.db`):
```sql
planning_entities (
    entity_type, entity_id (PK),
    status, version_hash, previous_version_hash,
    file_path, parent_id, parent_version_hash,
    invalidation_reason, invalidated_at,
    created_at, updated_at, metadata
)

planning_entity_backups (
    backup_id (PK), entity_type, entity_id,
    version_hash, backup_file_path,
    backed_up_at, reason
)
```

**JSON Fallback** (`workspace/planning-state/*.json`):
- Graceful degradation если SQLite недоступен
- Human-readable backup
- One file per entity

### Hook Pipeline

```
File Write/Edit Operation (planning file)
    ↓
[PreToolUse] hierarchy_validation_hook
    → Blocks if parent not approved
    ↓
Operation Executes
    ↓
[PostToolUse] state_sync_hook
    → Auto-syncs file → MCP state
    → Calculates version hash
    ↓
[PostToolUse] consistency_check_hook
    → Warns about parent version mismatch (non-blocking)
    ↓
[PostToolUse] invalidation_cascade_hook
    → Detects parent version change
    → Marks all descendants requires-revalidation
```

**Hook Execution Order**: validation → sync → consistency → cascade

### Cascade Invalidation Example

```
User edits act-1/strategic-plan.md (version changes)
    ↓
invalidation_cascade_hook detects version change
    ↓
Marks all descendants requires-revalidation:
  - chapter-01 (status: approved → requires-revalidation)
  - chapter-02 (status: approved → requires-revalidation)
    ↓
  - scene-0101 (cascades through chapter-01)
  - scene-0102
  - scene-0201 (cascades through chapter-02)
    ↓
User runs /revalidate-all --act 1
    ↓
Reviews each entity, decides:
  - Keep & approve (no changes needed)
  - Edit blueprint
  - Regenerate (creates backup first)
```

### Backup System

**Automatic Backups**:
- **Regeneration**: Before regenerating plan
- **Restore**: Before restoring old version

**Manual Backups**:
```bash
create_backup(entity_type='scene', entity_id='scene-0101', reason='manual')
```

**Backup Naming**:
```
acts/act-1/backups/
  ├── strategic-plan-2025-11-15-14-30-45.md
  └── strategic-plan-2025-11-10-09-15-20.md

acts/act-1/chapters/chapter-01/backups/
  ├── plan-2025-11-14-16-20-10.md
  └── plan-2025-11-12-11-45-30.md
```

### Recovery & Utilities

**Database Corruption**:
```bash
/rebuild-state --dry-run   # Preview rebuild
/rebuild-state             # Rebuild from files (10-30s)
```

**Lost Planning State**:
1. Check Git history: `git log --all --full-history -- "workspace/planning-state/*"`
2. Restore from Git if available
3. Otherwise: `/rebuild-state` reconstructs from files

**Hierarchy Visualization**:
```bash
/show-hierarchy --act 1
```
Output:
```
act-1 [approved] ✓
├── chapter-01 [approved] ✓
│   ├── scene-0101 [approved] ✓
│   ├── scene-0102 [requires-revalidation] ⚠️
│   └── scene-0103 [draft] 📝
└── chapter-02 [draft] 📝
    └── scene-0201 [draft] 📝

Summary: 3/5 approved, 1 requires revalidation, 2 draft
```

## 🎯 Key Design Patterns

### 1. Copy-on-Write Sessions

**Проблема**: Необходимость безопасного экспериментирования без риска потери данных.

**Решение**: Сессии с CoW - файлы копируются только при изменении.

```
Global Files                    Session Files
    ↓                               ↓
scene-0101.md       ───read───→  [not in session]
    │                               │
    │                          [modify]
    │                               ↓
    │                         CoW triggered
    │                               ↓
    │                    workspace/sessions/test/
    │                        scene-0101.md (copy)
    │
[commit_session]
    ↓
Updated scene-0101.md
```

**Преимущества**:
- Zero-cost для read-only операций
- Полная изоляция изменений
- Atomic commit/rollback
- Минимальное использование дискового пространства

### 2. Artifact-Based Communication

**Проблема**: Context window overflow при передаче больших данных между агентами.

**Решение**: Агенты обмениваются путями к файлам, а не содержимым.

```
Agent A                          Agent B
   ↓                                ↓
Generate plan            Read plan from file
   ↓                                ↓
Save to artifact/         Use artifact path
plan.md                          ↓
   ↓                        Process & save
Return path              artifact/result.md
   ↓                                ↓
   └────────── path ────────────────┘
```

**Правила**:
- Данные >100 строк → только через файлы
- Агенты возвращают metadata, не содержимое
- Держать context <60% лимита

### 3. Human-in-the-Loop

**Проблема**: Необходимость контроля критических решений.

**Решение**: Обязательные checkpoints с ожиданием одобрения.

```
Planning Phase 2: Scenarios
    ↓
Generate 3-5 variants
    ↓
update_workflow_state(status="waiting_approval")
    ↓
Show variants to user
    ↓
[WAIT for user input]
    ↓
approve_step(selected_variant="A")
    ↓
Continue with variant A
```

**Checkpoints**:
- Planning Phase 2: выбор сценария
- Generation Step 3: verification plan

### 4. State Persistence & Recovery

**Проблема**: Сбои сети, timeout, crashes прерывают длительные workflows.

**Решение**: Полное сохранение состояния в JSON с auto-resume.

```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "workflow_type": "generation",
  "status": "failed",
  "current_step": 4,
  "steps": [
    {"step": 1, "status": "completed", ...},
    {"step": 2, "status": "completed", ...},
    {"step": 3, "status": "completed", ...},
    {"step": 4, "status": "failed", "error": "timeout"}
  ]
}
```

**Recovery**:
```
User: /generation-state resume 0204
System: Продолжаю с Step 4 (3 steps skipped)
```

## 🧩 Component Architecture

### MCP Servers

**session_management_mcp.py** (CRITICAL)
- Управление CoW сессиями
- Путевое разрешение (session → global fallback)
- Commit/cancel операции
- Human retry tracking

**workflow_orchestration_mcp.py** (CORE)
- Управление состоянием workflows
- Sequential enforcement
- Human approval flow
- Resume/cancel workflows

**generation_state_mcp.py** (FEAT-0002 + FEAT-0003)
- **Scene Generation State** (FEAT-0002):
  - Generation workflow tracking
  - Resume failed workflows
  - Step-by-step progress monitoring
- **Hierarchical Planning State** (FEAT-0003):
  - 10 MCP tools для управления состоянием планирования
  - Entity state tracking (act/chapter/scene)
  - Hierarchy queries & cascade invalidation
  - Version management & backup system
  - Approval workflow

**MCP Tools (Planning State)**:
- `get_entity_state`, `update_entity_state` - CRUD operations
- `get_hierarchy_tree`, `get_children_status` - Hierarchy queries
- `cascade_invalidate`, `approve_entity` - State transitions
- `create_backup`, `list_backups`, `restore_backup`, `get_backup_diff` - Version control

### Hooks

**Hierarchical Planning Hooks** (FEAT-0003):

**.claude/hooks/hierarchy_validation_hook.py** (PreToolUse, BLOCKING)
- Blocks planning if parent not approved
- Enforces top-down planning order
- **Trigger**: Before Write/Edit on planning files
- **Effect**: BLOCKS operation if parent status ≠ approved

**.claude/hooks/state_sync_hook.py** (PostToolUse, NON-BLOCKING)
- Auto-syncs file changes → MCP state
- Calculates version hashes (SHA-256)
- Preserves entity status on edits
- **Trigger**: After Write/Edit on planning files
- **Effect**: Updates planning_state database

**.claude/hooks/consistency_check_hook.py** (PostToolUse, NON-BLOCKING)
- Warns about parent version mismatches
- Suggests revalidation when needed
- **Trigger**: After Write/Edit on planning files
- **Effect**: Shows warnings (operation allowed)

**.claude/hooks/invalidation_cascade_hook.py** (PostToolUse, NON-BLOCKING)
- Detects parent version changes
- Auto-cascades to all descendants
- Transaction-based marking
- **Trigger**: After Write/Edit on act/chapter plans
- **Effect**: Marks descendants requires-revalidation

**Shared Utilities**:

**.claude/hooks/planning_path_utils.py**
- Shared path parsing functions
- Canonical entity extraction logic
- Used by all 4 planning hooks
- Prevents code duplication

**Observability Hook**:

**.claude/hooks/path_interceptor_hook.py** (PostToolUse, NON-BLOCKING)
- Показывает AI путевое разрешение
- Информирует о CoW статусе
- Graceful degradation on errors
- **Trigger**: После Read, Write, Edit, Glob операций

**Output Example**:
```
💡 [CoW Active] Reading from session: scene-0101.md
   Source: workspace/sessions/test/scene-0101.md
   Status: Modified in session (CoW copy)
```

### Agent System

**Структура**:
```
.claude/agents/
├── planning/           # 15 агентов планирования
│   ├── context-analyzer.md
│   ├── scenario-generator.md
│   ├── consequence-predictor.md
│   └── ...
├── generation/         # 10 агентов генерации
│   ├── generation-coordinator.md
│   ├── prose-writer.md
│   ├── blueprint-validator.md
│   └── ...
└── shared/            # 15+ общих агентов
    ├── world-lorekeeper.md
    ├── character-state.md
    ├── canon-guardian.md
    └── ...
```

**Principles**:
- **Single Responsibility**: один агент = одна задача
- **Isolated Context**: каждый агент видит только необходимое
- **Artifact Output**: результаты в файлы, не в промпт
- **Stateless**: нет shared state между агентами

### Context Management

**World Bible** (Canon Levels 0-4):
```
context/world-bible/
├── level-0-absolutes/      # Неизменные факты
├── level-1-core/           # Основные элементы
├── level-2-established/    # Установленные факты
├── level-3-working/        # Рабочие предположения
└── level-4-exploratory/    # Идеи для проработки
```

**Character Tracking**:
```
context/characters/
└── {character-name}/
    ├── timeline.json       # Где и когда
    ├── knowledge.json      # Что знает
    ├── emotional-arc.json  # Эмоциональное состояние
    └── relationships.json  # Связи с другими
```

## 📊 Data Flow

### Planning → Generation

```
User: /plan-story
    ↓
Planning Workflow (5 phases)
    ↓
Blueprint: acts/act-1/chapters/chapter-01/scenes/scene-0101-blueprint.md
    │
    │  [User reviews blueprint, makes edits if needed]
    │
    ▼
User: Сгенерируй сцену 0101
    ↓
Generation Workflow (7 steps)
    ↓
Scene: acts/act-1/chapters/chapter-01/content/scene-0101.md
```

### Session Workflow

```
1. create_session(name="experiment")
    ↓
2. [Work in isolated session]
    ↓
   workspace/sessions/experiment/
   └── [modified files]
    ↓
3. session_status() → review changes
    ↓
4a. commit_session() → apply to global
    OR
4b. cancel_session() → discard all changes
```

## 🔐 Security & Safety

### File Isolation

- **Sessions**: полная изоляция от global files
- **CoW**: оригиналы не изменяются до commit
- **Backups**: автоматическое архивирование старых версий

### State Validation

- **Schema validation**: Pydantic models для всех inputs
- **Type safety**: использование Enums вместо strings
- **Prerequisite checks**: нельзя пропустить steps

### Error Handling

- **Graceful degradation**: hooks не блокируют при ошибках
- **Retry logic**: до 3 попыток для генерации
- **State preservation**: ошибки сохраняются для анализа

## 📈 Scalability

### Parallel Execution

**Planning Workflow**:
- Phase 2-3: до 6 агентов параллельно
- Phase 4: детализация сцен параллельно

**Generation Workflow**:
- Step 6: 7 validators параллельно

**Integration**:
- До 4 агентов параллельно

### Resource Management

**Context Budget**:
- Держать <60% context window
- `/compact` между фазами
- `/clear` перед новым workflow

**Disk Usage**:
- CoW: минимальное дублирование
- Backups: timestamped, ручная очистка
- Logs: rotation по дате

## 🎯 Performance

### Ориентировочное время

| Operation | Time | Bottleneck |
|-----------|------|------------|
| Planning (scene) | 2-5 min | Agent invocations |
| Generation (scene) | 5-8 min | LLM generation + validation |
| Blueprint validation | 30 sec | File I/O + checks |
| Full validation (7 validators) | 2-3 min | Parallel execution |
| Session commit | 5-10 sec | File copying |

### Optimization Strategies

1. **Parallel execution**: независимые агенты запускаются одновременно
2. **Artifact caching**: переиспользование промежуточных результатов
3. **Fast-fail validation**: поверхностная проверка перед глубокой
4. **Context compaction**: регулярная очистка истории

## 🔄 Update & Evolution

### Версионирование

**Файлы**:
- Current: стандартное имя без суффиксов
- Old: `backups/{name}-{timestamp}.md`

**Code**:
- Git branches: `claude/phase-{N}-{description}-{session-id}`
- Semantic commits: `feat:`, `fix:`, `refactor:`, `docs:`

### Добавление новых агентов

1. Создать агента в `.claude/agents/{category}/`
2. Добавить в `.workflows/agents-reference.md`
3. Интегрировать в workflow (`.workflows/{workflow}.md`)
4. Обновить CLAUDE.md если меняются критичные правила

### Добавление новых MCP tools

1. Добавить в существующий MCP server или создать новый
2. Обновить `mcp-servers/README.md`
3. Документировать в соответствующем workflow
4. Добавить в `.claude/mcp.json` если новый server

## 🧪 Testing Strategy

### Unit Tests (Planned)

- MCP tools: валидация inputs/outputs
- State management: transitions & persistence
- Path resolution: CoW logic

### Integration Tests (Planned)

- Full workflow: planning → generation
- Session lifecycle: create → modify → commit
- Error recovery: timeout → resume

### Manual Testing

- Blueprint quality assessment
- Generated prose review
- Validation accuracy check

## 📚 References

### Internal Documentation

**Core Documentation**:
- [README.md](README.md) - User guide
- [CLAUDE.md](CLAUDE.md) - AI assistant instructions & workflow router
- [.workflows/planning.md](.workflows/planning.md) - Planning workflow
- [.workflows/generation.md](.workflows/generation.md) - Generation workflow
- [.workflows/testing-checklist.md](.workflows/testing-checklist.md) - Testing procedures
- [.workflows/agents-reference.md](.workflows/agents-reference.md) - Agent catalog

**Component Documentation**:
- [mcp-servers/README.md](mcp-servers/README.md) - MCP servers documentation
- [.claude/hooks/README.md](.claude/hooks/README.md) - Hooks documentation

**Feature Documentation**:
- [features/FEAT-0003-hierarchical-planning/](features/FEAT-0003-hierarchical-planning/)
  - [technical-design.md](features/FEAT-0003-hierarchical-planning/technical-design.md) - Design specification
  - [IMPLEMENTATION-COMPLETE.md](features/FEAT-0003-hierarchical-planning/IMPLEMENTATION-COMPLETE.md) - Implementation summary
  - [CODE-REVIEW-RESPONSE.md](features/FEAT-0003-hierarchical-planning/CODE-REVIEW-RESPONSE.md) - Code review resolution
- [docs/emergency-recovery.md](docs/emergency-recovery.md) - Emergency recovery procedures

### External Resources

- [Anthropic Claude Code](https://docs.claude.com/en/docs/claude-code) - Official docs
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP Python SDK

## 🎓 Design Decisions

### Why Copy-on-Write?

**Alternatives considered**:
- Git branches: too heavyweight, merge conflicts
- Full directory copy: wasteful disk usage
- In-memory tracking: lost on crashes

**CoW chosen for**:
- Minimal overhead for read-only
- Atomic commit/rollback
- Disk space efficiency
- Simple implementation

### Why Artifact-Based Communication?

**Alternatives considered**:
- Full content in prompts: context overflow
- Shared memory: not supported by Claude
- Database: overkill for file-based system

**Artifacts chosen for**:
- Context efficiency
- Natural file system integration
- Easy debugging (files on disk)
- No additional dependencies

### Why Sequential Enforcement?

**Alternatives considered**:
- Free-form execution: hard to debug
- Manual checks: error-prone
- Implicit dependencies: fragile

**Sequential enforcement chosen for**:
- Predictable execution order
- Easy to reason about
- Clear error messages
- Resume capability

## 🔮 Future Improvements

### Phase 5: Advanced Features (Planned)

- [ ] Parallel scene generation
- [ ] Multi-chapter planning
- [ ] Character consistency checker
- [ ] World Bible auto-update
- [ ] Canon conflict resolver

### Phase 6: Optimization (Planned)

- [ ] Artifact caching layer
- [ ] Incremental validation
- [ ] Smart context pruning
- [ ] Batch blueprint validation

### Phase 7: Observability (Planned)

- [ ] Workflow metrics dashboard
- [ ] Agent performance tracking
- [ ] Context usage heatmap
- [ ] Error analytics

---

## 📋 Implementation Status

### ✅ Completed Features

**FEAT-0001**: Scene Generation Workflow (v2.0)
- 7-step generation workflow with auto-retry
- Blueprint validation & compliance checking
- Fast-fail + full validation

**FEAT-0002**: Generation State Tracking
- Resume failed workflows
- Real-time progress monitoring
- State persistence & recovery

**FEAT-0003**: Hierarchical Planning Architecture ⭐ NEW
- 3-level hierarchy (Act → Chapter → Scene)
- Parent-child validation & cascade invalidation
- Version management & backup system
- 10 MCP tools + 4 hooks + 12 commands
- Emergency recovery procedures

**FEAT-0004**: Workflow Orchestration (Phase 4)
- Sequential enforcement
- Human-in-the-loop approval
- State transitions & validation
- Resume capability

### 🚧 In Development

**Phase 5**: Advanced Features (Planned)
- Parallel scene generation
- Multi-chapter planning
- Character consistency checker

---

**Last Updated**: 2025-11-15
**Version**: Phase 4 + FEAT-0003 (Hierarchical Planning)
**Maintainers**: AI-assisted writing system team
