# Issue: Windows Path Separator Inconsistency Risk

**Priority:** P1
**Category:** Cross-Platform Compatibility
**Files Affected:**
- `.claude/hooks/session_track_hook.py:89`
- `mcp-servers/session_utils.py:372`

---

## Problem Description

The code uses `.as_posix()` to convert paths to forward slashes for storage:

```python
# session_track_hook.py:89
rel_path_str = str(rel_path.as_posix())  # Cross-platform

# session_utils.py:372
rel_path = str(item.relative_to(session_path).as_posix())
```

However, when comparing or matching paths elsewhere in the codebase, Windows backslashes `\` might cause mismatches if:
1. Some code uses native paths (`Path.resolve()` returns Windows paths with `\`)
2. Session.json stores POSIX paths (`acts/act-1/plan.md`)
3. Comparison happens without normalization

---

## Why This Is a Problem

**Impact:**
- **File tracking failures**: Files might not be matched correctly when checking `cow_files`
- **Duplicate entries**: Same file could be added twice with different path separators
- **Windows-specific bug**: Only manifests on Windows, making it hard to detect in testing

**Example Scenario:**
```python
# session.json stores:
{"path": "acts/act-1/plan.md", ...}

# Later code checks:
file_path = Path("acts\\act-1\\plan.md")  # Windows native
if str(file_path) in cow_files:  # MISMATCH: "acts\\act-1\\plan.md" != "acts/act-1/plan.md"
    ...
```

**Violated Principles:**
- **Cross-platform compatibility**: Code should work identically on Windows/Linux/macOS
- **Data consistency**: Same logical path should have single canonical representation

---

## Root Cause

Inconsistent path normalization across codebase. Some places use `.as_posix()`, others use native paths.

---

## Systemic Solution

**Enforce POSIX paths everywhere in session tracking:**

1. **Storage**: Always store paths with forward slashes (already done via `.as_posix()`)
2. **Comparison**: Always normalize paths before comparison
3. **Utilities**: Create helper function for path normalization

### Recommended Changes

**File:** `mcp-servers/session_utils.py`

**Add utility function:**
```python
def _normalize_session_path(path: str | Path) -> str:
    """Normalize path to POSIX format for session tracking.

    Args:
        path: Path string or Path object

    Returns:
        Path string with forward slashes (cross-platform)
    """
    if isinstance(path, str):
        path = Path(path)
    return str(path.as_posix())
```

**Update `_add_cow_file`:**
```python
def _add_cow_file(session_name: str, file_path: str, change_type: str) -> None:
    # Normalize path to POSIX
    file_path_normalized = _normalize_session_path(file_path)

    # ... rest of function uses file_path_normalized
```

**Update `_scan_session_directory`:**
```python
# Line 372 - already correct, but add comment
rel_path = _normalize_session_path(item.relative_to(session_path))
```

**Update hook:**
```python
# Line 89 - already correct, but use utility
rel_path_str = _normalize_session_path(rel_path)
```

**Update `commit_session` when checking paths:**
```python
# When iterating cow_files, always use normalized paths
for cow_file in session_data["cow_files"]:
    file_path = _normalize_session_path(cow_file["path"])
    # ... rest of logic
```

---

## Related Issues

Any code that compares paths against `cow_files` entries must normalize first. Audit points:
- `track_file_change` tool (line 378 in session_management_mcp.py)
- `_add_cow_file` function (session_utils.py)
- Hook's `_track_file_in_session` (session_track_hook.py:136)

---

## Testing

**Test on Windows:**
1. Create session
2. Write file `acts\act-1\plan.md` (native Windows path)
3. Verify session.json stores `acts/act-1/plan.md` (POSIX)
4. Write same file again
5. Verify it updates existing entry (not duplicates)

**Test on Linux/macOS:**
1. Same test with forward slashes
2. Verify identical behavior

---

**Status:** ⏳ Pending Fix
