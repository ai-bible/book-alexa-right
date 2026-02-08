# Issue: Hook Change Type Detection Logic Inconsistency

**Priority:** P2
**Category:** Code Quality / Logic
**Files Affected:** `.claude/hooks/session_track_hook.py:97`

---

## Problem Description

The hook uses a simplistic heuristic to determine `change_type`:

```python
# Line 97
change_type = "created" if tool_name == "Write" else "modified"
```

This assumes:
- `Write` always creates new files → `"created"`
- `Edit` always modifies existing files → `"modified"`

However, this is **incorrect**:
- `Write` tool can **overwrite** existing files (should be `"modified"`)
- The hook has no way to distinguish between file creation vs. overwrite

---

## Why This Is a Problem

**Impact:**
- **Incorrect tracking**: Files overwritten with `Write` will be tracked as `"created"` instead of `"modified"`
- **Session statistics inaccurate**: `changes["created"]` vs `changes["modified"]` lists will be wrong
- **Audit trail confusion**: Reviewing session changes will show incorrect change types

**Violated Principles:**
- **Correctness**: Logic doesn't match actual file operations
- **Explicit Error Handling**: No validation that assumption holds

---

## Root Cause

The hook runs **after** the write operation completes, so it can't check if the file existed before the write. The simplistic heuristic is a best-effort guess but is fundamentally flawed.

---

## Systemic Solution

**Option A: Check file existence BEFORE write (requires PreToolUse hook)**
- Add `PreToolUse` hook that records file existence state
- `PostToolUse` hook reads this state to determine change type
- More complex but accurate

**Option B: Always use "modified" for safety**
```python
# Conservative approach - assume modification
change_type = "modified"
```
- Simpler, errs on side of caution
- Accepts that precise tracking requires more infrastructure

**Option C: Use session.json to determine change type**
```python
# Check if file already in cow_files
if file already tracked in session.json:
    change_type = "modified"
else:
    change_type = "created"
```
- Most accurate with current architecture
- Requires reading session.json before updating (adds overhead)

---

### Recommended Changes

**File:** `.claude/hooks/session_track_hook.py`

**Current Code:**
```python
# Line 97
change_type = "created" if tool_name == "Write" else "modified"
```

**Suggested Code (Option C - most accurate):**
```python
# Determine change type by checking if already tracked
change_type = "modified"  # Default assumption

# Check session.json to see if file already tracked
session_file = session_path / "session.json"
try:
    with open(session_file, 'r', encoding='utf-8') as f:
        session_data = json.load(f)

    # If file not in cow_files, it's being created
    is_tracked = any(
        cow["path"] == rel_path_str
        for cow in session_data.get("cow_files", [])
    )
    if not is_tracked:
        change_type = "created"
except Exception:
    pass  # On error, keep default "modified"
```

**Alternative (Option B - simpler, conservative):**
```python
# Always use "modified" for safety (simpler heuristic)
change_type = "modified"
```

---

## Related Issues

None - this is isolated to the hook's change type detection logic.

---

## Testing

**Test Case 1: File Creation**
1. Create session
2. Use `Write` to create `acts/act-1/plan.md` (doesn't exist)
3. Verify hook tracks as `"created"`

**Test Case 2: File Overwrite**
1. Create session with existing `acts/act-1/plan.md`
2. Use `Write` to overwrite the file
3. Verify hook tracks as `"modified"` (not `"created"`)

**Test Case 3: File Edit**
1. Create session with modified file
2. Use `Edit` to change the file
3. Verify hook tracks as `"modified"`

---

**Status:** ⏳ Pending Fix
