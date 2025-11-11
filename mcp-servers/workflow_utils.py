"""
Workflow Orchestration Utilities

Helper functions for workflow orchestration MCP server.

This module contains:
- Constants (paths)
- Session-aware path resolution
- Workflow state loading/saving
- Step definition lookup
- Progress calculation
"""

from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import json

from workflow_models import GENERATION_STEPS


# Constants

WORKSPACE_PATH = Path("workspace")
GLOBAL_WORKFLOW_STATE_DIR = WORKSPACE_PATH / "workflow-state"
SESSIONS_PATH = WORKSPACE_PATH / "sessions"


# Helper Functions

def _get_active_session() -> Optional[str]:
    """Get active session name from session.lock.

    Returns:
        Session name or None if no active session
    """
    session_lock = WORKSPACE_PATH / "session.lock"
    if not session_lock.exists():
        return None

    try:
        with open(session_lock, 'r') as f:
            lock_data = json.load(f)
        return lock_data.get("active")
    except Exception:
        return None


def _get_workflow_state_path(workflow_id: str) -> Path:
    """Get path to workflow state file.

    Checks session directory first, then global.

    Args:
        workflow_id: Workflow ID

    Returns:
        Path to workflow state JSON file
    """
    # Check if running in session
    session_name = _get_active_session()
    if session_name:
        session_state_path = SESSIONS_PATH / session_name / "workflow-state" / f"{workflow_id}.json"
        if session_state_path.exists():
            return session_state_path

    # Fall back to global
    return GLOBAL_WORKFLOW_STATE_DIR / f"{workflow_id}.json"


def _load_workflow_state(workflow_id: str) -> Dict[str, Any]:
    """Load workflow state from file.

    Args:
        workflow_id: Workflow ID

    Returns:
        Workflow state dict

    Raises:
        FileNotFoundError: If workflow doesn't exist
        ValueError: If workflow state is corrupted
    """
    state_path = _get_workflow_state_path(workflow_id)

    if not state_path.exists():
        raise FileNotFoundError(f"Workflow '{workflow_id}' not found")

    try:
        with open(state_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupted workflow state for '{workflow_id}': {e}") from e


def _save_workflow_state(workflow_id: str, state: Dict[str, Any]) -> None:
    """Save workflow state to file.

    Args:
        workflow_id: Workflow ID
        state: Workflow state dict
    """
    state_path = _get_workflow_state_path(workflow_id)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)


def _get_step_definition(workflow_type: str, step: int) -> Optional[Dict[str, Any]]:
    """Get step definition from workflow definitions.

    Args:
        workflow_type: "generation" or "planning"
        step: Step number

    Returns:
        Step definition dict or None
    """
    if workflow_type == "generation":
        for step_def in GENERATION_STEPS:
            if step_def["step"] == step:
                return step_def
    # Planning phases would be similar
    return None


def _calculate_progress(state: Dict[str, Any]) -> int:
    """Calculate workflow progress percentage.

    Args:
        state: Workflow state dict

    Returns:
        Progress percentage (0-100)
    """
    workflow_type = state.get("workflow_type")

    if workflow_type == "generation":
        gen_state = state.get("generation", {})
        current_step = gen_state.get("current_step", 0)
        total_steps = gen_state.get("total_steps", 7)
        return int((current_step / total_steps) * 100)

    elif workflow_type == "planning":
        plan_state = state.get("planning", {})
        current_phase = plan_state.get("current_phase", 0)
        total_phases = plan_state.get("total_phases", 5)
        return int((current_phase / total_phases) * 100)

    return 0
