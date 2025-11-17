# MCP Servers

Model Context Protocol серверы для AI-Assisted Writing System.

## 📖 Что такое MCP?

**Model Context Protocol (MCP)** - это открытый протокол для интеграции AI с внешними системами и инструментами. MCP серверы предоставляют AI набор "tools" (функций), которые он может вызывать для выполнения задач.

### Почему MCP критичен?

**Без MCP серверов система не работает**. Они обеспечивают:

- 🔄 **Session management** - изоляция изменений, CoW механизм
- 📊 **Workflow orchestration** - отслеживание прогресса, recovery
- 💾 **State persistence** - сохранение состояния между запусками
- 🔒 **Safety** - валидация операций, предотвращение ошибок

## 🎯 Архитектура MCP

```
┌─────────────────────────────────────────────────────────┐
│                     Claude Code (AI)                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Вызывает MCP tools
                 ▼
┌─────────────────────────────────────────────────────────┐
│                   MCP Protocol Layer                    │
│         (FastMCP - Python SDK для MCP)                  │
└────────┬────────────────────┬────────────────┬──────────┘
         │                    │                │
         ▼                    ▼                ▼
┌──────────────────┐ ┌─────────────────┐ ┌──────────────┐
│  session_        │ │  workflow_      │ │ generation_  │
│  management_     │ │  orchestration_ │ │ state_       │
│  mcp.py          │ │  mcp.py         │ │ mcp.py       │
│                  │ │                 │ │              │
│ (CoW sessions)   │ │ (Workflow state)│ │ (Legacy)     │
└──────────────────┘ └─────────────────┘ └──────────────┘
```

## ⚙️ Setup & Installation

### Requirements

- **Python 3.13+** (managed via `uv`)
- **uv** (fast Python package manager) - [Install guide](https://docs.astral.sh/uv/)

### Quick Start

```bash
# 1. Install dependencies with uv (automatically uses Python 3.13)
cd mcp-servers
uv sync

# 2. Run tests to verify installation
uv run pytest

# 3. Compile all MCP servers to check for syntax errors
uv run python -m py_compile *.py
```

### Using uv

This project uses [**uv**](https://github.com/astral-sh/uv) for dependency management:

**Why uv?**
- ⚡ **10-100x faster** than pip
- 🔒 **Deterministic** dependency resolution with lockfile
- 🐍 **Python version management** built-in (uses Python 3.13)
- 📦 **Modern** pyproject.toml-based configuration

**Common commands:**

```bash
# Install/sync dependencies
uv sync

# Run Python with managed environment
uv run python script.py

# Run tests
uv run pytest

# Add new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade
```

### Dependencies

Managed via `pyproject.toml`:

- **mcp** (>=1.0.0) - Model Context Protocol Python SDK
- **pydantic** (>=2.0.0) - Data validation and schema generation

**Dev dependencies:**
- **pytest** (>=8.0.0) - Testing framework
- **pytest-asyncio** (>=0.23.0) - Async test support

### Migration from pip

If migrating from an existing `requirements.txt` setup:

```bash
# Old way (pip)
pip install -r requirements.txt

# New way (uv) - automatically migrated
uv sync
```

The `requirements.txt` file is kept for reference but **uv + pyproject.toml is now the primary method**.

## 📦 Установленные серверы

### 1. session_management_mcp.py ⭐ CRITICAL

**Статус**: Production, активно используется
**Framework**: FastMCP
**Dependencies**: session_models.py, session_utils.py

#### Назначение

Управление Copy-on-Write сессиями для безопасного экспериментирования.

#### Ключевые возможности

- ✅ Создание изолированных сессий
- ✅ Переключение между сессиями
- ✅ Commit изменений в global
- ✅ Cancel сессий без изменения global
- ✅ CoW механизм (файлы копируются только при изменении)
- ✅ Путевое разрешение (session → global fallback)
- ✅ Human retry tracking

#### MCP Tools (6)

| Tool | Описание |
|------|----------|
| `create_session` | Создать новую сессию |
| `switch_session` | Переключиться на другую сессию |
| `commit_session` | Закоммитить изменения в global |
| `cancel_session` | Удалить сессию и все изменения |
| `list_sessions` | Список всех сессий |
| `session_status` | Статус активной сессии |

#### Пример использования

```python
# Создать сессию
create_session(
    name="experiment-scene-0204",
    description="Trying darker tone"
)

# [Work in session - все изменения изолированы]

# Проверить что изменилось
session_status()

# Если понравилось - закоммитить
commit_session(name="experiment-scene-0204")

# Если нет - отменить
cancel_session(name="experiment-scene-0204")
```

#### Внутренняя структура

**session_models.py** - Pydantic модели и Enums:
- `SessionStatus` - ACTIVE, INACTIVE, CRASHED
- `ChangeType` - MODIFIED, CREATED, DELETED
- Input validation для всех tools

**session_utils.py** - Вспомогательные функции:
- `_resolve_path_cow()` - путевое разрешение с CoW
- `_add_cow_file()` - добавить файл в tracking
- `_copy_workflow_states_to_global()` - интеграция с workflow orchestration

#### Состояние сессии

```json
{
  "name": "experiment-scene-0204",
  "description": "Trying darker tone",
  "status": "ACTIVE",
  "created_at": "2025-11-10T14:30:00Z",
  "cow_files": [
    {
      "path": "acts/act-1/chapters/chapter-01/content/scene-0101.md",
      "type": "modified",
      "copied_at": "2025-11-10T14:35:00Z",
      "size_bytes": 4096
    }
  ],
  "changes": {
    "modified": ["acts/.../scene-0101.md"],
    "created": [],
    "deleted": []
  },
  "stats": {
    "total_files_changed": 1,
    "session_size_bytes": 4096
  }
}
```

---

### 2. workflow_orchestration_mcp.py ⭐ CORE

**Статус**: Production, активно используется
**Framework**: FastMCP
**Dependencies**: Нет (standalone)

#### Назначение

Централизованное управление состоянием Planning и Generation workflows.

#### Ключевые возможности

- ✅ Sequential enforcement (нельзя пропустить steps)
- ✅ Human-in-the-loop checkpoints (approval flow)
- ✅ State persistence (JSON files)
- ✅ Resume capability (продолжение после сбоя)
- ✅ Session-aware paths (интеграция с sessions)

#### MCP Tools (8)

| Tool | Описание |
|------|----------|
| `get_workflow_status` | Получить статус workflow |
| `get_next_step` | Узнать следующий step/phase |
| `validate_prerequisites` | Проверить можно ли начать step |
| `approve_step` | Одобрить human-in-the-loop checkpoint |
| `update_workflow_state` | Обновить состояние step/phase |
| `list_workflows` | Список всех workflows (с фильтрами) |
| `resume_workflow` | Продолжить failed workflow |
| `cancel_workflow` | Отменить workflow |

#### Workflow Types

**Generation Workflow** (7 steps):
1. File Check
2. Blueprint Validation
3. Verification Plan (HUMAN APPROVAL)
4. Generation (retry до 3 раз)
5. Fast Compliance Check
6. Full Validation
7. Final Output

**Planning Workflow** (5 phases):
1. Exploration
2. Scenarios (HUMAN APPROVAL)
3. Path Planning
4. Detailing
5. Integration

#### Пример использования

```python
# STEP 0B: Initialize workflow state
workflow_id = f"generation-scene-{scene_id}-{timestamp}"

# Create initial state (manual JSON write)
state = {
    "workflow_id": workflow_id,
    "workflow_type": "generation",
    "status": "in_progress",
    "steps": [...]
}

# STEP 1: Validate prerequisites before starting
result = validate_prerequisites(workflow_id, step=1)
if not result["can_start_step"]:
    return error(result["blocking_issues"])

# Start step 1
update_workflow_state(workflow_id, step=1, status="in_progress")

# [Do work]

# Complete step 1
update_workflow_state(
    workflow_id,
    step=1,
    status="completed",
    artifacts={"blueprint_path": "..."}
)

# STEP 3: Human approval
update_workflow_state(workflow_id, step=3, status="waiting_approval")
# [Show plan to user]
approve_step(workflow_id, step=3, approved=True)
```

#### Workflow State

```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "workflow_type": "generation",
  "status": "in_progress",
  "current_step": 3,
  "scene_id": "0204",
  "started_at": "2025-11-10T14:30:00Z",
  "steps": [
    {
      "step": 1,
      "name": "File Check",
      "status": "completed",
      "started_at": "2025-11-10T14:30:01Z",
      "completed_at": "2025-11-10T14:30:05Z",
      "artifacts": {"blueprint_path": "..."}
    },
    {
      "step": 3,
      "name": "Verification Plan",
      "status": "waiting_approval",
      "started_at": "2025-11-10T14:30:15Z",
      "approval_required": true
    }
  ]
}
```

---

### 3. generation_state_mcp.py ⚠️ DEPRECATED

**Статус**: Legacy, заменяется на workflow_orchestration_mcp
**Framework**: FastMCP
**Причина deprecation**: Функциональность дублируется workflow_orchestration

#### Почему оставлен?

- Обратная совместимость со старым кодом
- Постепенная миграция на workflow_orchestration
- Будет удалён в Phase 5

#### Что делать?

**Новый код**: используй `workflow_orchestration_mcp`
**Старый код**: работает, но планируй миграцию

---

## ⚙️ Установка и настройка

### 1. Требования

```bash
# Python 3.10+
python --version

# FastMCP (MCP Python SDK)
pip install fastmcp

# Pydantic для валидации
pip install pydantic
```

### 2. Регистрация в Claude Code

Файл `.claude/mcp.json`:

```json
{
  "servers": {
    "session_management": {
      "command": "python",
      "args": ["mcp-servers/session_management_mcp.py"],
      "disabled": false
    },
    "workflow_orchestration": {
      "command": "python",
      "args": ["mcp-servers/workflow_orchestration_mcp.py"],
      "disabled": false
    },
    "generation_state": {
      "command": "python",
      "args": ["mcp-servers/generation_state_mcp.py"],
      "disabled": true
    }
  }
}
```

**Важно**: `generation_state` отключен (deprecated), остальные обязательны!

### 3. Проверка установки

```bash
# Запустить MCP server напрямую (для тестирования)
python mcp-servers/session_management_mcp.py

# Должно показать список tools
```

В Claude Code:
```
create_session(name="test", description="Installation test")
```

Если работает → MCP настроен правильно ✅

## 🧪 Тестирование

### Manual Testing

```python
# Test session management
create_session(name="test-session", description="Test")
session_status()
commit_session(name="test-session")

# Test workflow orchestration
# (требует создания test workflow state file)
list_workflows(workflow_type="generation")
```

### Debugging

**Включить debug output**:

```json
{
  "servers": {
    "session_management": {
      "command": "python",
      "args": ["mcp-servers/session_management_mcp.py"],
      "env": {
        "MCP_DEBUG": "1"
      }
    }
  }
}
```

**Проверить логи**:
```bash
# Claude Code логи показывают MCP вызовы
claude code --verbose
```

## 🔍 Troubleshooting

### MCP server не запускается

**Симптомы**: Tools не доступны, ошибки при вызове

**Решения**:
1. Проверь `.claude/mcp.json` - правильные пути?
2. Проверь Python version: `python --version` (3.10+)
3. Проверь dependencies: `pip list | grep fastmcp`
4. Запусти server напрямую для проверки ошибок

### Tools возвращают ошибки

**Симптомы**: Tool вызывается но возвращает error

**Решения**:
1. Проверь параметры - используй правильные типы
2. Проверь файловую систему - workspace/ существует?
3. Проверь права доступа - Python может писать в workspace/?
4. Проверь логи MCP server (если debug включен)

### Session не коммитится

**Симптомы**: `commit_session` не применяет изменения

**Решения**:
1. Проверь session status - файлы изменены?
2. Проверь CoW tracking - `session_status()` показывает cow_files?
3. Проверь права на global файлы - можно писать?
4. Проверь workspace/sessions/{name}/ - файлы там?

### Workflow не возобновляется

**Симптомы**: `resume_workflow` не находит state

**Решения**:
1. Проверь workflow-state/ директорию
2. Проверь session path - может state в session?
3. Проверь workflow_id - правильный формат?
4. Проверь JSON файл - валидный?

## 📚 API Reference

### Session Management API

Подробная документация в коде: `session_management_mcp.py`

**Ключевые типы**:
```python
class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CRASHED = "CRASHED"

class ChangeType(str, Enum):
    MODIFIED = "modified"
    CREATED = "created"
    DELETED = "deleted"
```

### Workflow Orchestration API

Подробная документация в коде: `workflow_orchestration_mcp.py`

**Ключевые типы**:
```python
WorkflowType = "generation" | "planning"
StepStatus = "pending" | "in_progress" | "completed" | "failed" | "waiting_approval"
```

## 🎯 Best Practices

### DO's ✅

1. **Всегда используй sessions для экспериментов** - безопасно
2. **Проверяй prerequisites перед каждым step** - sequential enforcement
3. **Сохраняй workflow state часто** - каждый step start/complete
4. **Обрабатывай human approval** - не пропускай waiting_approval
5. **Используй resume при сбоях** - не начинай заново

### DON'Ts ❌

1. **Не коммить сессию без проверки** - может быть ошибка
2. **Не пропускать steps** - validate_prerequisites обязателен
3. **Не игнорировать failed workflows** - resume или cancel
4. **Не хардкодить пути** - используй session-aware paths
5. **Не удалять state files вручную** - используй MCP tools

## 🔮 Roadmap

### Phase 5: Consolidation

- [ ] Удалить generation_state_mcp.py (deprecated)
- [ ] Мигрировать весь код на workflow_orchestration_mcp
- [ ] Унифицировать API между servers

### Phase 6: Enhancements

- [ ] Metrics collection MCP server
- [ ] Backup/restore MCP server
- [ ] Cache management MCP server

### Phase 7: Optimization

- [ ] Batch operations support
- [ ] Async tool execution
- [ ] Performance monitoring

## 📖 References

### Internal Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [README.md](../README.md) - User guide
- [.claude/hooks/README.md](../.claude/hooks/README.md) - Hooks documentation

### External Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Claude Code MCP Guide](https://docs.claude.com/en/docs/claude-code/mcp)

## 📝 Contributing

### Добавление нового MCP server

1. Создай `{name}_mcp.py` в `mcp-servers/`
2. Используй FastMCP framework
3. Добавь Pydantic models для валидации
4. Зарегистрируй в `.claude/mcp.json`
5. Обнови этот README
6. Добавь в ARCHITECTURE.md если нужно

### Добавление нового tool

1. Декоратор `@mcp.tool()` для функции
2. Pydantic model для параметров
3. Docstring с описанием (показывается AI)
4. Error handling с понятными сообщениями
5. Обнови документацию в коде

---

**Last Updated**: 2025-11-15
**Version**: Phase 4 (Workflow Orchestration) + Python 3.13 + UV migration
**Maintainers**: AI-assisted writing system team

## 📝 Changelog

### 2025-11-15: UV Migration
- ✅ Migrated to **uv** for dependency management
- ✅ Upgraded to **Python 3.13.8**
- ✅ Added `pyproject.toml` with modern configuration
- ✅ All tests passing with Python 3.13
- ✅ 10-100x faster dependency installation
- ℹ️ `requirements.txt` kept for reference only
