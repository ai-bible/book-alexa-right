# Claude Code Hooks

Документация по hooks для AI-Assisted Writing System.

## 📖 Что такое Hooks?

Hooks - это Python скрипты, которые автоматически выполняются в ответ на события в Claude Code. Они позволяют:

- **Наблюдать** за действиями AI
- **Направлять** поведение AI
- **Автоматизировать** рутинные задачи
- **Валидировать** операции

**Важно**: Hooks должны быть **быстрыми** и **надёжными**. Они не должны блокировать работу AI.

## 🎯 Существующие Hooks

### path_interceptor_hook.py

**Тип**: PostToolUse (observability)
**Статус**: CRITICAL - система не работает без него
**Блокирует**: НЕТ (graceful degradation)

#### Назначение

Показывает AI информацию о путевом разрешении в контексте CoW сессий:
- Откуда читается файл (session vs global)
- Статус CoW (modified, original, new)
- Предупреждения о shadowing

#### Когда запускается

После каждой операции с файлами:
- `Read` - чтение файла
- `Write` - запись файла
- `Edit` - редактирование файла
- `Glob` - поиск файлов по паттерну

#### Что показывает AI

**Сценарий 1: Файл в сессии (CoW активен)**
```
💡 [CoW Active] Reading from session: scene-0101.md
   Source: workspace/sessions/experiment/scene-0101.md
   Status: Modified in session (CoW copy)
```

**Сценарий 2: Файл в global (не изменён)**
```
💡 [Global] Reading from global: scene-0101.md
   Source: acts/act-1/chapters/chapter-01/content/scene-0101.md
   Status: Not yet modified in session
   ⚡ CoW will trigger: File will be copied to session on write
```

**Сценарий 3: Новый файл**
```
✨ [New File] Creating in session: scene-0102.md
   Destination: workspace/sessions/experiment/scene-0102.md
```

**Сценарий 4: Файл существует в обоих местах**
```
💡 [CoW Active] Reading from session: scene-0101.md
   Source: workspace/sessions/experiment/scene-0101.md
   Status: Modified in session (CoW copy)
   Note: Global file is shadowed - session version takes precedence
```

#### Архитектура

```python
def _print_file_status(header: str, details: dict[str, Optional[str]]) -> None:
    """
    Вспомогательная функция для единообразного вывода статуса.

    Args:
        header: Заголовок (например, "💡 [CoW Active] Reading from...")
        details: Словарь деталей {label: value}
                 value=None означает что key выводится как есть
    """
    print(f"\n{header}", file=sys.stderr)
    for key, value in details.items():
        if value is None:
            print(f"   {key}", file=sys.stderr)
        else:
            print(f"   {key}: {value}", file=sys.stderr)

def main():
    """Основная логика hook."""
    try:
        # 1. Прочитать event data из stdin
        event_data = json.load(sys.stdin)

        # 2. Проверить tool_name
        if tool_name not in ["Read", "Write", "Edit", "Glob"]:
            sys.exit(0)  # Не наш случай

        # 3. Проверить активную сессию
        lock_file = Path("workspace/session.lock")
        if not lock_file.exists():
            sys.exit(0)  # Нет сессии

        # 4. Определить расположение файла
        session_file = session_path / file_path
        global_file = Path(file_path)

        # 5. Показать статус AI
        if session_file.exists() and global_file.exists():
            _print_file_status("CoW Active", {...})
        elif session_file.exists():
            _print_file_status("CoW Active", {...})
        elif global_file.exists():
            _print_file_status("Global", {...})
        elif tool_name in ["Write", "Edit"]:
            _print_file_status("New File", {...})

        sys.exit(0)  # Всегда успех

    except Exception as e:
        # Graceful degradation - залогировать но не блокировать
        print(f"⚠️ [Path Interceptor] Error: {e}", file=sys.stderr)
        sys.exit(0)
```

#### Почему это критично?

Без этого hook AI:
- Не знает что работает в сессии
- Может случайно изменить global файлы
- Не понимает CoW механизм
- Запутается в версиях файлов

#### Error Handling

**Принцип**: **Никогда не блокировать**

Если hook упал:
1. Логируем ошибку в stderr
2. Возвращаем exit code 0 (успех)
3. AI продолжает работу

```python
except Exception as e:
    print(f"⚠️ [Path Interceptor] Error: {e}", file=sys.stderr)
    sys.exit(0)  # НЕ sys.exit(1) - не блокируем!
```

## 🔧 Создание собственных Hooks

### Hook Types

Claude Code поддерживает несколько типов hooks:

1. **PreToolUse** - перед выполнением tool
   - Может блокировать операцию
   - Может модифицировать параметры
   - Use case: валидация, проверки безопасности

2. **PostToolUse** - после выполнения tool
   - НЕ может блокировать
   - Может показывать информацию AI
   - Use case: observability, логирование

3. **PrePrompt** - перед отправкой промпта
   - Может добавлять контекст
   - Use case: injection системных инструкций

4. **PostResponse** - после ответа AI
   - Может обрабатывать ответ
   - Use case: валидация, метрики

### Структура Hook

```python
#!/usr/bin/env python
"""
{Hook Type}: {Hook Name}

RESPONSIBILITY: {Краткое описание}

ARCHITECTURE: {Blocking/Non-blocking}
- {Что делает}
- {Когда запускается}

TRIGGERS: {События}
FAILURE MODE: {Что происходит при ошибке}
"""

import sys
import json
from pathlib import Path

def main():
    """Основная логика hook."""
    try:
        # 1. Прочитать event data
        event_data = json.load(sys.stdin)

        # 2. Обработать событие
        # ...

        # 3. Вернуть результат
        # For blocking hooks:
        #   sys.exit(0) = allow
        #   sys.exit(1) = block
        # For non-blocking hooks:
        #   sys.exit(0) всегда

        sys.exit(0)

    except Exception as e:
        # Error handling
        print(f"⚠️ [{Hook Name}] Error: {e}", file=sys.stderr)
        sys.exit(0)  # or 1 for blocking hooks

if __name__ == "__main__":
    main()
```

### Регистрация Hook

В `.claude/claude.json`:

```json
{
  "hooks": {
    "postToolUse": [
      {
        "name": "path_interceptor",
        "command": "python",
        "args": [".claude/hooks/path_interceptor_hook.py"]
      }
    ],
    "preToolUse": [
      {
        "name": "file_validator",
        "command": "python",
        "args": [".claude/hooks/file_validator_hook.py"]
      }
    ]
  }
}
```

## 🎯 Best Practices

### DO's ✅

1. **Будь быстрым**: hook должен выполняться <100ms
2. **Будь надёжным**: всегда обрабатывай ошибки
3. **Будь информативным**: чёткие сообщения в stderr
4. **Используй graceful degradation**: не блокируй на ошибках
5. **Логируй всё**: stdout/stderr видны в логах Claude Code
6. **Тестируй изолированно**: можно запускать руками с test data

### DON'Ts ❌

1. **Не блокируй без необходимости**: особенно PostToolUse hooks
2. **Не делай сетевые запросы**: слишком медленно
3. **Не модифицируй файлы**: hook для наблюдения, не действия
4. **Не используй внешние dependencies**: только stdlib Python
5. **Не логируй sensitive data**: stdout/stderr идут в логи
6. **Не полагайся на current directory**: используй абсолютные пути

## 🧪 Тестирование Hooks

### Manual Testing

```bash
# Подготовить test event data
cat > test_event.json <<EOF
{
  "tool_name": "Read",
  "tool_input": {
    "file_path": "acts/act-1/chapters/chapter-01/content/scene-0101.md"
  }
}
EOF

# Запустить hook
python .claude/hooks/path_interceptor_hook.py < test_event.json

# Проверить exit code
echo $?  # Должно быть 0
```

### Test Scenarios

Для path_interceptor_hook:

1. **No session active**: hook should exit silently
2. **File in session**: show CoW status
3. **File in global**: show global status + CoW warning
4. **File in both**: show shadowing warning
5. **New file**: show creation in session
6. **Invalid event data**: graceful error, exit 0

## 📊 Performance

### Benchmark

```bash
# Измерить время выполнения
time python .claude/hooks/path_interceptor_hook.py < test_event.json

# Целевые значения:
# Real time: <50ms
# User time: <30ms
# Sys time: <20ms
```

### Optimization Tips

1. **Lazy imports**: импортируй только если нужно
2. **Early exit**: проверяй условия в начале
3. **Cache file reads**: если читаешь несколько раз
4. **Avoid glob patterns**: используй прямые path checks

## 🔍 Debugging

### Enabling Debug Output

```python
import os

DEBUG = os.getenv("HOOK_DEBUG", "0") == "1"

if DEBUG:
    print(f"[DEBUG] Event data: {event_data}", file=sys.stderr)
```

Запуск с debug:
```bash
HOOK_DEBUG=1 claude code
```

### Common Issues

**Hook не запускается**:
- Проверь `.claude/claude.json` регистрацию
- Проверь права на выполнение: `chmod +x hook.py`
- Проверь shebang: `#!/usr/bin/env python`

**Hook блокирует операции**:
- Проверь exit code: должен быть 0 для non-blocking
- Проверь exception handling: все catch должны exit(0)

**Hook медленный**:
- Профилируй с `time` или `cProfile`
- Убери сетевые запросы
- Убери тяжёлые вычисления

## 🔒 Security

### Safe Practices

1. **Validate inputs**: проверяй event_data перед использованием
2. **Sanitize paths**: используй `Path().resolve()` для предотвращения path traversal
3. **Limit file access**: читай только необходимые файлы
4. **No shell execution**: не используй `os.system()` или `subprocess.call()`
5. **No eval/exec**: никогда не выполняй динамический код

### Example: Safe Path Handling

```python
from pathlib import Path

def is_safe_path(path_str: str, base_dir: Path) -> bool:
    """Check if path is within base directory."""
    try:
        path = Path(path_str).resolve()
        base = base_dir.resolve()
        return path.is_relative_to(base)
    except Exception:
        return False

# Usage
file_path = event_data.get("tool_input", {}).get("file_path", "")
if not is_safe_path(file_path, Path.cwd()):
    print("⚠️ Path outside project directory", file=sys.stderr)
    sys.exit(1)  # Block if suspicious
```

## 📚 References

### Internal Documentation

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - System architecture
- [README.md](../../README.md) - User guide
- [mcp-servers/README.md](../../mcp-servers/README.md) - MCP servers

### External Resources

- [Claude Code Hooks Documentation](https://docs.claude.com/en/docs/claude-code/hooks)
- [Python sys module](https://docs.python.org/3/library/sys.html)
- [Python json module](https://docs.python.org/3/library/json.html)

### integration_guard_hook.py (FEAT-0005)

**Тип**: PreToolUse (blocking)
**Статус**: IMPORTANT - предотвращает потерю контекста
**Блокирует**: ДА (только commit_session)

#### Назначение

Блокирует коммит сессии если есть сцены с pending context integrations:
- Сгенерирована (`generated=true`)
- НЕ интегрирована (`integrated=false`)
- НЕ пропущена (`skipped=false`)

#### Когда запускается

Перед вызовом `mcp__session_management__commit_session`

#### Что показывает

**Если есть pending integrations:**
```
❌ BLOCKED: Commit has pending context integrations

The following scenes were generated but not integrated:
  • Scene 0204
  • Scene 0205

💡 Options:
   1. Integrate contexts: /integrate-context <scene_id>
   2. Skip integration: Mark as skipped in integration-status.json
   3. Force commit: /session commit --force
```

#### Связанные файлы

- `workspace/integration-status.json` - tracking статуса интеграций
- `context/characters/{name}/knowledge-timeline.md` - knowledge timelines

---

### session_summary_hook.py (Updated for FEAT-0005)

**Обновление**: Теперь показывает pending context integrations при завершении сессии.

```
📂 ACTIVE SESSION
============================================================

Session: chapter-01-work
Status: ACTIVE
...

⚠️  Pending context integrations: 2
  • Scene 0204 (generated but not integrated)
  • Scene 0205 (generated but not integrated)

  Run: /integrate-context <scene_id>

💡 Don't forget to:
  - Integrate contexts first (or commit will be blocked)
  - Commit changes: /session commit
  - Or cancel: /session cancel
```

---

## 🔮 Future Hooks (Planned)

### validation_hook.py (PreToolUse)

**Purpose**: Validate file operations against project rules
- Check file naming conventions
- Prevent creation of versioned files (plan-v2.md)
- Ensure files go to correct directories

### metrics_hook.py (PostResponse)

**Purpose**: Collect metrics on AI performance
- Track response time
- Count token usage
- Measure context efficiency

### context_pruning_hook.py (PrePrompt)

**Purpose**: Auto-prune context before overflow
- Detect context approaching limit
- Remove old conversation history
- Preserve critical context

---

**Last Updated**: 2025-11-10
**Version**: Phase 4 (Workflow Orchestration)
**Maintainers**: AI-assisted writing system team
