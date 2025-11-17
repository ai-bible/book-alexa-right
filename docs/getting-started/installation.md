# Установка

Эта страница покажет вам, как установить и настроить AI Writing System.

## Предварительные требования

Перед началом убедитесь, что у вас установлены:

### 1. Python 3.13+

=== "Linux/macOS"

    ```bash
    # Проверка версии
    python3 --version

    # Если Python 3.13 не установлен, используйте pyenv
    curl https://pyenv.run | bash
    pyenv install 3.13.8
    pyenv global 3.13.8
    ```

=== "Windows"

    ```powershell
    # Проверка версии
    python --version

    # Скачайте Python 3.13 с python.org
    # или используйте winget
    winget install Python.Python.3.13
    ```

### 2. UV Package Manager

UV — это современный быстрый пакетный менеджер для Python (10-100x быстрее pip).

=== "Linux/macOS"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

Проверка установки:

```bash
uv --version
```

### 3. Git

=== "Linux"

    ```bash
    # Debian/Ubuntu
    sudo apt-get install git

    # Fedora
    sudo dnf install git

    # Arch
    sudo pacman -S git
    ```

=== "macOS"

    ```bash
    # С помощью Homebrew
    brew install git
    ```

=== "Windows"

    ```powershell
    # С помощью winget
    winget install Git.Git
    ```

### 4. Claude Code

!!! info "Доступ к Claude Code"

    Для использования AI Writing System требуется доступ к Claude Code CLI от Anthropic.

    - Документация: [https://docs.claude.com/en/docs/claude-code](https://docs.claude.com/en/docs/claude-code)
    - Установка: Следуйте официальной документации Anthropic

## Клонирование репозитория

```bash
git clone https://github.com/ai-bible/book-alexa-right.git
cd book-alexa-right
```

## Установка зависимостей

### 1. MCP Servers

```bash
cd mcp-servers
uv sync
```

Эта команда:

- Создаст виртуальное окружение `.venv`
- Установит все зависимости из `pyproject.toml`
- Настроит dev-dependencies для тестирования

### 2. Проверка установки

Запустите тесты чтобы убедиться, что всё работает:

```bash
uv run pytest
```

Ожидаемый вывод:

```
============================= test session starts ==============================
collected 15 items

test_generation_state_mcp.py ........                                    [ 53%]
test_session_management_mcp.py .....                                     [ 86%]
test_workflow_orchestration_mcp.py ..                                    [100%]

============================== 15 passed in 2.43s ===============================
```

## Настройка Claude Code

### 1. Конфигурация MCP серверов

Добавьте MCP серверы в конфигурацию Claude Code:

=== "Linux/macOS"

    Отредактируйте `~/.config/claude-code/mcp_servers.json`:

    ```json
    {
      "mcpServers": {
        "generation-state": {
          "command": "uv",
          "args": [
            "run",
            "python",
            "/path/to/book-alexa-right/mcp-servers/generation_state_mcp.py"
          ],
          "cwd": "/path/to/book-alexa-right/mcp-servers"
        },
        "session-management": {
          "command": "uv",
          "args": [
            "run",
            "python",
            "/path/to/book-alexa-right/mcp-servers/session_management_mcp.py"
          ],
          "cwd": "/path/to/book-alexa-right/mcp-servers"
        },
        "workflow-orchestration": {
          "command": "uv",
          "args": [
            "run",
            "python",
            "/path/to/book-alexa-right/mcp-servers/workflow_orchestration_mcp.py"
          ],
          "cwd": "/path/to/book-alexa-right/mcp-servers"
        }
      }
    }
    ```

=== "Windows"

    Отредактируйте `%APPDATA%\claude-code\mcp_servers.json`:

    ```json
    {
      "mcpServers": {
        "generation-state": {
          "command": "uv",
          "args": [
            "run",
            "python",
            "C:\\path\\to\\book-alexa-right\\mcp-servers\\generation_state_mcp.py"
          ],
          "cwd": "C:\\path\\to\\book-alexa-right\\mcp-servers"
        },
        "session-management": {
          "command": "uv",
          "args": [
            "run",
            "python",
            "C:\\path\\to\\book-alexa-right\\mcp-servers\\session_management_mcp.py"
          ],
          "cwd": "C:\\path\\to\\book-alexa-right\\mcp-servers"
        },
        "workflow-orchestration": {
          "command": "uv",
          "args": [
            "run",
            "python",
            "C:\\path\\to\\book-alexa-right\\mcp-servers\\workflow_orchestration_mcp.py"
          ],
          "cwd": "C:\\path\\to\\book-alexa-right\\mcp-servers"
        }
      }
    }
    ```

!!! warning "Замените пути"

    Замените `/path/to/book-alexa-right` на актуальный путь к клонированному репозиторию.

### 2. Проверка подключения

Перезапустите Claude Code и выполните:

```
/mcp-list
```

Вы должны увидеть три MCP сервера в списке:

- `generation-state`
- `session-management`
- `workflow-orchestration`

## Структура проекта

После установки ваша структура проекта должна выглядеть так:

```
book-alexa-right/
├── .claude/                  # Агенты и hooks
│   ├── agents/              # Специализированные агенты
│   └── hooks/               # Hooks для validation
├── .workflows/              # Документация workflows
├── acts/                    # Структура романа
├── context/                 # Контекст мира
│   ├── characters/         # Персонажи
│   ├── locations/          # Локации
│   └── world-bible/        # Библия мира
├── mcp-servers/            # MCP серверы
│   ├── .venv/             # Виртуальное окружение (создаётся uv)
│   ├── pyproject.toml     # Конфигурация проекта
│   └── *.py               # MCP серверы
└── workspace/              # Временные файлы
```

## Следующие шаги

Теперь, когда система установлена, переходите к быстрому старту:

[Быстрый старт :octicons-arrow-right-24:](quick-start.md){ .md-button .md-button--primary }

---

## Решение проблем

### Проблема: `uv: command not found`

**Решение**: Убедитесь, что uv добавлен в PATH. Перезапустите терминал или выполните:

```bash
# Linux/macOS
source ~/.bashrc  # или ~/.zshrc

# Windows
# Перезапустите терминал
```

### Проблема: Тесты падают

**Решение**: Убедитесь, что вы находитесь в директории `mcp-servers` и используете правильную версию Python:

```bash
cd mcp-servers
python --version  # Должно быть 3.13+
uv sync           # Переустановите зависимости
uv run pytest -v  # Запустите с verbose
```

### Проблема: MCP серверы не обнаруживаются

**Решение**:

1. Проверьте пути в `mcp_servers.json`
2. Убедитесь, что файлы MCP серверов существуют
3. Проверьте права доступа к файлам (должны быть исполняемыми)
4. Перезапустите Claude Code

### Другие проблемы

Если проблема не решена, откройте [issue на GitHub](https://github.com/ai-bible/book-alexa-right/issues) с описанием:

- Версии Python (`python --version`)
- Версии UV (`uv --version`)
- Операционной системы
- Полного текста ошибки
