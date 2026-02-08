# Issue: Hook Has Redundant Tracking Logic vs MCP Tool

**Priority:** P2
**Category:** Code Quality / DRY Violation
**Files Affected:**
- `.claude/hooks/session_track_hook.py:119-176`
- `mcp-servers/session_utils.py:271-332`

---

## Problem Description

The hook implements its own version of file tracking logic in `_track_file_in_session()` (lines 119-176), which **duplicates** the logic already in `_add_cow_file()` in `session_utils.py`.

**Duplication:**
- Both check if file is already tracked
- Both update `change_type` if it changed
- Both maintain `changes` lists
- Both update `stats`
- Both use atomic write via temp file

**Difference:**
- Hook version: Direct JSON manipulation (faster, ~5ms)
- Utility version: Goes through `_load_session_data` / `_save_session_data` (~10-15ms)

---

## Why This Is a Problem

**Impact:**
- **Maintenance burden**: Bug fixes must be applied in TWO places
- **Inconsistency risk**: Logic might diverge over time
- **DRY violation**: Same business logic implemented twice

**Example:**
- If we fix the "created vs modified" logic in one place, must remember to fix the other
- If we add a new field to `cow_files` entries, must update both implementations

**Violated Principles:**
- **DRY (Don't Repeat Yourself)**: Core principle violated
- **Single Source of Truth**: Tracking logic should exist in ONE place

---

## Root Cause

Performance optimization (direct JSON update ~5ms faster) led to duplicating the logic instead of refactoring for performance.

---

## Systemic Solution

**Option A: Hook calls MCP tool (cleaner, slower)**
```python
# Hook calls track_file_change MCP tool via subprocess
subprocess.run([
    "python", "-m", "mcp",
    "track_file_change",
    f"--path={rel_path_str}",
    f"--change-type={change_type}"
], check=False)
```
- Clean separation
- ~50ms overhead (subprocess spawn)
- Not acceptable for PostToolUse hook (runs on every write)

**Option B: Extract shared tracking function (RECOMMENDED)**

Create `session_tracking_core.py` with minimal dependencies:
```python
def update_cow_tracking(
    session_data: dict,
    file_path: str,
    change_type: str,
    file_size_bytes: int
) -> dict:
    """Update CoW tracking in session data dict.

    Pure function - no I/O, just data transformation.

    Args:
        session_data: Session JSON data
        file_path: Normalized POSIX path
        change_type: "created" | "modified" | "deleted"
        file_size_bytes: File size in bytes

    Returns:
        Updated session_data dict
    """
    # ... shared logic here ...
```

**Both hook and utility use this:**
- Hook: `update_cow_tracking()` → direct write
- Utility: `update_cow_tracking()` → save via `_save_session_data()`

**Option C: Hook uses _add_cow_file directly (quick fix)**
```python
# Hook imports from session_utils
from session_utils import _add_cow_file

# Replace _track_file_in_session with:
_add_cow_file(session_name, rel_path_str, change_type)
```
- Simplest fix
- Slightly slower (~10ms extra) but acceptable for PostToolUse
- Eliminates duplication immediately

---

### Recommended Changes

**Immediate Fix (Option C):**

**File:** `.claude/hooks/session_track_hook.py`

**Current Code:**
```python
# Line 100
_track_file_in_session(session_name, session_path, rel_path_str, change_type)

# Lines 119-176: _track_file_in_session implementation
```

**Suggested Code:**
```python
# Add import at top
import sys
sys.path.insert(0, "mcp-servers")  # Add to path
from session_utils import _add_cow_file

# Line 100 - replace function call
try:
    _add_cow_file(session_name, rel_path_str, change_type)
except Exception as e:
    print(f"⚠️ [Session Track] Failed to track: {e}", file=sys.stderr)
    sys.exit(0)  # Graceful degradation

# Delete lines 119-201 (_track_file_in_session and _save_session_json)
```

**Long-term Fix (Option B):**
- Extract shared logic to `session_tracking_core.py`
- Refactor both hook and utility to use it
- Add comprehensive tests for tracking logic

---

## Related Issues

Any future changes to tracking logic must be aware of this duplication until fixed.

---

## Testing

After fix:
1. Write file in session
2. Verify hook still tracks correctly
3. Measure performance impact (<20ms acceptable)
4. Verify no regression in tracking accuracy

---

**Status:** ⏳ Pending Fix
