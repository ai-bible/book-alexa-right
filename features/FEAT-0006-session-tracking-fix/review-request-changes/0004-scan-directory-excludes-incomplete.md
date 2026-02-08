# Issue: Scan Directory Excludes List Incomplete

**Priority:** P3
**Category:** Code Quality / Completeness
**Files Affected:** `mcp-servers/session_utils.py:347-353`

---

## Problem Description

The `_scan_session_directory` function excludes specific system directories:

```python
# Lines 347-353
exclude_dirs = {
    "human-retries",
    "workflow-state",
    "generation-runs",
    "planning-runs",
    "artifacts"
}
```

However, the session structure (created in `_create_session_structure`) includes **more directories**:

```python
# Lines 213-224 (session_utils.py)
dirs = [
    session_path / "context" / "characters",
    session_path / "context" / "world-bible",
    session_path / "context" / "canon-levels",
    session_path / "context" / "plot-graph",
    session_path / "acts",
    session_path / "artifacts",        # ✓ excluded
    session_path / "human-retries",    # ✓ excluded
    session_path / "workflow-state",   # ✓ excluded
    session_path / "generation-runs",  # ✓ excluded
    session_path / "planning-runs",    # ✓ excluded
]
```

**Missing from excludes:** None currently, but future additions to session structure might be missed.

---

## Why This Is a Problem

**Impact:**
- **Future bug risk**: If new system directory added to session structure but not to `exclude_dirs`, it will be scanned and tracked
- **Inconsistency**: No single source of truth for "system directories"
- **Maintenance**: Must remember to update `exclude_dirs` when adding new session directories

**Example Scenario:**
1. Add `session_path / "temp-artifacts"` to session structure
2. Forget to add `"temp-artifacts"` to `exclude_dirs`
3. Files in temp directory get tracked and committed → pollution

**Violated Principles:**
- **Single Source of Truth**: System directories defined in multiple places
- **Fail-Safe Design**: Should exclude by default, include explicitly

---

## Root Cause

`exclude_dirs` is hardcoded separately from `_create_session_structure` instead of being derived from a shared constant.

---

## Systemic Solution

**Define system directories as module constant:**

```python
# At top of session_utils.py
SESSION_SYSTEM_DIRS = {
    "human-retries",
    "workflow-state",
    "generation-runs",
    "planning-runs",
    "artifacts"
}

# Optional: Define trackable directories explicitly
SESSION_CONTENT_DIRS = {
    "context",
    "acts"
}
```

**Update `_scan_session_directory`:**
```python
def _scan_session_directory(session_path: Path) -> list[tuple[str, int]]:
    tracked_files = []

    for item in session_path.rglob("*"):
        if item.is_dir():
            continue

        if item.name == "session.json":
            continue

        # Check if file is in system directory
        rel_parts = item.relative_to(session_path).parts
        if any(part in SESSION_SYSTEM_DIRS for part in rel_parts):
            continue

        # File is in content directory - track it
        rel_path = _normalize_session_path(item.relative_to(session_path))
        size_bytes = item.stat().st_size
        tracked_files.append((rel_path, size_bytes))

    return tracked_files
```

**Alternative (Whitelist Approach - More Explicit):**
```python
# Only scan specific content directories
for content_dir in ["context", "acts"]:
    content_path = session_path / content_dir
    if not content_path.exists():
        continue

    for item in content_path.rglob("*"):
        if item.is_file():
            rel_path = _normalize_session_path(item.relative_to(session_path))
            size_bytes = item.stat().st_size
            tracked_files.append((rel_path, size_bytes))
```

---

### Recommended Changes

**File:** `mcp-servers/session_utils.py`

**Add constant at module level (after imports):**
```python
# Line 22 (after imports)

# Constants

WORKSPACE_PATH = Path("workspace")
SESSIONS_PATH = WORKSPACE_PATH / "sessions"
SESSION_LOCK_FILE = WORKSPACE_PATH / "session.lock"

# System directories (not tracked in CoW)
SESSION_SYSTEM_DIRS = {
    "human-retries",
    "workflow-state",
    "generation-runs",
    "planning-runs",
    "artifacts"
}
```

**Update `_scan_session_directory`:**
```python
# Line 347-353
exclude_dirs = SESSION_SYSTEM_DIRS  # Use constant
```

**Add validation in `_create_session_structure`:**
```python
# Optional: Verify all created dirs are accounted for
CREATED_DIRS = {
    "context",
    "acts",
    "artifacts",
    "human-retries",
    "workflow-state",
    "generation-runs",
    "planning-runs"
}

# In _create_session_structure, add assertion:
assert all(
    any(str(d).endswith(system_dir) for system_dir in SESSION_SYSTEM_DIRS)
    for d in dirs if d.name in SESSION_SYSTEM_DIRS
), "SESSION_SYSTEM_DIRS out of sync with created directories"
```

---

## Related Issues

None currently, but this prevents future bugs.

---

## Testing

1. Create session
2. Add files to various directories (context, acts, artifacts, human-retries)
3. Run `_scan_session_directory`
4. Verify only context/ and acts/ files are returned

---

**Status:** ⏳ Pending Fix (Low priority - preventive measure)
