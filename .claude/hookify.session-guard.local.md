---
name: session-guard-block-global-writes
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|[/\\])(acts|context)[/\\]
  - field: file_path
    operator: not_contains
    pattern: workspace/sessions/
---

🚫 **БЛОКИРОВКА: Запись в глобальные файлы без сессии!**

Вы пытаетесь записать файл напрямую в `acts/` или `context/`, минуя активную сессию.

## ❌ Это ЗАПРЕЩЕНО! Почему:
- Изменения должны быть изолированы в сессии для возможности отката
- Copy-on-Write система требует записи в `workspace/sessions/{session_name}/`
- Прямая запись нарушает workflow и может повредить канонические файлы

## ✅ Правильный путь:

1. **Проверьте активную сессию:**
   ```
   mcp__session_management__get_active_session()
   ```

2. **Если сессия активна** - пишите в:
   ```
   workspace/sessions/{session_name}/acts/...
   workspace/sessions/{session_name}/context/...
   ```

3. **Если сессии нет** - создайте:
   ```
   mcp__session_management__create_session(name="...", description="...")
   ```

4. **После завершения работы** - закоммитьте:
   ```
   mcp__session_management__commit_session()
   ```

## 🔧 Исправьте путь и повторите операцию!
