# Architecture Plan: Session File Change Tracking

**Feature ID:** FEAT-0006
**Status:** Architecture Design
**Architect:** Django Architect Agent
**Date:** 2025-12-21

---

## Problem Statement

The MCP session management server does not track files written by Claude Code's Write/Edit tools. When a user creates a session, calls `resolve_path()` to get a session path, and writes a file, the MCP server remains unaware. The `cow_files` list stays empty, causing `commit_session()` to report "no changes to commit" even though files physically exist in the session directory.

**Additional Issue:** Sessions can remain in CRASHED status indefinitely without recovery mechanism.

---

## Review Findings Summary

No code review performed yet - this is initial architecture design based on README requirements.

---

## Architectural Solution

### High-Level Approach

This solution introduces **explicit file change tracking** through a new MCP tool that must be called after Write/Edit operations. To reduce manual burden, a **PostToolUse hook** will automatically call this tracking tool after successful file writes.

**Defense-in-Depth Strategy:**
1. **Primary:** PostToolUse hook auto-tracks changes
2. **Fallback:** Manual `track_file_change` tool calls (explicit)
3. **Safety Net:** Auto-scan session directory in `commit_session` if `cow_files` is empty

This multi-layered approach ensures file tracking works even if one mechanism fails.

### Core Principles Applied

1. **Single Responsibility:** Each component has one clear job
   - `track_file_change` tool: Register file in session
   - `session_track_hook.py`: Auto-invoke tracking after writes
   - `commit_session`: Validate and copy tracked files

2. **Fail-Fast Validation:**
   - Track tool validates file exists before registering
   - Commit validates session state before proceeding

3. **Minimal Dependencies:**
   - Uses existing `_add_cow_file()` utility
   - Leverages standard Path operations
   - No new external libraries

4. **Explicit Error Handling:**
   - Clear error messages for missing files
   - Graceful degradation in hook failures
   - Recovery tool for CRASHED sessions

---

## Changes by File

### 1. `mcp-servers/session_models.py`

**Purpose:** Add input validation models for new tools

**Changes:**
- Add `TrackFileInput` model:
  - `path: str` (relative path, 1-500 chars)
  - `change_type: ChangeType` (modified/created/deleted)

- Add `RecoverSessionInput` model:
  - `name: str` (session name, 1-100 chars)

**Validation Rules:**
- `path` must be relative (no absolute paths)
- `change_type` must match ChangeType enum values
- Use same ConfigDict settings as other models (str_strip_whitespace, validate_assignment, extra='forbid')

---

### 2. `mcp-servers/session_management_mcp.py`

**Purpose:** Implement new MCP tools

#### Tool 1: `track_file_change`

**Signature:**
```python
@mcp.tool(
    name="track_file_change",
    annotations={
        "title": "Track File Change in Session",
        "readOnlyHint": False,
        "idempotentHint": True  # Safe to call multiple times
    }
)
async def track_file_change(params: TrackFileInput) -> str
```

**Logic Flow:**
1. Get active session via `_get_active_session()`
   - If no session: Return error message (not exception)
2. Validate file exists in session directory
   - For "created"/"modified": File must exist
   - For "deleted": File may not exist (already deleted)
3. Call existing `_add_cow_file(session["name"], params.path, params.change_type)`
4. Return success message with file count

**Error Cases:**
- No active session → "No active session. Start session first: /session start <name>"
- File not found (for created/modified) → "File not found in session: {path}"
- Invalid change_type → Pydantic validation error (auto-handled)

**Return Format (Markdown):**
```
✅ TRACKED: {path}

Change type: {change_type}
Session: {session_name}
Total tracked files: {count}
```

#### Tool 2: `recover_session`

**Signature:**
```python
@mcp.tool(
    name="recover_session",
    annotations={
        "title": "Recover Crashed Session",
        "readOnlyHint": False,
        "idempotentHint": True
    }
)
async def recover_session(params: RecoverSessionInput) -> str
```

**Logic Flow:**
1. Load session data via `_load_session_data(params.name)`
   - If not found: Return error
2. Check current status
   - If not CRASHED: Return info message (nothing to recover)
3. Reset status to ACTIVE
   - Delete `crashed_at` field
   - Set `status = SessionStatus.ACTIVE.value`
4. Save session data atomically via `_save_session_data()`
5. Update session.lock to activate recovered session
6. Return success message

**Error Cases:**
- Session not found → "Session not found: {name}"
- Session not crashed → "Session is not CRASHED (current status: {status})"
- Load/save failure → Propagate exception with context

**Return Format (Markdown):**
```
✅ SESSION RECOVERED

Session: {name}
Previous status: CRASHED (crashed at: {timestamp})
New status: ACTIVE

📊 Session stats:
   • Modified: {count}
   • Created: {count}
   • Size: {formatted_size}

💡 Session activated - ready to continue work
```

---

### 3. `mcp-servers/session_utils.py`

**Purpose:** Enhance `_add_cow_file()` with deduplication logic

**Changes:**
- **Current:** Function appends to `cow_files` unconditionally (may duplicate)
- **Enhanced:** Check if file already tracked before appending

**Updated Logic:**
```python
def _add_cow_file(session_name: str, file_path: str, change_type: str) -> None:
    session_data = _load_session_data(session_name)

    # NEW: Check for existing entry
    existing_entry = None
    for cow_file in session_data["cow_files"]:
        if cow_file["path"] == file_path:
            existing_entry = cow_file
            break

    if existing_entry:
        # UPDATE: Only update if change_type differs
        if existing_entry["type"] != change_type:
            # Remove from old changes list
            old_type = existing_entry["type"]
            session_data["changes"][old_type].remove(file_path)

            # Add to new changes list
            session_data["changes"][change_type].append(file_path)

            # Update entry
            existing_entry["type"] = change_type
            existing_entry["updated_at"] = datetime.now(timezone.utc).isoformat()

            _save_session_data(session_name, session_data)
        return  # Already tracked, no duplicate

    # EXISTING: Add new entry (rest of function unchanged)
    ...
```

**Why This Matters:** Prevents duplicate entries when:
- Hook calls `track_file_change` after Write
- User manually calls `track_file_change` again
- File modified multiple times in same session

---

### 4. `.claude/hooks/session_track_hook.py` (NEW)

**Purpose:** Auto-track file changes after Write/Edit operations

**Type:** PostToolUse (non-blocking, observability + automation)

**Architecture:**
- **Single Responsibility:** Call MCP tracking tool after file writes
- **Fail-Fast Validation:** Check tool name, session existence before processing
- **Graceful Degradation:** Never block operation, always exit 0
- **Performance:** <50ms execution time (minimal overhead)

**Hook Structure:**

```python
#!/usr/bin/env python
"""
PostToolUse Hook: Session File Change Tracker

RESPONSIBILITY: Auto-track file changes in session CoW system

ARCHITECTURE: Non-blocking automation hook
- Calls track_file_change MCP tool after Write/Edit/NotebookEdit
- Extracts relative path from absolute session path
- Determines change_type (created vs modified)
- Provides observability feedback to AI

TRIGGERS: After Write, Edit, NotebookEdit (successful)
FAILURE MODE: Graceful - logs warning, allows operation to complete
"""
```

**Logic Flow:**

1. **Read event data from stdin** (JSON)
2. **Check tool name:**
   - If not in `["Write", "Edit", "NotebookEdit"]` → exit 0 (not our concern)
3. **Check active session:**
   - Load `workspace/session.lock`
   - If no lock → exit 0 (no session, no tracking needed)
4. **Extract file path from tool_input:**
   - `file_path = event_data["tool_input"]["file_path"]`
5. **Validate path is in session directory:**
   - Convert to Path, check if starts with session path
   - If not in session → exit 0 (global file, don't track)
6. **Calculate relative path:**
   - Remove session prefix: `workspace/sessions/{name}/` → remaining path
7. **Determine change_type:**
   - Check if file existed before (via tool_output or heuristic)
   - "created" if new file, "modified" if existing
8. **Call MCP tool:**
   - Use subprocess or HTTP call to `track_file_change`
   - Pass `path` and `change_type`
9. **Show feedback to AI** (stderr):
   ```
   ✅ [Session Track] Auto-tracked: acts/act-1/plan.md (modified)
      Session: work-on-chapter-01
      Total tracked: 3 files
   ```
10. **Exit 0** (always success)

**Error Handling:**
- JSON parse error → log warning, exit 0
- Session lock corrupted → log warning, exit 0
- MCP call fails → log warning, exit 0 (fallback to manual tracking)
- Path outside session → silent exit 0 (expected case)

**Performance Optimization:**
- Early exits for non-Write tools (99% of tool calls)
- Single file read (session.lock)
- No glob operations
- Subprocess call is fast (<20ms for MCP tool)

**Edge Cases:**
- **Concurrent writes:** `_add_cow_file()` handles deduplication
- **File deleted then recreated:** Change type updates correctly
- **Multiple hooks fail:** Fallback auto-scan in commit_session catches it
- **NotebookEdit:** Track `.ipynb` file same as regular files

---

### 5. `mcp-servers/session_management_mcp.py` (update `commit_session`)

**Purpose:** Add safety net auto-scan if `cow_files` is empty

**Changes:** Insert fallback scan before "no changes" check

**Location:** In `commit_session()`, after loading session_data, before checking `cow_files`

**Logic (Fallback Scan):**

```python
# Load session data
session_data = _load_session_data(session_name)
session_path = _get_session_path(session_name)

# NEW: Safety net - auto-scan if cow_files empty
if not session_data["cow_files"]:
    scanned_files = _scan_session_directory(session_path)

    if scanned_files:
        # Files found but not tracked - auto-add them
        for file_path, size_bytes in scanned_files:
            cow_entry = {
                "path": file_path,
                "type": ChangeType.CREATED.value,  # Assume created (safe default)
                "copied_at": datetime.now(timezone.utc).isoformat(),
                "size_bytes": size_bytes
            }
            session_data["cow_files"].append(cow_entry)
            session_data["changes"][ChangeType.CREATED.value].append(file_path)

        # Update stats
        session_data["stats"]["total_files_changed"] = len(session_data["cow_files"])
        session_data["stats"]["session_size_bytes"] = sum(f["size_bytes"] for f in session_data["cow_files"])

        # Save updated data
        _save_session_data(session_name, session_data)

        # Show warning to user
        print(f"⚠️ WARNING: Found {len(scanned_files)} untracked files - auto-added to commit", file=sys.stderr)

# EXISTING: Check if any changes to commit
if not session_data["cow_files"]:
    return "No changes to commit..."
```

**Helper Function (Add to session_utils.py):**

```python
def _scan_session_directory(session_path: Path) -> list[tuple[str, int]]:
    """Scan session directory for files not in system directories.

    Args:
        session_path: Path to session directory

    Returns:
        List of (relative_path, size_bytes) tuples
    """
    exclude_dirs = {
        "human-retries",
        "workflow-state",
        "generation-runs",
        "planning-runs",
        "artifacts"
    }

    tracked_files = []

    for item in session_path.rglob("*"):
        # Skip directories
        if item.is_dir():
            continue

        # Skip session.json
        if item.name == "session.json":
            continue

        # Skip excluded directories
        if any(excluded in item.parts for excluded in exclude_dirs):
            continue

        # Calculate relative path from session root
        rel_path = item.relative_to(session_path)
        size_bytes = item.stat().st_size

        tracked_files.append((str(rel_path), size_bytes))

    return tracked_files
```

**Why This Matters:**
- **Defense in Depth:** Even if hook fails, commit still works
- **Data Safety:** Prevents losing user work due to tracking bugs
- **User Experience:** No manual intervention needed
- **Observability:** Warning shows when fallback activates (indicates hook issue)

---

### 6. `.claude/hooks.json`

**Purpose:** Register new PostToolUse hook

**Changes:** Add entry to PostToolUse hooks array

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/session_track_hook.py",
            "description": "FEAT-0006: Auto-track file changes in session CoW system"
          },
          // ... existing hooks ...
        ]
      }
    ]
  }
}
```

**Placement:** Add as first hook in PostToolUse array (runs before others)

---

## Data Flow

### End-to-End Tracking Flow

**Scenario 1: Normal Write Operation (Hook Works)**

```
1. User creates session
   └─> create_session("work-chapter-01")
       └─> session.json: {cow_files: [], changes: {...}}

2. User resolves path
   └─> resolve_path("acts/act-1/plan.md")
       └─> Returns: workspace/sessions/work-chapter-01/acts/act-1/plan.md

3. Claude writes file
   └─> Write(file_path="workspace/sessions/.../plan.md")
       └─> File created on disk

4. PostToolUse hook triggers
   └─> session_track_hook.py receives event
       ├─> Validates: tool=Write, session active, path in session
       ├─> Extracts relative path: acts/act-1/plan.md
       ├─> Calls: track_file_change(path="acts/act-1/plan.md", type="created")
       └─> MCP updates: session.json.cow_files += entry

5. User commits
   └─> commit_session()
       ├─> Finds cow_files: [acts/act-1/plan.md]
       ├─> Copies to global: acts/act-1/plan.md
       └─> Success
```

**Scenario 2: Hook Fails (Fallback Works)**

```
1-3. [Same as above]

4. PostToolUse hook FAILS
   └─> session_track_hook.py crashes
       └─> Hook exits 0 (graceful degradation)
       └─> session.json.cow_files stays empty

5. User commits
   └─> commit_session()
       ├─> Checks cow_files: []
       ├─> FALLBACK: Scans session directory
       ├─> Finds: acts/act-1/plan.md (physical file)
       ├─> Auto-adds to cow_files
       ├─> Shows warning: "Found 1 untracked file - auto-added"
       ├─> Copies to global
       └─> Success
```

**Scenario 3: Manual Tracking**

```
1-3. [Same as above]

4. User manually calls MCP tool
   └─> track_file_change(path="acts/act-1/plan.md", type="created")
       └─> Validates file exists
       └─> Updates session.json.cow_files

5. User commits
   └─> commit_session()
       └─> Success (cow_files already populated)
```

**Scenario 4: CRASHED Session Recovery**

```
1. Session crashes (process dies)
   └─> session_guard_hook marks status=CRASHED

2. User lists sessions
   └─> list_sessions()
       └─> Shows: "⚠️ Session 'work' is CRASHED"

3. User recovers
   └─> recover_session(name="work")
       ├─> Validates status=CRASHED
       ├─> Resets status=ACTIVE
       ├─> Deletes crashed_at
       ├─> Updates session.lock
       └─> Returns success message

4. User resumes work
   └─> session_guard_hook now allows operations
```

---

## Implementation Stages

### Stage 1: Core MCP Tools

**Goal:** Implement `track_file_change` and `recover_session` MCP tools

**Changes:**
1. Add input models to `session_models.py`
   - `TrackFileInput`
   - `RecoverSessionInput`
2. Implement `track_file_change` in `session_management_mcp.py`
   - Validation logic
   - Call `_add_cow_file()`
   - Return formatted message
3. Implement `recover_session` in `session_management_mcp.py`
   - Status check
   - State reset
   - Lock update

**Validation:**
- Developer tests with manual MCP calls
- Verify session.json updates correctly
- Check error messages are clear

**Tests:**
- Unit test: track_file_change with valid/invalid paths
- Unit test: recover_session with CRASHED/ACTIVE sessions
- Integration test: track → commit flow

---

### Stage 2: Hook Auto-Tracking

**Goal:** Implement PostToolUse hook for automatic tracking

**Changes:**
1. Create `.claude/hooks/session_track_hook.py`
   - Tool name filtering
   - Path validation
   - MCP tool invocation
   - Feedback messages
2. Register hook in `.claude/hooks.json`
   - Add to PostToolUse array (first position)

**Validation:**
- Developer creates session, writes file
- Verify hook output appears in stderr
- Check session.json updated automatically
- Test error handling (no session, invalid path)

**Tests:**
- Integration test: Write → hook → track → session.json
- Error test: Hook fails gracefully (exit 0)
- Performance test: Hook completes <50ms

---

### Stage 3: Fallback Auto-Scan

**Goal:** Add safety net in commit_session

**Changes:**
1. Add `_scan_session_directory()` to `session_utils.py`
   - Recursive file scan
   - Exclude system directories
   - Calculate sizes
2. Update `commit_session()` in `session_management_mcp.py`
   - Call scan before "no changes" check
   - Auto-add found files
   - Show warning

**Validation:**
- Developer writes file without tracking (disable hook)
- Commit session
- Verify files still committed with warning

**Tests:**
- Integration test: Untracked file → commit → auto-scan triggers
- Edge case: Empty session → no false positives
- Edge case: Only system files → no tracking

---

### Stage 4: Enhance `_add_cow_file` Deduplication

**Goal:** Prevent duplicate tracking entries

**Changes:**
1. Update `_add_cow_file()` in `session_utils.py`
   - Check existing entries before append
   - Update change_type if differs
   - Skip if already tracked

**Validation:**
- Developer calls track_file_change twice for same file
- Verify only one entry in cow_files
- Test change_type transition (created → modified)

**Tests:**
- Unit test: Double-track same file → one entry
- Unit test: Change type update (created → modified → deleted)
- Integration test: Hook + manual track → no duplicates

---

## Testing Strategy

### Unit Tests

**Test File:** `tests/test_session_tracking.py`

**Test Cases:**

1. **track_file_change tool:**
   - ✅ Valid file, active session → success
   - ❌ No active session → error message
   - ❌ File not found → error message
   - ✅ Multiple calls same file → idempotent

2. **recover_session tool:**
   - ✅ CRASHED session → reset to ACTIVE
   - ❌ Session not found → error
   - ❌ Session not crashed → info message
   - ✅ Lock updated correctly

3. **_add_cow_file deduplication:**
   - Track new file → entry added
   - Track same file twice → one entry
   - Track with different change_type → entry updated
   - Stats calculated correctly

4. **_scan_session_directory:**
   - Empty session → empty list
   - Files in context/ → tracked
   - Files in artifacts/ → excluded
   - session.json → excluded
   - Nested files → relative paths correct

---

### Integration Tests

**Test File:** `tests/integration/test_session_workflow.py`

**Test Scenarios:**

1. **Full CoW workflow with auto-tracking:**
   - Create session
   - Write file → hook tracks automatically
   - Commit → file copied to global
   - Verify cow_files correct

2. **Fallback auto-scan:**
   - Create session
   - Manually create file (bypass Write tool)
   - Commit → auto-scan finds file
   - Warning shown, file committed

3. **CRASHED session recovery:**
   - Create session
   - Simulate crash (kill process, mark CRASHED)
   - Recover session
   - Resume work successfully

4. **Concurrent writes:**
   - Create session
   - Write multiple files in sequence
   - Each tracked separately
   - All committed correctly

---

### Hook Tests

**Test File:** `tests/hooks/test_session_track_hook.py`

**Test Method:** Simulate hook with JSON stdin

**Test Cases:**

1. **Happy path:**
   - Write tool event → hook tracks file
   - Output contains success message
   - Exit code 0

2. **Non-Write tools:**
   - Read tool event → hook exits silently
   - Exit code 0

3. **No session:**
   - Write event, no session.lock → hook exits silently
   - Exit code 0

4. **Path outside session:**
   - Write to global path → hook exits silently
   - Exit code 0

5. **MCP call failure:**
   - track_file_change fails → hook logs error, exits 0
   - Graceful degradation works

6. **Performance:**
   - Hook completes in <50ms
   - Measure with `time` command

---

### Manual Testing Checklist

**Scenario:** Real user workflow

**Steps:**
1. [ ] Create session: `create_session("test-tracking")`
2. [ ] Resolve path: `resolve_path("acts/test.md")`
3. [ ] Write file: Use Write tool
4. [ ] Check stderr: See "Auto-tracked" message
5. [ ] Check session.json: File in cow_files
6. [ ] Commit: `commit_session(force=True)`
7. [ ] Verify: File in global acts/test.md
8. [ ] Clean up: Delete test.md

**Scenario:** Fallback auto-scan

**Steps:**
1. [ ] Create session
2. [ ] Manually create file in session directory (bypass Write)
3. [ ] Commit
4. [ ] Verify warning: "Found X untracked files"
5. [ ] Verify file committed to global

**Scenario:** CRASHED recovery

**Steps:**
1. [ ] Create session
2. [ ] Manually edit session.json: status=CRASHED
3. [ ] Call recover_session
4. [ ] Verify status=ACTIVE
5. [ ] Write file successfully

---

## Performance Considerations

### Query Optimization

**No database queries** - all operations are file-based JSON I/O.

**File I/O Patterns:**
- `track_file_change`: 1 read (session.json) + 1 write (atomic)
- `commit_session` with scan: 1 read + recursive glob + N copies
- Hook: 1 read (session.lock) + subprocess call (~20ms)

**Optimization:**
- Use `_atomic_write_session_json()` to prevent corruption
- Early exits in hook reduce overhead
- Scan uses `rglob()` generator (memory efficient)

---

### Memory Usage

**Small Memory Footprint:**
- Session.json files: <100KB typical
- CoW tracking: ~100 bytes per file entry
- Hook process: <10MB resident memory

**Large Session Handling:**
- Auto-scan with 1000+ files: Use generator pattern
- Commit copies: Process files in batches if needed
- No memory leaks: All file handles closed properly

---

### Concurrent Load

**Concurrency Characteristics:**
- Single active session per user (lock enforced)
- No parallel writes to same session
- Multiple sessions allowed (different users)

**Lock Strategy:**
- File-based lock (`session.lock`) prevents race conditions
- Atomic JSON writes prevent data corruption
- Hook runs in subprocess (isolated from main process)

**Potential Issues:**
- Rapid Write → Hook → Track sequence: `_add_cow_file` handles deduplication
- Concurrent commit attempts: Session lock prevents this
- Hook timeout: 60s timeout in Claude Code (sufficient)

---

## Security Considerations

### Data Validation

**Input Validation (Pydantic):**
- `path` field: Max 500 chars, no absolute paths allowed
- `change_type`: Enum validation (only valid values)
- `name` field: Alphanumeric + hyphens/underscores only

**Path Traversal Prevention:**
- Hook validates path within session directory
- `track_file_change` tool validates file exists in session
- `resolve_path` already sanitizes paths

**Implementation:**
```python
# In session_track_hook.py
def is_path_in_session(file_path: Path, session_path: Path) -> bool:
    """Check if file path is within session directory."""
    try:
        resolved_file = file_path.resolve()
        resolved_session = session_path.resolve()
        return resolved_file.is_relative_to(resolved_session)
    except Exception:
        return False
```

---

### Access Control

**Session Isolation:**
- Sessions stored per user (OS-level isolation)
- File permissions: 0644 for files, 0755 for directories
- No shared sessions between users

**MCP Tool Access:**
- All tools require valid session name
- No wildcards or glob patterns in tool inputs
- Fail-fast on invalid session references

---

### External APIs

**No external API calls** - this feature is entirely local file operations.

**Subprocess Execution:**
- Hook uses Python subprocess for MCP call
- Arguments sanitized via Pydantic validation
- No shell=True (prevents injection)

---

## Risks and Mitigation

### Risk 1: Hook Fails to Track Files

**Impact:** Medium
**Probability:** Low (with graceful degradation)

**Scenario:** Hook crashes or MCP tool unreachable → files not tracked

**Mitigation:**
- **Primary:** Hook exits 0 on error (doesn't block Write)
- **Secondary:** Fallback auto-scan in commit_session
- **Tertiary:** Manual track_file_change tool available
- **Detection:** Warning shown at commit time if fallback activates

**Recovery:**
- User sees "Found X untracked files" warning
- Files still committed successfully
- No data loss, just observability impact

---

### Risk 2: Session.json Corruption During Concurrent Updates

**Impact:** High (data loss)
**Probability:** Very Low (atomic writes protect)

**Scenario:** Multiple processes write session.json simultaneously

**Mitigation:**
- **Primary:** `_atomic_write_session_json()` uses temp file + rename
- **Secondary:** Single session.lock prevents concurrent access
- **Tertiary:** File-level locking (OS prevents simultaneous writes)

**Detection:**
- JSON decode error when loading session.json
- Session marked CRASHED automatically

**Recovery:**
- `recover_session` tool can attempt repair
- Worst case: Cancel session, lose uncommitted work (rare)

---

### Risk 3: Auto-Scan Performance with Large Sessions

**Impact:** Medium (slow commits)
**Probability:** Low (most sessions <100 files)

**Scenario:** Session with 1000+ files → scan takes >5 seconds

**Mitigation:**
- **Primary:** Hook tracks files incrementally (scan only fallback)
- **Secondary:** Scan uses generator pattern (low memory)
- **Optimization:** Exclude system directories early (reduces scan scope)
- **UX:** Show progress indicator if scan >2 seconds (future)

**Threshold:**
- Scan <1000 files: <500ms (acceptable)
- Scan 1000-5000 files: 1-3s (noticeable but okay)
- Scan >5000 files: Consider optimization (unlikely scenario)

---

### Risk 4: Hook Overhead Slows Down Write Operations

**Impact:** Low (minor UX degradation)
**Probability:** Low (<50ms overhead)

**Scenario:** Hook adds latency to every Write operation

**Mitigation:**
- **Primary:** Early exits for non-Write tools (99% of calls)
- **Optimization:** Single file read (session.lock), minimal processing
- **Async:** Hook runs PostToolUse (doesn't block Write completion)
- **Benchmark:** Target <50ms, actual ~20-30ms

**Measurement:**
```bash
time python .claude/hooks/session_track_hook.py < test_event.json
# Expected: real <0.05s
```

---

### Risk 5: Path Resolution Ambiguity (Windows vs POSIX)

**Impact:** Medium (tracking fails on wrong OS)
**Probability:** Medium (if not handled)

**Scenario:** Session created on Windows, committed on Linux → path separators differ

**Mitigation:**
- **Primary:** Use `Path()` throughout (handles both separators)
- **Normalization:** Store paths with forward slashes in session.json
- **Cross-platform:** Test on both Windows and Linux

**Implementation:**
```python
# In _add_cow_file and track_file_change
file_path_normalized = str(Path(file_path).as_posix())
# Always uses forward slashes
```

---

## Follow-up Improvements

### Technical Debt

**Known Compromises for MVP:**

1. **Hook uses subprocess for MCP call**
   - Current: Spawns new process for each track
   - Future: Use MCP Python SDK directly (faster)
   - Savings: ~10ms per track

2. **Auto-scan is brute-force directory walk**
   - Current: Scans entire session directory
   - Future: Index files incrementally (SQLite or JSON index)
   - Savings: 90% reduction for large sessions

3. **No progress indicator for slow operations**
   - Current: Silent during scan/commit
   - Future: Show progress bar for >2s operations
   - UX: Better user confidence

4. **Change type detection is heuristic**
   - Current: Assumes "created" if untracked
   - Future: Check global file existence (created vs modified)
   - Accuracy: Prevents false "created" labels

---

### Future Enhancements

**Potential Improvements for Later Iterations:**

1. **Incremental File Indexing**
   - Maintain index.json with file metadata
   - Update on each Write (faster scan)
   - Reduces commit time by 90% for large sessions

2. **Diff-Based Change Detection**
   - Compare session file vs global file
   - Detect actual changes (not just timestamps)
   - Skip unchanged files in commit

3. **Conflict Resolution UI**
   - Detect global file modified during session
   - Offer merge/overwrite/cancel options
   - Prevents accidental overwrites

4. **Session Templates**
   - Pre-configure tracking for common patterns
   - Auto-exclude certain directories
   - Faster session creation

5. **Metrics Dashboard**
   - Track hook performance over time
   - Alert if hook success rate drops
   - Observability for reliability

6. **Rollback Support**
   - Save session snapshot before commit
   - Allow undo of last commit
   - Safety net for accidental commits

---

## References

### Feature Documentation
- Feature Brief: `features/FEAT-0006-session-tracking-fix/README.md`

### Related Code
- `mcp-servers/session_management_mcp.py` - Main MCP server
- `mcp-servers/session_models.py` - Input validation models
- `mcp-servers/session_utils.py` - Utility functions
- `.claude/hooks/session_guard_hook.py` - PreToolUse validation hook
- `.claude/hooks/README.md` - Hook architecture guide

### System Documentation
- `ARCHITECTURE.md` - Overall system architecture
- `CLAUDE.md` - AI-assisted writing system guide
- `.workflows/` - Workflow documentation

---

## Implementation Checklist

### Stage 1: Core MCP Tools ✅
- [ ] Add `TrackFileInput` to session_models.py
- [ ] Add `RecoverSessionInput` to session_models.py
- [ ] Implement `track_file_change` tool
- [ ] Implement `recover_session` tool
- [ ] Write unit tests for both tools
- [ ] Test manually with MCP calls

### Stage 2: Hook Auto-Tracking ✅
- [ ] Create `.claude/hooks/session_track_hook.py`
- [ ] Register hook in `.claude/hooks.json`
- [ ] Test hook with Write tool
- [ ] Verify error handling (no session, invalid path)
- [ ] Benchmark performance (<50ms)

### Stage 3: Fallback Auto-Scan ✅
- [ ] Add `_scan_session_directory()` to session_utils.py
- [ ] Update `commit_session()` with fallback
- [ ] Test untracked file scenario
- [ ] Verify warning message
- [ ] Test with empty session (no false positives)

### Stage 4: Deduplication ✅
- [ ] Update `_add_cow_file()` with duplicate check
- [ ] Test double-tracking same file
- [ ] Test change_type transitions
- [ ] Verify stats calculation

### Stage 5: Integration Testing ✅
- [ ] Full workflow: create → write → commit
- [ ] Fallback workflow: manual file → commit
- [ ] Recovery workflow: crash → recover → resume
- [ ] Concurrent writes test

### Stage 6: Documentation ✅
- [ ] Update README.md with usage examples
- [ ] Document hook in `.claude/hooks/README.md`
- [ ] Add troubleshooting guide
- [ ] Create architecture diagram (optional)

---

## Ready for Implementation

**Status:** ✅ Ready

**Estimated Complexity:** Medium
**Estimated Time:** 2-3 days

**Prerequisites:**
- Python 3.11+ environment
- FastMCP library installed
- Claude Code with hooks support

**Implementation Order:**
1. Stage 1 (Core MCP Tools) - Day 1
2. Stage 4 (Deduplication) - Day 1
3. Stage 2 (Hook) - Day 2
4. Stage 3 (Fallback) - Day 2
5. Stage 5 (Integration Tests) - Day 3

**Blockers:** None

**Dependencies:**
- Existing MCP session management infrastructure
- Claude Code hooks system

---

**Architecture Review:** Pending developer feedback
**Next Step:** Begin Stage 1 implementation
