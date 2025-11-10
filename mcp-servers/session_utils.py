"""
Session Management Utilities

Utility functions for session management MCP server.

This module contains:
- Constants (paths)
- Session lock management
- Session data I/O (with atomic writes)
- CoW (Copy-on-Write) tracking
- File size formatting
"""

from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import tempfile


# Constants

WORKSPACE_PATH = Path("workspace")
SESSIONS_PATH = WORKSPACE_PATH / "sessions"
SESSION_LOCK_FILE = WORKSPACE_PATH / "session.lock"


# Session Lock Management

def _get_session_lock() -> Optional[Dict[str, Any]]:
    """Get current session lock data.

    Returns:
        Session lock dict or None if no lock exists
    """
    if not SESSION_LOCK_FILE.exists():
        return None

    try:
        with open(SESSION_LOCK_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def _update_session_lock(session_name: str) -> None:
    """Update session.lock with new active session.

    Args:
        session_name: Name of session to activate
    """
    WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)

    lock_data = {
        "active": session_name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "user": os.environ.get("USER", "unknown")
    }

    with open(SESSION_LOCK_FILE, 'w') as f:
        json.dump(lock_data, f, indent=2)


def _clear_session_lock() -> None:
    """Clear session.lock (no active session)."""
    if SESSION_LOCK_FILE.exists():
        SESSION_LOCK_FILE.unlink()


# Session Path Management

def _get_session_path(name: str) -> Path:
    """Get path to session directory.

    Args:
        name: Session name

    Returns:
        Path to session directory
    """
    return SESSIONS_PATH / name


# Session Data I/O

def _load_session_data(name: str) -> Dict[str, Any]:
    """Load session.json data.

    Args:
        name: Session name

    Returns:
        Session data dict

    Raises:
        FileNotFoundError: If session doesn't exist
        ValueError: If session.json is corrupted
    """
    session_path = _get_session_path(name)
    session_file = session_path / "session.json"

    if not session_file.exists():
        raise FileNotFoundError(f"Session '{name}' not found")

    try:
        with open(session_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupted session.json for '{name}': {e}") from e


def _atomic_write_session_json(session_path: Path, data: Dict[str, Any]) -> None:
    """Atomically write session.json to prevent data corruption.

    Uses temp file + atomic rename to ensure session.json is never partially written.

    Args:
        session_path: Path to session directory
        data: Session data to write

    Raises:
        ValueError: If write fails
    """
    session_file = session_path / "session.json"
    dir_path = session_file.parent

    try:
        # Write to temp file in same directory (atomic rename requires same filesystem)
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=dir_path,
            delete=False,
            encoding='utf-8',
            suffix='.tmp'
        ) as tf:
            json.dump(data, tf, indent=2, ensure_ascii=False)
            temp_name = tf.name

        # Atomic rename (POSIX guarantees atomicity)
        os.replace(temp_name, session_file)
    except Exception as e:
        # Clean up temp file if rename failed
        if 'temp_name' in locals() and Path(temp_name).exists():
            Path(temp_name).unlink()
        raise ValueError(f"Failed to write session.json atomically: {e}") from e


def _save_session_data(name: str, data: Dict[str, Any]) -> None:
    """Save session.json data atomically.

    Args:
        name: Session name
        data: Session data to save
    """
    session_path = _get_session_path(name)
    _atomic_write_session_json(session_path, data)


# Session Information

def _get_active_session() -> Optional[Dict[str, Any]]:
    """Get active session information.

    Returns:
        {
            "name": str,
            "path": str,
            "context_path": str,
            "acts_path": str,
            "status": str,
            "data": dict  # Full session.json data
        }
        or None if no active session
    """
    lock = _get_session_lock()
    if not lock:
        return None

    session_name = lock.get("active")
    if not session_name:
        return None

    session_path = _get_session_path(session_name)
    if not session_path.exists():
        return None

    try:
        session_data = _load_session_data(session_name)
    except Exception:
        return None

    return {
        "name": session_name,
        "path": str(session_path),
        "context_path": str(session_path / "context"),
        "acts_path": str(session_path / "acts"),
        "status": session_data.get("status", "UNKNOWN"),
        "data": session_data
    }


# Session Structure

def _create_session_structure(session_path: Path) -> None:
    """Create empty session directory structure (CoW).

    Args:
        session_path: Path to session directory
    """
    # Create directory structure WITHOUT copying files
    dirs = [
        session_path / "context" / "characters",
        session_path / "context" / "world-bible",
        session_path / "context" / "canon-levels",
        session_path / "context" / "plot-graph",
        session_path / "acts",
        session_path / "artifacts",
        session_path / "human-retries",
        session_path / "workflow-state",  # Workflow orchestration state
        session_path / "generation-runs",  # Generation workflow artifacts
        session_path / "planning-runs",  # Planning workflow artifacts
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


# Copy-on-Write Path Resolution

def _resolve_path_cow(rel_path: str, session_name: str) -> Dict[str, Any]:
    """Resolve path with Copy-on-Write logic.

    Args:
        rel_path: Relative path (e.g., "acts/act-1/.../scene-0101.md")
        session_name: Session name

    Returns:
        {
            "resolved_path": str,  # Actual path to use
            "source": str,         # "session" | "global"
            "exists": bool,
            "modified_in_session": bool
        }
    """
    session_path = _get_session_path(session_name)
    session_file_path = session_path / rel_path
    global_file_path = Path(rel_path)

    # Check if file exists in session (modified)
    if session_file_path.exists():
        return {
            "resolved_path": str(session_file_path),
            "source": "session",
            "exists": True,
            "modified_in_session": True
        }

    # File not in session, use global
    return {
        "resolved_path": str(global_file_path),
        "source": "global",
        "exists": global_file_path.exists(),
        "modified_in_session": False
    }


# CoW Tracking

def _add_cow_file(session_name: str, file_path: str, change_type: str) -> None:
    """Add file to session CoW tracking.

    Args:
        session_name: Session name
        file_path: Relative path to file
        change_type: "modified" | "created" | "deleted"
    """
    session_data = _load_session_data(session_name)
    session_path = _get_session_path(session_name)

    # Check if already tracked
    existing_entry = None
    for cow_file in session_data["cow_files"]:
        if cow_file["path"] == file_path:
            existing_entry = cow_file
            break

    if existing_entry:
        # Update change_type if status changed
        old_type = existing_entry["type"]
        if old_type != change_type:
            # Remove from old change list
            if file_path in session_data["changes"][old_type]:
                session_data["changes"][old_type].remove(file_path)

            # Add to new change list
            if file_path not in session_data["changes"][change_type]:
                session_data["changes"][change_type].append(file_path)

            # Update type in cow_files
            existing_entry["type"] = change_type
            existing_entry["updated_at"] = datetime.now(timezone.utc).isoformat()

            _save_session_data(session_name, session_data)
        return

    # Get file size from session directory
    session_file = session_path / file_path
    size_bytes = os.path.getsize(session_file) if session_file.exists() else 0

    # Add to cow_files
    cow_entry = {
        "path": file_path,
        "type": change_type,
        "copied_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": size_bytes
    }

    session_data["cow_files"].append(cow_entry)

    # Update changes list
    if file_path not in session_data["changes"][change_type]:
        session_data["changes"][change_type].append(file_path)

    # Update stats
    session_data["stats"]["total_files_changed"] = len(session_data["cow_files"])
    session_data["stats"]["session_size_bytes"] = sum(
        f["size_bytes"] for f in session_data["cow_files"]
    )

    _save_session_data(session_name, session_data)


# Workflow State Management

def _copy_workflow_states_to_global(session_name: str, session_path: Path) -> tuple[int, int]:
    """Copy workflow states from session to global directory on commit.

    Args:
        session_name: Session name
        session_path: Path to session directory

    Returns:
        Tuple of (copied_count, failed_count)
    """
    global_workflow_dir = WORKSPACE_PATH / "workflow-state"
    global_workflow_dir.mkdir(parents=True, exist_ok=True)

    session_workflow_dir = session_path / "workflow-state"

    copied = 0
    failed = 0

    if not session_workflow_dir.exists():
        return (copied, failed)

    # Copy all workflow state files
    import shutil
    for state_file in session_workflow_dir.glob("*.json"):
        if state_file.name == "index.json":
            continue  # Skip index files

        try:
            shutil.copy2(state_file, global_workflow_dir / state_file.name)
            copied += 1
        except Exception:
            failed += 1

    # Copy generation-runs artifacts
    session_gen_runs = session_path / "generation-runs"
    global_gen_runs = WORKSPACE_PATH / "generation-runs"
    if session_gen_runs.exists():
        global_gen_runs.mkdir(parents=True, exist_ok=True)
        for run_dir in session_gen_runs.iterdir():
            if run_dir.is_dir():
                try:
                    shutil.copytree(run_dir, global_gen_runs / run_dir.name, dirs_exist_ok=True)
                    copied += 1
                except Exception:
                    failed += 1

    # Copy planning-runs artifacts
    session_plan_runs = session_path / "planning-runs"
    global_plan_runs = WORKSPACE_PATH / "planning-runs"
    if session_plan_runs.exists():
        global_plan_runs.mkdir(parents=True, exist_ok=True)
        for run_dir in session_plan_runs.iterdir():
            if run_dir.is_dir():
                try:
                    shutil.copytree(run_dir, global_plan_runs / run_dir.name, dirs_exist_ok=True)
                    copied += 1
                except Exception:
                    failed += 1

    return (copied, failed)


# Formatting

def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "2.3 MB", "450 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
