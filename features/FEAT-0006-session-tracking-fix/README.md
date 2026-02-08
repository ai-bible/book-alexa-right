# FEAT-0006: Session Management Tracking Fix

## Problem Statement

MCP Session Management не отслеживает файлы, созданные через Claude Code Write/Edit инструменты. При вызове `commit_session` сервер говорит "no changes to commit" несмотря на то, что файлы физически существуют в директории сессии.

Дополнительно: сессии остаются в статусе "CRASHED" без возможности восстановления.

---

## User Journey

### Current (Broken) Flow

**Starting Point:**
Пользователь хочет работать с изоляцией изменений через сессию.

**Step-by-Step (сейчас):**
1. User: Создаёт сессию через `create_session("work-on-chapter")`
2. System: Сессия создана, `cow_files: []`
3. User: Вызывает `resolve_path("acts/act-1/plan.md")`
4. System: Возвращает путь `workspace/sessions/work-on-chapter/acts/act-1/plan.md`
5. User/Claude: Использует `Write` tool для записи в этот путь
6. System: Файл создан, **НО MCP не уведомлён**
7. User: Вызывает `commit_session()`
8. System: ❌ "No changes to commit" — `cow_files` всё ещё пуст

**End State (broken):**
Файлы существуют в директории сессии, но MCP не знает о них. Commit невозможен.

### Expected (Fixed) Flow

**Step-by-Step (должно быть):**
1. User: Создаёт сессию через `create_session("work-on-chapter")`
2. System: Сессия создана
3. User: Вызывает `resolve_path("acts/act-1/plan.md")`
4. System: Возвращает путь + информацию о source
5. User/Claude: Использует `Write` tool для записи
6. **User/Claude: Вызывает `track_file_change("acts/act-1/plan.md", "created")`** ← NEW
7. System: Добавляет в `cow_files`, обновляет статистику
8. User: Вызывает `commit_session()`
9. System: ✅ Копирует файлы из сессии в global, удаляет сессию

---

## Edge Cases & Behaviors

| Scenario | Expected Behavior |
|----------|-------------------|
| Claude writes directly without calling track | Warning in logs, file exists but not tracked |
| User calls track for non-existent file | Error: "File not found in session directory" |
| Session status is CRASHED | Provide `recover_session` tool to fix status |
| Multiple writes to same file | Update `cow_files` entry, don't duplicate |
| commit_session with cow_files=[] but files exist | Scan directory and auto-track before commit |

---

## Definition of Done (DoD)

### Must Have:
- [ ] New MCP tool `track_file_change(path, change_type)` that registers files in `cow_files`
- [ ] `commit_session` correctly copies all tracked files to global
- [ ] Status CRASHED can be fixed via `recover_session` tool
- [ ] Claude Code hook that auto-calls `track_file_change` after Write/Edit to session paths

### Nice to Have:
- [ ] `commit_session` auto-scans directory if `cow_files` is empty (fallback)
- [ ] Warning message when file exists in session but not tracked
- [ ] Integration status check in `/integrate-context` respects session tracking

---

## Technical Notes

### Root Causes

1. **Missing write/track tool**: `resolve_path` is read-only, `_add_cow_file` exists but never called
2. **CRASHED status persists**: Status written to `session.json` and never auto-recovered
3. **No directory scanning**: Commit only looks at `cow_files`, ignores actual filesystem

### Proposed Changes

#### Option A: Add `track_file_change` tool (Recommended)

```python
@mcp.tool(name="track_file_change")
async def track_file_change(params: TrackFileInput) -> str:
    """Register file as changed in session.

    Call AFTER writing file with Write/Edit tool.

    Args:
        path: Relative path (e.g., "acts/act-1/plan.md")
        change_type: "modified" | "created" | "deleted"
    """
    session = _get_active_session()
    if not session:
        return "❌ No active session"

    # Verify file exists in session directory
    session_file = Path(session["path"]) / params.path
    if not session_file.exists() and params.change_type != "deleted":
        return f"❌ File not found: {session_file}"

    # Track using existing function
    _add_cow_file(session["name"], params.path, params.change_type)

    return f"✅ Tracked: {params.path} ({params.change_type})"
```

#### Option B: Hook-based auto-tracking

Create `.claude/hooks/session_track_hook.py`:
```python
# Intercept Write/Edit tool calls
# If path starts with "workspace/sessions/", extract relative path and call MCP
```

#### Option C: Directory scan on commit

```python
# In commit_session, before copying:
if not session_data["cow_files"]:
    # Scan session directory for all files
    for file in session_path.rglob("*"):
        if file.is_file() and file.name != "session.json":
            rel_path = file.relative_to(session_path)
            _add_cow_file(session_name, str(rel_path), "created")
```

### Add `recover_session` tool

```python
@mcp.tool(name="recover_session")
async def recover_session(params: RecoverSessionInput) -> str:
    """Recover CRASHED session by resetting status to ACTIVE."""
    session_data = _load_session_data(params.name)

    if session_data.get("status") != "CRASHED":
        return f"Session '{params.name}' is not CRASHED"

    # Reset status
    session_data["status"] = SessionStatus.ACTIVE.value
    del session_data["crashed_at"]  # Remove crash timestamp

    _save_session_data(params.name, session_data)
    _update_session_lock(params.name)

    return f"✅ Session '{params.name}' recovered and activated"
```

---

## Open Questions

1. Should `track_file_change` be called automatically by a hook, or manually by Claude?
   - Auto: More reliable, but requires hook maintenance
   - Manual: Simpler, but relies on Claude remembering to call

2. What about files created before this fix?
   - Option: One-time migration script to scan and track
   - Option: Auto-scan on next commit

3. Windows path compatibility — are there issues with backslash vs forward slash?

---

## Ready for Technical Design: **Yes**

Next step: Implement Option A (track_file_change) + Option C (fallback scan) + recover_session tool.
