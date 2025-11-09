#!/usr/bin/env python3
"""
Session Management MCP Server with Copy-on-Write Support

This MCP server provides session management for book writing workflow with CoW.

Features:
- Copy-on-Write file isolation (files copied only on first write)
- Session creation, switching, commit, cancel
- Human retry tracking
- Path resolution (session → global fallback)
- Session lock management

State files:
- workspace/session.lock - Active session pointer
- workspace/sessions/{name}/session.json - Session metadata + CoW tracking
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import shutil
import glob

from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("session_management_mcp")

# Constants
WORKSPACE_PATH = Path("workspace")
SESSIONS_PATH = WORKSPACE_PATH / "sessions"
SESSION_LOCK_FILE = WORKSPACE_PATH / "session.lock"


# Enums
class SessionStatus(str, Enum):
    """Possible session statuses."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CRASHED = "CRASHED"


class ChangeType(str, Enum):
    """Types of file changes."""
    MODIFIED = "modified"
    CREATED = "created"
    DELETED = "deleted"


# Pydantic Models

class CreateSessionInput(BaseModel):
    """Input model for create_session tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    name: str = Field(
        ...,
        description="Session name (e.g., 'work-on-chapter-01', 'experimental-scene-0102')",
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
    description: str = Field(
        default="",
        description="Optional description of session purpose",
        max_length=500
    )


class SwitchSessionInput(BaseModel):
    """Input model for switch_session tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    name: str = Field(
        ...,
        description="Session name to switch to",
        min_length=1,
        max_length=100
    )


class CommitSessionInput(BaseModel):
    """Input model for commit_session tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    name: Optional[str] = Field(
        default=None,
        description="Session name to commit (None = active session)",
        max_length=100
    )
    force: bool = Field(
        default=False,
        description="Force commit even if warnings present"
    )


class CancelSessionInput(BaseModel):
    """Input model for cancel_session tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    name: Optional[str] = Field(
        default=None,
        description="Session name to cancel (None = active session)",
        max_length=100
    )
    backup_retries: bool = Field(
        default=True,
        description="Backup human retries before cancelling"
    )


class ResolvePathInput(BaseModel):
    """Input model for resolve_path tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    path: str = Field(
        ...,
        description="Relative path to resolve (e.g., 'acts/act-1/chapters/chapter-01/plan.md')",
        min_length=1,
        max_length=500
    )


class RecordHumanRetryInput(BaseModel):
    """Input model for record_human_retry tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    file_path: str = Field(
        ...,
        description="Path to file being retried (relative or just filename)",
        min_length=1,
        max_length=500
    )
    reason: str = Field(
        ...,
        description="Reason for human retry",
        min_length=1,
        max_length=2000
    )
    auto_detected: bool = Field(
        default=False,
        description="True if AI detected retry, False if explicit /retry command"
    )


# Utility Functions

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


def _get_session_path(name: str) -> Path:
    """Get path to session directory.

    Args:
        name: Session name

    Returns:
        Path to session directory
    """
    return SESSIONS_PATH / name


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
        raise ValueError(f"Corrupted session.json for '{name}': {e}")


def _save_session_data(name: str, data: Dict[str, Any]) -> None:
    """Save session.json data.

    Args:
        name: Session name
        data: Session data to save
    """
    session_path = _get_session_path(name)
    session_file = session_path / "session.json"

    with open(session_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
        session_path / "human-retries"
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


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


def _add_cow_file(session_name: str, file_path: str, change_type: str) -> None:
    """Add file to session CoW tracking.

    Args:
        session_name: Session name
        file_path: Relative path to file
        change_type: "modified" | "created" | "deleted"
    """
    session_data = _load_session_data(session_name)

    # Check if already tracked
    existing_paths = [f["path"] for f in session_data["cow_files"]]
    if file_path in existing_paths:
        return  # Already tracked

    # Get file size
    size_bytes = 0
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)

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


# MCP Tools

@mcp.tool(
    name="get_active_session",
    annotations={
        "title": "Get Active Session Info",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_active_session() -> str:
    """Get information about currently active session.

    Returns:
        Markdown-formatted session info or message if no active session
    """
    session = _get_active_session()

    if not session:
        return """ℹ️ NO ACTIVE SESSION

💡 To start working:
   - Create new session: /session start <name>
   - List sessions: /session list
   - Switch to existing: /session switch <name>
"""

    data = session["data"]
    stats = data.get("stats", {})

    lines = [
        f"📂 ACTIVE SESSION: {session['name']}",
        "",
        f"**Status**: {session['status']}",
        f"**Created**: {data.get('created_at', 'unknown')}",
        f"**Description**: {data.get('description', 'No description')}",
        "",
        "📊 **Changes** (uncommitted):",
        f"   • Modified: {len(data['changes']['modified'])} files",
        f"   • Created: {len(data['changes']['created'])} files",
        f"   • Deleted: {len(data['changes']['deleted'])} files",
        "",
        f"💾 **Session Size**: {_format_file_size(stats.get('session_size_bytes', 0))}",
        "",
        "📁 **Paths**:",
        f"   • Session: {session['path']}/",
        f"   • Context: {session['context_path']}/",
        f"   • Acts: {session['acts_path']}/",
    ]

    # Human retries
    retries = data.get("human_retries", [])
    if retries:
        lines.append("")
        lines.append(f"🔄 **Human Retries**: {len(retries)}")
        for retry in retries[-3:]:  # Show last 3
            lines.append(f"   • {retry['file']}: Retry #{retry['retry_number']} - {retry['reason'][:50]}...")

    return "\n".join(lines)


@mcp.tool(
    name="create_session",
    annotations={
        "title": "Create New Session (CoW)",
        "readOnlyHint": False,
        "idempotentHint": False
    }
)
async def create_session(params: CreateSessionInput) -> str:
    """Create new session with Copy-on-Write structure.

    Creates empty directory structure. Files are copied on-demand when first written.

    Args:
        params: Session creation parameters (name, description)

    Returns:
        Markdown-formatted success message
    """
    session_name = params.name
    session_path = _get_session_path(session_name)

    # Check if session already exists
    if session_path.exists():
        return f"""❌ ERROR: Session '{session_name}' already exists

💡 Options:
   - Use different name: /session start <other-name>
   - Switch to existing: /session switch {session_name}
   - Delete existing: /session cancel {session_name}
"""

    # Create session structure (empty, CoW)
    _create_session_structure(session_path)

    # Create session.json
    session_data = {
        "name": session_name,
        "description": params.description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": os.environ.get("USER", "unknown"),
        "status": SessionStatus.ACTIVE.value,
        "cow_files": [],
        "changes": {
            "modified": [],
            "created": [],
            "deleted": []
        },
        "human_retries": [],
        "stats": {
            "total_files_changed": 0,
            "session_size_bytes": 0
        }
    }

    _save_session_data(session_name, session_data)

    # Update session.lock
    _update_session_lock(session_name)

    return f"""✅ SESSION CREATED: {session_name}

📂 Session Path:
   {session_path}/

⚡ Copy-on-Write Mode:
   • Empty session created (~10 KB structure only)
   • Files will copy on first write
   • Read operations use global files by default

🔒 Session activated (written to session.lock)

💡 How CoW works:
   1. Read "acts/.../plan.md" → Reads from global (not yet modified)
   2. Write "acts/.../plan.md" → CoW: Copies to session, then modifies
   3. Read "acts/.../plan.md" → Reads from session (now modified)

🚀 Ready to work in session!
"""


@mcp.tool(
    name="resolve_path",
    annotations={
        "title": "Resolve Path (CoW)",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def resolve_path(params: ResolvePathInput) -> str:
    """Resolve file path with Copy-on-Write logic.

    Checks if file exists in active session. If yes, returns session path.
    If no, returns global path.

    Args:
        params: Path resolution parameters

    Returns:
        JSON string with resolution result
    """
    session = _get_active_session()

    if not session:
        # No active session - use global path
        global_path = Path(params.path)
        return json.dumps({
            "resolved_path": params.path,
            "source": "global",
            "exists": global_path.exists(),
            "modified_in_session": False,
            "session_active": False
        }, indent=2)

    # Resolve with CoW
    result = _resolve_path_cow(params.path, session["name"])
    result["session_active"] = True
    result["session_name"] = session["name"]

    return json.dumps(result, indent=2)


@mcp.tool(
    name="record_human_retry",
    annotations={
        "title": "Record Human Retry",
        "readOnlyHint": False,
        "idempotentHint": False
    }
)
async def record_human_retry(params: RecordHumanRetryInput) -> str:
    """Record human retry attempt for a file.

    Copies current version to human-retries/ and records reason.

    Args:
        params: Retry recording parameters

    Returns:
        Markdown-formatted confirmation
    """
    session = _get_active_session()

    if not session:
        return """❌ ERROR: No active session

💡 Start session first: /session start <name>
"""

    # Resolve file path
    resolved = _resolve_path_cow(params.file_path, session["name"])
    full_path = Path(resolved["resolved_path"])

    if not full_path.exists():
        return f"""❌ ERROR: File not found: {params.file_path}

Checked paths:
   • Session: {session['path']}/{params.file_path}
   • Global: {params.file_path}
"""

    # Count existing retries for this file
    session_data = session["data"]
    retry_number = len([
        r for r in session_data["human_retries"]
        if r["file"] == params.file_path
    ]) + 1

    # Copy to human-retries/
    filename = Path(params.file_path).name
    retry_file = Path(session["path"]) / "human-retries" / f"{filename}-retry-{retry_number}.md"
    retry_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full_path, retry_file)

    # Save reason
    reason_file = retry_file.with_suffix('.md.reason.txt')
    with open(reason_file, 'w') as f:
        f.write(params.reason)

    # Update session.json
    retry_entry = {
        "file": params.file_path,
        "retry_number": retry_number,
        "reason": params.reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "auto_detected": params.auto_detected
    }
    session_data["human_retries"].append(retry_entry)

    _save_session_data(session["name"], session_data)

    source = "AI detected" if params.auto_detected else "User command"

    return f"""✅ HUMAN RETRY RECORDED

📁 File: {params.file_path}
🔢 Retry Number: {retry_number}
📝 Reason: {params.reason}
🤖 Source: {source}

💾 Saved to:
   • {retry_file}
   • {reason_file}

💡 Previous version preserved for review
"""


@mcp.tool(
    name="list_sessions",
    annotations={
        "title": "List All Sessions",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def list_sessions() -> str:
    """List all sessions (active and inactive).

    Returns:
        Markdown-formatted table of sessions
    """
    if not SESSIONS_PATH.exists():
        return """📋 SESSIONS (0 total)

No sessions found.

💡 Create first session: /session start <name>
"""

    # Scan sessions directory
    session_dirs = [d for d in SESSIONS_PATH.iterdir() if d.is_dir()]

    if not session_dirs:
        return """📋 SESSIONS (0 total)

No sessions found.

💡 Create first session: /session start <name>
"""

    # Get active session
    lock = _get_session_lock()
    active_name = lock.get("active") if lock else None

    # Build session list
    sessions = []
    for session_dir in session_dirs:
        name = session_dir.name

        try:
            data = _load_session_data(name)
            status = SessionStatus.ACTIVE.value if name == active_name else SessionStatus.INACTIVE.value

            sessions.append({
                "name": name,
                "status": status,
                "created": data.get("created_at", "unknown"),
                "changes": data["stats"]["total_files_changed"],
                "size": data["stats"]["session_size_bytes"]
            })
        except Exception:
            # Corrupted session
            sessions.append({
                "name": name,
                "status": SessionStatus.CRASHED.value,
                "created": "unknown",
                "changes": "?",
                "size": 0
            })

    # Sort by creation time (most recent first)
    sessions.sort(key=lambda s: s["created"], reverse=True)

    # Build table
    lines = [
        f"📋 SESSIONS ({len(sessions)} total)",
        "",
        "┌────────────────────────────┬──────────┬────────────┬──────────┐",
        "│ Name                       │ Status   │ Created    │ Changes  │",
        "├────────────────────────────┼──────────┼────────────┼──────────┤"
    ]

    for s in sessions:
        name_short = s["name"][:26].ljust(26)
        status_short = s["status"][:8].ljust(8)

        # Format created time
        try:
            created_dt = datetime.fromisoformat(s["created"].replace('Z', '+00:00'))
            created_str = created_dt.strftime('%Y-%m-%d')[:10]
        except Exception:
            created_str = "unknown   "

        changes_str = str(s["changes"]).rjust(8)

        lines.append(
            f"│ {name_short} │ {status_short} │ {created_str} │ {changes_str} │"
        )

    lines.append("└────────────────────────────┴──────────┴────────────┴──────────┘")
    lines.append("")

    if active_name:
        lines.append(f"🔒 Active: {active_name}")
        lines.append("")

    # Show crashed sessions if any
    crashed = [s for s in sessions if s["status"] == SessionStatus.CRASHED.value]
    if crashed:
        lines.append(f"⚠️ Crashed sessions ({len(crashed)}):")
        for s in crashed:
            lines.append(f"   • {s['name']}")
            lines.append("     Action required: /session cancel <name>")
        lines.append("")

    lines.append("💡 Commands:")
    lines.append("   - Switch: /session switch <name>")
    lines.append("   - Commit: /session commit")
    lines.append("   - Cancel: /session cancel")

    return "\n".join(lines)


@mcp.tool(
    name="switch_session",
    annotations={
        "title": "Switch Active Session",
        "readOnlyHint": False,
        "idempotentHint": True
    }
)
async def switch_session(params: SwitchSessionInput) -> str:
    """Switch to different session.

    Args:
        params: Session switch parameters

    Returns:
        Markdown-formatted confirmation
    """
    session_name = params.name
    session_path = _get_session_path(session_name)

    # Check session exists
    if not session_path.exists():
        return f"""❌ ERROR: Session '{session_name}' not found

💡 Available sessions: /session list
"""

    # Load session data
    try:
        session_data = _load_session_data(session_name)
    except Exception as e:
        return f"""❌ ERROR: Failed to load session '{session_name}'

Error: {str(e)}

💡 Session may be corrupted. Try: /session cancel {session_name}
"""

    # Check if crashed
    if session_data.get("status") == SessionStatus.CRASHED.value:
        return f"""❌ ERROR: Session '{session_name}' is CRASHED

💡 Action required:
   - Cancel: /session cancel {session_name}
   - Or fix manually and try again
"""

    # Get previous session
    prev_lock = _get_session_lock()
    prev_name = prev_lock.get("active") if prev_lock else None

    # Update session.lock
    _update_session_lock(session_name)

    # Format response
    lines = ["🔄 SWITCHED SESSION", ""]

    if prev_name:
        lines.append(f"From: {prev_name}")

    lines.append(f"To:   {session_name}")
    lines.append("")
    lines.append("📂 Active Session Directory:")
    lines.append(f"   {session_path}/")
    lines.append("")

    # Show session stats
    stats = session_data.get("stats", {})
    lines.append("📊 Progress:")
    lines.append(f"   • Modified files: {len(session_data['changes']['modified'])}")
    lines.append(f"   • Created files: {len(session_data['changes']['created'])}")
    lines.append(f"   • Session size: {_format_file_size(stats.get('session_size_bytes', 0))}")

    retries = len(session_data.get("human_retries", []))
    if retries > 0:
        lines.append(f"   • Human retries: {retries}")

    lines.append("")
    lines.append("💡 Resume work or commit when ready")

    return "\n".join(lines)


@mcp.tool(
    name="commit_session",
    annotations={
        "title": "Commit Session Changes",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False
    }
)
async def commit_session(params: CommitSessionInput) -> str:
    """Commit session changes to global files (Copy CoW files to global).

    Args:
        params: Commit parameters

    Returns:
        Markdown-formatted commit summary
    """
    # Get session to commit
    if params.name:
        session_name = params.name
    else:
        session = _get_active_session()
        if not session:
            return """❌ ERROR: No active session

💡 Specify session: /session commit <name>
   Or start session: /session start <name>
"""
        session_name = session["name"]

    # Load session data
    try:
        session_data = _load_session_data(session_name)
    except Exception as e:
        return f"❌ ERROR: Failed to load session '{session_name}': {str(e)}"

    session_path = _get_session_path(session_name)

    # Check if any changes to commit
    if not session_data["cow_files"]:
        return f"""ℹ️ NO CHANGES TO COMMIT

Session '{session_name}' has no modified files.

💡 Nothing to commit - session is empty
"""

    # Show what will be committed (require confirmation if not force)
    if not params.force:
        lines = [
            f"⚠️ COMMIT SESSION: {session_name}",
            "",
            "📊 Changes to be committed:"
        ]

        modified = session_data["changes"]["modified"]
        created = session_data["changes"]["created"]
        deleted = session_data["changes"]["deleted"]

        if modified:
            lines.append(f"\n   Modified files ({len(modified)}):")
            for f in modified[:5]:
                lines.append(f"     • {f}")
            if len(modified) > 5:
                lines.append(f"     ... and {len(modified) - 5} more")

        if created:
            lines.append(f"\n   Created files ({len(created)}):")
            for f in created[:5]:
                lines.append(f"     • {f}")
            if len(created) > 5:
                lines.append(f"     ... and {len(created) - 5} more")

        if deleted:
            lines.append(f"\n   Deleted files ({len(deleted)}):")
            for f in deleted:
                lines.append(f"     • {f}")

        retries = session_data.get("human_retries", [])
        if retries:
            lines.append(f"\n   Human retries: {len(retries)}")
            for r in retries[:3]:
                lines.append(f"     • {r['file']}: {r['reason'][:60]}...")

        lines.append("")
        lines.append("❓ This will OVERWRITE global files.")
        lines.append("💡 To proceed: commit_session(name='{}', force=True)".format(session_name))

        return "\n".join(lines)

    # Commit: Copy CoW files from session to global
    copied_files = []
    failed_files = []

    for cow_file in session_data["cow_files"]:
        file_path = cow_file["path"]
        session_file = session_path / file_path
        global_file = Path(file_path)

        try:
            # Create parent directory if needed
            global_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy from session to global
            if session_file.exists():
                shutil.copy2(session_file, global_file)
                copied_files.append(file_path)
        except Exception as e:
            failed_files.append((file_path, str(e)))

    # Archive human retries (don't delete)
    retries_archived = False
    if session_data.get("human_retries"):
        archive_dir = WORKSPACE_PATH / "retries-archive" / session_name
        archive_dir.mkdir(parents=True, exist_ok=True)

        retries_dir = session_path / "human-retries"
        if retries_dir.exists():
            shutil.copytree(retries_dir, archive_dir, dirs_exist_ok=True)
            retries_archived = True

    # Clean up session directory
    shutil.rmtree(session_path)

    # Clear session.lock if this was active session
    lock = _get_session_lock()
    if lock and lock.get("active") == session_name:
        _clear_session_lock()

    # Build response
    lines = [
        "✅ SESSION COMMITTED",
        "",
        f"Session: {session_name}",
        "",
        "📁 Files copied to global:"
    ]

    if copied_files:
        for f in copied_files[:10]:
            lines.append(f"   ✓ {f}")
        if len(copied_files) > 10:
            lines.append(f"   ... and {len(copied_files) - 10} more")
    else:
        lines.append("   (none)")

    if failed_files:
        lines.append("")
        lines.append("⚠️ Failed to copy:")
        for f, err in failed_files:
            lines.append(f"   ✗ {f}: {err}")

    if retries_archived:
        lines.append("")
        lines.append("📦 Human retries archived:")
        lines.append(f"   {WORKSPACE_PATH}/retries-archive/{session_name}/")

    lines.append("")
    lines.append("🗑️ Session directory removed")
    lines.append("🔓 Session lock cleared")
    lines.append("")
    lines.append("🎉 Changes committed to book!")

    return "\n".join(lines)


@mcp.tool(
    name="cancel_session",
    annotations={
        "title": "Cancel Session (Rollback)",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False
    }
)
async def cancel_session(params: CancelSessionInput) -> str:
    """Cancel session and discard all changes.

    Args:
        params: Cancel parameters

    Returns:
        Markdown-formatted cancellation summary
    """
    # Get session to cancel
    if params.name:
        session_name = params.name
    else:
        session = _get_active_session()
        if not session:
            return """❌ ERROR: No active session

💡 Specify session: /session cancel <name>
   Or list sessions: /session list
"""
        session_name = session["name"]

    session_path = _get_session_path(session_name)

    if not session_path.exists():
        return f"❌ ERROR: Session '{session_name}' not found"

    # Load session data (best effort)
    try:
        session_data = _load_session_data(session_name)
    except Exception:
        session_data = {"human_retries": [], "changes": {"modified": [], "created": [], "deleted": []}}

    # Backup human retries if requested
    retries_backed_up = False
    if params.backup_retries and session_data.get("human_retries"):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_dir = WORKSPACE_PATH / "retries-archive" / f"{session_name}-cancelled-{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        retries_dir = session_path / "human-retries"
        if retries_dir.exists():
            shutil.copytree(retries_dir, backup_dir, dirs_exist_ok=True)
            retries_backed_up = True

    # Count changes
    modified = len(session_data["changes"]["modified"])
    created = len(session_data["changes"]["created"])
    retries = len(session_data.get("human_retries", []))

    # Delete session directory
    shutil.rmtree(session_path)

    # Clear session.lock if this was active
    lock = _get_session_lock()
    if lock and lock.get("active") == session_name:
        _clear_session_lock()

    # Build response
    lines = [
        "🛑 SESSION CANCELLED",
        "",
        f"Session: {session_name}",
        "",
        "📊 Discarded changes:",
        f"   • Modified files: {modified}",
        f"   • Created files: {created}",
        f"   • Human retries: {retries}",
        ""
    ]

    if retries_backed_up:
        lines.append("📦 Human retries backed up:")
        lines.append(f"   {backup_dir}/")
        lines.append("")

    lines.append("🗑️ Session directory removed")
    lines.append("🔓 Session lock cleared")
    lines.append("")
    lines.append("💡 Global files (context/, acts/) unchanged")

    return "\n".join(lines)


# Main entry point
if __name__ == "__main__":
    # Run server with stdio transport
    mcp.run()
