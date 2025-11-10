"""
Workflow Orchestration MCP Server

Provides sequential workflow enforcement, state tracking, and human-in-the-loop
checkpoints for Generation and Planning workflows.

Features:
- Sequential step enforcement (can't skip steps)
- Human approval checkpoints
- Retry logic for Generation workflow
- Recovery/resume after failures
- Integration with session management
- Parallel execution tracking

Tools:
- get_workflow_status: Get current workflow state
- get_next_step: Get next step info (sequential enforcement)
- validate_prerequisites: Check if prerequisites met
- approve_step: Approve human checkpoint
- update_workflow_state: Update workflow state (internal)
- list_workflows: List all workflows (optionally filter)
- resume_workflow: Resume failed/cancelled workflow
- cancel_workflow: Cancel active workflow
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
import json
import os

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict


# Initialize FastMCP server
mcp = FastMCP("workflow-orchestration")


# Constants

WORKSPACE_PATH = Path("workspace")
GLOBAL_WORKFLOW_STATE_DIR = WORKSPACE_PATH / "workflow-state"
SESSIONS_PATH = WORKSPACE_PATH / "sessions"


# Enums

class WorkflowType(str, Enum):
    """Workflow types."""
    GENERATION = "generation"
    PLANNING = "planning"


class WorkflowStatus(str, Enum):
    """Workflow status values."""
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step/phase status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


# Workflow Definitions

GENERATION_STEPS = [
    {
        "step": 1,
        "name": "File Check",
        "agent": "generation-coordinator",
        "description": "Verify blueprint exists",
        "prerequisites": [],
        "outputs": ["blueprint_path"],
        "human_approval": False,
        "retry_enabled": False,
    },
    {
        "step": 2,
        "name": "Blueprint Validation",
        "agent": "blueprint-validator",
        "description": "Validate blueprint completeness and consistency",
        "prerequisites": [1],
        "outputs": ["constraints_list"],
        "human_approval": False,
        "retry_enabled": False,
    },
    {
        "step": 3,
        "name": "Verification Plan",
        "agent": "verification-planner",
        "description": "Create human-readable plan for approval",
        "prerequisites": [2],
        "outputs": ["verification_plan"],
        "human_approval": True,
        "retry_enabled": False,
    },
    {
        "step": 4,
        "name": "Generation",
        "agent": "prose-writer",
        "description": "Generate literary prose adhering to constraints",
        "prerequisites": [3],
        "outputs": ["draft", "compliance_echo"],
        "human_approval": False,
        "retry_enabled": True,
        "max_attempts": 3,
    },
    {
        "step": 5,
        "name": "Fast Compliance Check",
        "agent": "blueprint-compliance-fast-checker",
        "description": "Fast surface-level compliance check (<30s)",
        "prerequisites": [4],
        "outputs": ["fast_compliance_result"],
        "human_approval": False,
        "retry_enabled": False,
        "triggers_retry": True,
    },
    {
        "step": 6,
        "name": "Full Validation",
        "agent": "validation-aggregator",
        "description": "Deep validation with 7 validators in parallel",
        "prerequisites": [5],
        "outputs": ["final_validation_report"],
        "human_approval": False,
        "retry_enabled": False,
        "parallel_agents": 7,
    },
    {
        "step": 7,
        "name": "Final Output",
        "agent": "generation-coordinator",
        "description": "Format final report for user",
        "prerequisites": [6],
        "outputs": ["final_report", "scene_content"],
        "human_approval": False,
        "retry_enabled": False,
    },
]

PLANNING_PHASES = {
    "scene": [
        {
            "phase": 1,
            "name": "Exploration",
            "agents": ["dialogue-analyst", "context-analyzer"],
            "parallel": True,
            "prerequisites": [],
            "outputs": ["exploration_results"],
            "human_approval": False,
        },
        {
            "phase": 2,
            "name": "Scenarios",
            "agents": ["scenario-generator", "consequence-predictor"],
            "parallel": False,
            "prerequisites": [1],
            "outputs": ["scenarios"],
            "human_approval": True,
            "approval_type": "select_variant",
        },
        {
            "phase": 3,
            "name": "Path Planning",
            "agents": ["arc-planner", "dependency-mapper"],
            "parallel": False,
            "prerequisites": [2],
            "outputs": ["path_plan"],
            "human_approval": False,
        },
        {
            "phase": 4,
            "name": "Detailing",
            "agents": ["emotional-arc-designer", "beat-planner", "dialogue-weaver"],
            "parallel": False,
            "prerequisites": [3],
            "outputs": ["detailed_plans"],
            "human_approval": False,
        },
        {
            "phase": 5,
            "name": "Integration",
            "agents": ["storyline-integrator", "impact-analyzer"],
            "parallel": False,
            "prerequisites": [4],
            "outputs": ["integration_analysis"],
            "human_approval": False,
        },
    ],
    # Chapter, Act planning phases can be added here
}


# Pydantic Input Models

class GetWorkflowStatusInput(BaseModel):
    """Input for get_workflow_status tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    workflow_id: str = Field(
        ...,
        description="Workflow ID",
        min_length=1,
        max_length=200
    )


class GetNextStepInput(BaseModel):
    """Input for get_next_step tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    workflow_id: str = Field(
        ...,
        description="Workflow ID",
        min_length=1,
        max_length=200
    )


class ValidatePrerequisitesInput(BaseModel):
    """Input for validate_prerequisites tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    workflow_id: str = Field(
        ...,
        description="Workflow ID",
        min_length=1,
        max_length=200
    )
    step: int = Field(
        ...,
        description="Step number to validate prerequisites for",
        ge=1
    )


class ApproveStepInput(BaseModel):
    """Input for approve_step tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    workflow_id: str = Field(
        ...,
        description="Workflow ID",
        min_length=1,
        max_length=200
    )
    step: int = Field(
        ...,
        description="Step number to approve",
        ge=1
    )
    approved: bool = Field(
        ...,
        description="True to approve, False to reject"
    )
    modifications: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional modifications requested by user"
    )


class UpdateWorkflowStateInput(BaseModel):
    """Input for update_workflow_state tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    workflow_id: str = Field(
        ...,
        description="Workflow ID",
        min_length=1,
        max_length=200
    )
    step: Optional[int] = Field(
        default=None,
        description="Step number being updated",
        ge=1
    )
    status: Optional[str] = Field(
        default=None,
        description="New status for step"
    )
    artifacts: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Artifacts produced by step"
    )


class ListWorkflowsInput(BaseModel):
    """Input for list_workflows tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    status: Optional[str] = Field(
        default=None,
        description="Filter by status"
    )
    workflow_type: Optional[str] = Field(
        default=None,
        description="Filter by workflow type"
    )
    session_name: Optional[str] = Field(
        default=None,
        description="Filter by session name"
    )


class ResumeWorkflowInput(BaseModel):
    """Input for resume_workflow tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    workflow_id: str = Field(
        ...,
        description="Workflow ID to resume",
        min_length=1,
        max_length=200
    )
    from_step: Optional[int] = Field(
        default=None,
        description="Step to resume from (defaults to last completed step + 1)",
        ge=1
    )


class CancelWorkflowInput(BaseModel):
    """Input for cancel_workflow tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    workflow_id: str = Field(
        ...,
        description="Workflow ID to cancel",
        min_length=1,
        max_length=200
    )
    reason: Optional[str] = Field(
        default="User requested cancellation",
        description="Reason for cancellation",
        max_length=500
    )


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


# MCP Tools

@mcp.tool()
def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get current workflow state.

    Returns detailed status including current step, progress, and artifacts.

    Args:
        workflow_id: Workflow ID

    Returns:
        {
            "workflow_id": str,
            "workflow_type": "generation" | "planning",
            "status": str,
            "current_step": int,
            "current_step_name": str,
            "waiting_for_approval": bool,
            "progress_percentage": int,
            "artifacts": dict
        }
    """
    try:
        state = _load_workflow_state(workflow_id)
        workflow_type = state.get("workflow_type")

        result = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "status": state.get("status"),
            "progress_percentage": _calculate_progress(state),
        }

        if workflow_type == "generation":
            gen_state = state.get("generation", {})
            current_step = gen_state.get("current_step", 0)
            steps = gen_state.get("steps", [])

            # Find current step
            current_step_data = next((s for s in steps if s["step"] == current_step), None)

            result.update({
                "current_step": current_step,
                "current_step_name": current_step_data.get("name") if current_step_data else "",
                "waiting_for_approval": current_step_data.get("status") == "waiting_approval" if current_step_data else False,
                "artifacts": gen_state.get("artifacts", {}),
            })

        elif workflow_type == "planning":
            plan_state = state.get("planning", {})
            current_phase = plan_state.get("current_phase", 0)
            phases = plan_state.get("phases", [])

            # Find current phase
            current_phase_data = next((p for p in phases if p["phase"] == current_phase), None)

            result.update({
                "current_phase": current_phase,
                "current_phase_name": current_phase_data.get("name") if current_phase_data else "",
                "waiting_for_approval": current_phase_data.get("status") == "waiting_approval" if current_phase_data else False,
                "artifacts": plan_state.get("artifacts", {}),
            })

        return result

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to get workflow status: {e}"}


@mcp.tool()
def get_next_step(workflow_id: str) -> Dict[str, Any]:
    """Get next step info (sequential enforcement).

    Determines if workflow can proceed to next step, what's blocking, and what action is required.

    Args:
        workflow_id: Workflow ID

    Returns:
        {
            "can_proceed": bool,
            "current_step": int,
            "current_step_name": str,
            "current_status": str,
            "blocking_reason": str | None,
            "required_action": str | None,
            "next_step": int | None,
            "next_step_name": str | None,
            "prerequisites_met": bool
        }
    """
    try:
        state = _load_workflow_state(workflow_id)
        workflow_type = state.get("workflow_type")

        if workflow_type == "generation":
            gen_state = state.get("generation", {})
            current_step = gen_state.get("current_step", 0)
            steps = gen_state.get("steps", [])

            # Find current step
            current_step_data = next((s for s in steps if s["step"] == current_step), None)
            if not current_step_data:
                return {"error": f"Invalid current step: {current_step}"}

            current_status = current_step_data.get("status")

            # Check if waiting for approval
            if current_status == "waiting_approval":
                return {
                    "can_proceed": False,
                    "current_step": current_step,
                    "current_step_name": current_step_data.get("name"),
                    "current_status": current_status,
                    "blocking_reason": "Human approval required",
                    "required_action": f"User must approve or modify {current_step_data.get('name')}",
                    "next_step": None,
                    "next_step_name": None,
                    "prerequisites_met": False,
                }

            # Check if current step is still in progress
            if current_status == "in_progress":
                return {
                    "can_proceed": False,
                    "current_step": current_step,
                    "current_step_name": current_step_data.get("name"),
                    "current_status": current_status,
                    "blocking_reason": "Current step still in progress",
                    "required_action": "Wait for current step to complete",
                    "next_step": None,
                    "next_step_name": None,
                    "prerequisites_met": False,
                }

            # Check if current step completed
            if current_status == "completed":
                next_step_num = current_step + 1
                next_step_data = next((s for s in steps if s["step"] == next_step_num), None)

                if not next_step_data:
                    # Workflow complete
                    return {
                        "can_proceed": False,
                        "current_step": current_step,
                        "current_step_name": current_step_data.get("name"),
                        "current_status": current_status,
                        "blocking_reason": "Workflow completed",
                        "required_action": None,
                        "next_step": None,
                        "next_step_name": None,
                        "prerequisites_met": True,
                    }

                return {
                    "can_proceed": True,
                    "current_step": current_step,
                    "current_step_name": current_step_data.get("name"),
                    "current_status": current_status,
                    "blocking_reason": None,
                    "required_action": None,
                    "next_step": next_step_num,
                    "next_step_name": next_step_data.get("name"),
                    "prerequisites_met": True,
                }

        return {"error": "Unsupported workflow type"}

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to get next step: {e}"}


@mcp.tool()
def validate_prerequisites(workflow_id: str, step: int) -> Dict[str, Any]:
    """Check if prerequisites met for specific step.

    Validates that all required previous steps are completed before starting requested step.

    Args:
        workflow_id: Workflow ID
        step: Step number to validate prerequisites for

    Returns:
        {
            "prerequisites_met": bool,
            "required_steps": list[int],
            "completed_steps": list[int],
            "missing_steps": list[int],
            "can_start_step": bool,
            "blocking_issues": list[str]
        }
    """
    try:
        state = _load_workflow_state(workflow_id)
        workflow_type = state.get("workflow_type")

        if workflow_type != "generation":
            return {"error": "Only generation workflow supported currently"}

        # Get step definition
        step_def = _get_step_definition(workflow_type, step)
        if not step_def:
            return {"error": f"Invalid step number: {step}"}

        required_steps = step_def.get("prerequisites", [])
        gen_state = state.get("generation", {})
        steps = gen_state.get("steps", [])

        # Find completed steps
        completed_steps = [
            s["step"] for s in steps
            if s.get("status") == "completed"
        ]

        missing_steps = [s for s in required_steps if s not in completed_steps]

        prerequisites_met = len(missing_steps) == 0

        # Check for blocking issues
        blocking_issues = []
        if missing_steps:
            blocking_issues.append(f"Missing completed steps: {missing_steps}")

        # Check if current step is the right one
        current_step = gen_state.get("current_step", 0)
        if step != current_step and step != current_step + 1:
            blocking_issues.append(f"Cannot jump to step {step}. Current step is {current_step}")

        return {
            "prerequisites_met": prerequisites_met,
            "required_steps": required_steps,
            "completed_steps": completed_steps,
            "missing_steps": missing_steps,
            "can_start_step": prerequisites_met and len(blocking_issues) == 0,
            "blocking_issues": blocking_issues,
        }

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to validate prerequisites: {e}"}


@mcp.tool()
def approve_step(
    workflow_id: str,
    step: int,
    approved: bool,
    modifications: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Approve human checkpoint (Step 3, Phase 2/10).

    User approves or rejects a step that requires human-in-the-loop.

    Args:
        workflow_id: Workflow ID
        step: Step number to approve
        approved: True to approve, False to reject
        modifications: Optional user-requested modifications

    Returns:
        {
            "success": bool,
            "workflow_id": str,
            "step": int,
            "status": str,
            "next_step": int | None,
            "next_step_name": str | None
        }
    """
    try:
        state = _load_workflow_state(workflow_id)
        workflow_type = state.get("workflow_type")

        if workflow_type != "generation":
            return {"error": "Only generation workflow supported currently"}

        gen_state = state.get("generation", {})
        steps = gen_state.get("steps", [])

        # Find step
        step_data = next((s for s in steps if s["step"] == step), None)
        if not step_data:
            return {"error": f"Invalid step number: {step}"}

        # Check if step requires approval
        if step_data.get("status") != "waiting_approval":
            return {"error": f"Step {step} is not waiting for approval"}

        # Update step status
        if approved:
            step_data["status"] = "completed"
            step_data["completed_at"] = datetime.now(timezone.utc).isoformat()

            if modifications:
                step_data.setdefault("human_approval", {})["modifications"] = modifications

            # Update current step
            gen_state["current_step"] = step + 1

            # Determine next step
            next_step_data = next((s for s in steps if s["step"] == step + 1), None)
            next_step = step + 1 if next_step_data else None
            next_step_name = next_step_data.get("name") if next_step_data else None
        else:
            step_data["status"] = "failed"
            state["status"] = "failed"
            next_step = None
            next_step_name = None

        _save_workflow_state(workflow_id, state)

        return {
            "success": True,
            "workflow_id": workflow_id,
            "step": step,
            "status": step_data["status"],
            "next_step": next_step,
            "next_step_name": next_step_name,
        }

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to approve step: {e}"}


@mcp.tool()
def update_workflow_state(
    workflow_id: str,
    step: Optional[int] = None,
    status: Optional[str] = None,
    artifacts: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update workflow state (internal tool for agents).

    Used by workflow agents to update step status and artifacts.

    Args:
        workflow_id: Workflow ID
        step: Step number being updated
        status: New status for step
        artifacts: Artifacts produced by step

    Returns:
        {
            "success": bool,
            "workflow_id": str,
            "updated_at": str
        }
    """
    try:
        state = _load_workflow_state(workflow_id)
        workflow_type = state.get("workflow_type")

        if workflow_type != "generation":
            return {"error": "Only generation workflow supported currently"}

        gen_state = state.get("generation", {})
        steps = gen_state.get("steps", [])

        if step:
            # Find step
            step_data = next((s for s in steps if s["step"] == step), None)
            if not step_data:
                return {"error": f"Invalid step number: {step}"}

            # Update step status
            if status:
                step_data["status"] = status

                if status == "in_progress" and not step_data.get("started_at"):
                    step_data["started_at"] = datetime.now(timezone.utc).isoformat()
                elif status == "completed":
                    step_data["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Update artifacts
            if artifacts:
                step_data.setdefault("artifacts", {}).update(artifacts)

        # Update overall workflow status based on step statuses
        if any(s.get("status") == "failed" for s in steps):
            state["status"] = "failed"
        elif all(s.get("status") == "completed" for s in steps):
            state["status"] = "completed"
        elif any(s.get("status") == "waiting_approval" for s in steps):
            state["status"] = "waiting_approval"
        else:
            state["status"] = "in_progress"

        _save_workflow_state(workflow_id, state)

        return {
            "success": True,
            "workflow_id": workflow_id,
            "updated_at": state["updated_at"],
        }

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to update workflow state: {e}"}


@mcp.tool()
def list_workflows(
    status: Optional[str] = None,
    workflow_type: Optional[str] = None,
    session_name: Optional[str] = None
) -> Dict[str, Any]:
    """List all workflows (optionally filter by status).

    Returns list of workflows matching filter criteria.

    Args:
        status: Filter by status
        workflow_type: Filter by workflow type
        session_name: Filter by session name

    Returns:
        {
            "workflows": list[dict],
            "total": int
        }
    """
    try:
        workflows = []

        # Check session directory first
        active_session = _get_active_session()
        if active_session or session_name:
            target_session = session_name or active_session
            session_state_dir = SESSIONS_PATH / target_session / "workflow-state"

            if session_state_dir.exists():
                for state_file in session_state_dir.glob("*.json"):
                    if state_file.name == "index.json":
                        continue

                    try:
                        with open(state_file, 'r') as f:
                            state = json.load(f)

                        # Apply filters
                        if status and state.get("status") != status:
                            continue
                        if workflow_type and state.get("workflow_type") != workflow_type:
                            continue

                        workflows.append({
                            "workflow_id": state.get("workflow_id"),
                            "workflow_type": state.get("workflow_type"),
                            "status": state.get("status"),
                            "progress_percentage": _calculate_progress(state),
                            "created_at": state.get("created_at"),
                            "updated_at": state.get("updated_at"),
                        })
                    except Exception:
                        continue

        # Check global directory if no session filter
        if not session_name:
            global_state_dir = GLOBAL_WORKFLOW_STATE_DIR

            if global_state_dir.exists():
                for state_file in global_state_dir.glob("*.json"):
                    if state_file.name == "index.json":
                        continue

                    try:
                        with open(state_file, 'r') as f:
                            state = json.load(f)

                        # Apply filters
                        if status and state.get("status") != status:
                            continue
                        if workflow_type and state.get("workflow_type") != workflow_type:
                            continue

                        workflows.append({
                            "workflow_id": state.get("workflow_id"),
                            "workflow_type": state.get("workflow_type"),
                            "status": state.get("status"),
                            "progress_percentage": _calculate_progress(state),
                            "created_at": state.get("created_at"),
                            "updated_at": state.get("updated_at"),
                        })
                    except Exception:
                        continue

        return {
            "workflows": workflows,
            "total": len(workflows),
        }

    except Exception as e:
        return {"error": f"Failed to list workflows: {e}"}


@mcp.tool()
def resume_workflow(
    workflow_id: str,
    from_step: Optional[int] = None
) -> Dict[str, Any]:
    """Resume failed/cancelled workflow.

    Allows continuing workflow from last completed step or specified step.

    Args:
        workflow_id: Workflow ID to resume
        from_step: Step to resume from (defaults to last completed + 1)

    Returns:
        {
            "success": bool,
            "workflow_id": str,
            "resumed_from_step": int,
            "current_status": str
        }
    """
    try:
        state = _load_workflow_state(workflow_id)
        workflow_type = state.get("workflow_type")

        if workflow_type != "generation":
            return {"error": "Only generation workflow supported currently"}

        gen_state = state.get("generation", {})
        steps = gen_state.get("steps", [])

        # Determine resume point
        if from_step:
            resume_step = from_step
        else:
            # Find last completed step
            completed_steps = [s["step"] for s in steps if s.get("status") == "completed"]
            if not completed_steps:
                resume_step = 1
            else:
                resume_step = max(completed_steps) + 1

        # Validate resume step
        if resume_step > len(steps):
            return {"error": f"Invalid resume step: {resume_step}. Workflow has {len(steps)} steps"}

        # Reset failed/cancelled status
        if state.get("status") in ["failed", "cancelled"]:
            state["status"] = "in_progress"

        # Update current step
        gen_state["current_step"] = resume_step

        # Reset step status from resume point onwards
        for step_data in steps:
            if step_data["step"] >= resume_step:
                step_data["status"] = "pending"
                step_data["started_at"] = None
                step_data["completed_at"] = None

        _save_workflow_state(workflow_id, state)

        return {
            "success": True,
            "workflow_id": workflow_id,
            "resumed_from_step": resume_step,
            "current_status": state["status"],
        }

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to resume workflow: {e}"}


@mcp.tool()
def cancel_workflow(
    workflow_id: str,
    reason: str = "User requested cancellation"
) -> Dict[str, Any]:
    """Cancel active workflow.

    Marks workflow as cancelled and performs cleanup.

    Args:
        workflow_id: Workflow ID to cancel
        reason: Reason for cancellation

    Returns:
        {
            "success": bool,
            "workflow_id": str,
            "status": str,
            "cleanup_performed": bool
        }
    """
    try:
        state = _load_workflow_state(workflow_id)

        # Update status
        state["status"] = "cancelled"
        state["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        state["cancellation_reason"] = reason

        _save_workflow_state(workflow_id, state)

        # Cleanup is minimal - just mark as cancelled
        # Artifacts remain for potential resume
        cleanup_performed = True

        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": state["status"],
            "cleanup_performed": cleanup_performed,
        }

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to cancel workflow: {e}"}


if __name__ == "__main__":
    mcp.run()
