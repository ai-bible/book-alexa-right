---
name: session
description: >-
  This skill should be used when the user asks to "start session", "create session",
  "session status", "session list", "commit session", "cancel session", "switch session",
  "record retry", "/session", "/retry", "создать сессию", "начать сессию",
  "статус сессии", "закоммитить сессию", "отменить сессию", "переключить сессию",
  or mentions isolated work sessions, Copy-on-Write file handling, or human retry tracking.
  Provides session lifecycle management with CoW isolation for safe book editing.
---

# Session Management

User-friendly interface for managing isolated book writing sessions with
Copy-on-Write file handling. Backend: MCP Server `session_management_mcp`.

## Commands

### `/session start <name> [description]`

Create new session and activate it with CoW isolation.

```
/session start work-on-chapter-01
/session start experimental-scene-0102 "Trying alternative version"
```

MCP call: `create_session(name, description)`

Creates empty session directory (~10 KB), sets up CoW tracking,
updates `workspace/session.lock`.

### `/session list`

List all sessions with status indicators.

MCP call: `list_sessions()`

Shows table: name, status (ACTIVE/INACTIVE/CRASHED), created date, change count.

### `/session status`

Show detailed status of active session: metadata, modified/created files,
human retry count, session size.

MCP call: `get_active_session()`

### `/session switch <name>`

Switch to a different existing session. Updates `workspace/session.lock`.

MCP call: `switch_session(name)`

Error if session not found or CRASHED.

### `/session commit [name]`

Commit session changes to global files. Two-step process:

1. First call (preview): shows files to overwrite, requires confirmation
2. Second call with `force=True`: executes commit, archives retries, removes session

MCP calls: `commit_session(name, force=False)` then `commit_session(name, force=True)`

### `/session cancel [name]`

Cancel session, discard all changes. Global files remain untouched.
Human retries backed up to `workspace/retries-archive/`.

MCP call: `cancel_session(name, backup_retries=True)`

### `/retry <file> <reason>`

Record human retry attempt for a file within active session.

```
/retry scene-0101.md "Too much exposition, needs more action"
```

MCP call: `record_human_retry(file_path, reason, auto_detected=False)`

Copies current version to `human-retries/`, saves reason, assigns retry number.

AI can also auto-detect retry requests from user feedback and call with
`auto_detected=True`.

## MCP Tool Mapping

| Command | MCP Tool | Key Parameters |
|---------|----------|----------------|
| `start <name> [desc]` | `create_session` | `name, description` |
| `list` | `list_sessions` | — |
| `status` | `get_active_session` | — |
| `switch <name>` | `switch_session` | `name` |
| `commit [name]` | `commit_session` | `name, force` |
| `cancel [name]` | `cancel_session` | `name, backup_retries` |
| `/retry <file> <reason>` | `record_human_retry` | `file_path, reason, auto_detected` |

## Copy-on-Write Overview

Sessions use CoW for efficient isolation:

1. **Create** — empty directory structure only (~10 KB)
2. **First write** — file copied from global to session, then modified
3. **Subsequent writes** — modify session copy directly (no re-copy)
4. **Read** — check session first, fall back to global
5. **Commit** — copy all CoW files from session to global
6. **Cancel** — delete session directory, global untouched

For detailed CoW mechanics and file resolution logic, see
`references/cow-details.md`.

## Error Messages

Provide clear, actionable errors:

- No active session → suggest `/session start` or `/session list`
- Session not found → suggest `/session list`
- Session CRASHED → suggest `/session cancel <name>`
- File not found → show checked paths (session + global)

## Argument Parsing

1. Extract subcommand: `start`, `list`, `status`, `switch`, `commit`, `cancel`
2. Extract session name (if provided)
3. Extract description/reason (quoted string, if provided)
4. Validate session name format (alphanumeric, hyphens, underscores)
5. Map to MCP tool and call

## Additional Resources

### Reference Files

- **`references/cow-details.md`** — Detailed Copy-on-Write mechanics, file resolution,
  commit/cancel logic
- **`references/interaction-patterns.md`** — User interaction patterns: full lifecycle,
  retry workflow, experimental sessions, parallel sessions, commit workflow

## Integration

Requires MCP server `session_management_mcp`. Verify with `/mcp list`.

If not loaded: check `mcp-servers/session_management_mcp.py`, add to MCP config,
restart Claude Code.
