#!/usr/bin/env python3
"""
Generation State Tracker MCP Server (FEAT-0002)

This MCP server provides tools to manage FEAT-0001 scene generation workflow states.
It enables tracking, resuming, and monitoring of generation workflows through persistent
state files.

Features:
- Resume failed/interrupted workflows from saved state
- Check real-time status and progress of running generations
- Cancel running workflows with state preservation
- List all generation workflows with filtering

State files are stored as: workspace/generation-state-{scene_id}.json
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import json
import glob

from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("generation_state_mcp")

# Constants
WORKSPACE_PATH = Path("workspace")
SESSIONS_PATH = WORKSPACE_PATH / "sessions"
SESSION_LOCK_FILE = WORKSPACE_PATH / "session.lock"
STATE_FILE_PATTERN = "generation-state-*.json"
CHARACTER_LIMIT = 25000  # Maximum response size in characters

# Valid step names for Scene Generation Workflow v2.0
VALID_STEP_NAMES = [
    "scene:gen:setup:files",
    "scene:gen:setup:blueprint",
    "scene:gen:setup:plan",
    "scene:gen:draft:prose",
    "scene:gen:review:validation",
    "scene:gen:publish:output"
]

# Step order for resume logic
STEP_ORDER = VALID_STEP_NAMES.copy()

# Enums
class WorkflowStatus(str, Enum):
    """Possible workflow statuses."""
    NOT_FOUND = "NOT_FOUND"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_USER_APPROVAL = "WAITING_USER_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class StepStatus(str, Enum):
    """Possible step statuses."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class FilterType(str, Enum):
    """Filter types for list_generations."""
    ALL = "all"
    ACTIVE = "active"
    FAILED = "failed"
    COMPLETED = "completed"

class ErrorSeverity(str, Enum):
    """Error severity levels for record_error tool."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

# Pydantic Models for Input Validation

class ResumeGenerationInput(BaseModel):
    """Input model for resume_generation tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID to resume (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    force: bool = Field(
        default=False,
        description="Force resume even if state is old (>24h) or warnings present"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v


class GetGenerationStatusInput(BaseModel):
    """Input model for get_generation_status tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID to check status (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    detailed: bool = Field(
        default=False,
        description="Return detailed status including all steps and timing"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v


class CancelGenerationInput(BaseModel):
    """Input model for cancel_generation tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID to cancel (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for cancellation",
        max_length=500
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v


class ListGenerationsInput(BaseModel):
    """Input model for list_generations tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    filter: FilterType = Field(
        default=FilterType.ALL,
        description="Filter generations by status: 'all', 'active', 'failed', 'completed'"
    )
    sort_by: str = Field(
        default="started_at",
        description="Sort results by field: 'scene_id', 'started_at', 'status'"
    )

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort_by field."""
        allowed = ['scene_id', 'started_at', 'status']
        if v not in allowed:
            raise ValueError(f"sort_by must be one of: {', '.join(allowed)}")
        return v


class StartGenerationInput(BaseModel):
    """Input model for start_generation tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID to initialize (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    blueprint_path: str = Field(
        ...,
        description="Path to scene blueprint file (e.g., 'acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md')",
        min_length=1,
        max_length=500
    )
    initiated_by: str = Field(
        default="generation-coordinator",
        description="Name of agent or user initiating generation",
        max_length=100
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for tracking (e.g., {'user_id': '123', 'session': 'interactive'})"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v


class StartStepInput(BaseModel):
    """Input model for start_step tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    step_name: str = Field(
        ...,
        description="Semantic step name (e.g., 'scene:gen:setup:files', 'scene:gen:draft:prose')"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata (e.g., {'agent_name': 'blueprint-validator', 'phase_name': 'Blueprint Validation'})"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v

    @field_validator('step_name')
    @classmethod
    def validate_step_name(cls, v: str) -> str:
        """Validate step name against VALID_STEP_NAMES."""
        if v not in VALID_STEP_NAMES:
            valid_names = "\n  - ".join(VALID_STEP_NAMES)
            raise ValueError(
                f"Invalid step_name: '{v}'\n"
                f"Must be one of:\n  - {valid_names}"
            )
        return v


class CompleteStepInput(BaseModel):
    """Input model for complete_step tool."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    step_name: str = Field(
        ...,
        description="Semantic step name (e.g., 'scene:gen:setup:files', 'scene:gen:draft:prose')"
    )
    duration_seconds: float = Field(
        ...,
        description="Time taken to complete step in seconds (e.g., 45.2)",
        ge=0
    )
    artifacts: Optional[Dict[str, str]] = Field(
        default=None,
        description="Artifact paths produced by this step (e.g., {'constraints_list_path': 'workspace/artifacts/scene-0204-constraints.json'})"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional step completion metadata (use {'workflow_complete': True} for final step)"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v

    @field_validator('step_name')
    @classmethod
    def validate_step_name(cls, v: str) -> str:
        """Validate step name against VALID_STEP_NAMES."""
        if v not in VALID_STEP_NAMES:
            valid_names = "\n  - ".join(VALID_STEP_NAMES)
            raise ValueError(
                f"Invalid step_name: '{v}'\n"
                f"Must be one of:\n  - {valid_names}"
            )
        return v


class FailStepInput(BaseModel):
    """Input model for fail_step tool.

    Records step failure with errors. NOT necessarily terminal - coordinator
    can call retry_step() afterwards. Terminal failure = fail_step() with
    metadata={'terminal': True} WITHOUT subsequent retry_step().
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    step_name: str = Field(
        ...,
        description="Semantic step name (e.g., 'scene:gen:draft:prose')"
    )
    failure_reason: str = Field(
        ...,
        description="Detailed reason for step failure (e.g., 'Constraint violations: location, character_knowledge')",
        min_length=1,
        max_length=1000
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata (e.g., {'attempt': 1, 'severity': 'MEDIUM', 'terminal': False})"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v

    @field_validator('step_name')
    @classmethod
    def validate_step_name(cls, v: str) -> str:
        """Validate step name against VALID_STEP_NAMES."""
        if v not in VALID_STEP_NAMES:
            valid_names = "\n  - ".join(VALID_STEP_NAMES)
            raise ValueError(
                f"Invalid step_name: '{v}'\n"
                f"Must be one of:\n  - {valid_names}"
            )
        return v


class RetryStepInput(BaseModel):
    """Input model for retry_step tool.

    Indicates coordinator is retrying a failed step. Only called after fail_step().
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    step_name: str = Field(
        ...,
        description="Semantic step name to retry (e.g., 'scene:gen:draft:prose')"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata (e.g., {'attempt_number': 2})"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v

    @field_validator('step_name')
    @classmethod
    def validate_step_name(cls, v: str) -> str:
        """Validate step name against VALID_STEP_NAMES."""
        if v not in VALID_STEP_NAMES:
            valid_names = "\n  - ".join(VALID_STEP_NAMES)
            raise ValueError(
                f"Invalid step_name: '{v}'\n"
                f"Must be one of:\n  - {valid_names}"
            )
        return v


class CompleteGenerationInput(BaseModel):
    """Input model for complete_generation tool.

    DEPRECATED: Use complete_step() with metadata={'workflow_complete': True} instead.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    final_scene_path: str = Field(
        ...,
        description="Path to final generated scene file (e.g., 'acts/act-1/chapters/chapter-02/content/scene-0204.md')",
        min_length=1,
        max_length=500
    )
    validation_report_path: str = Field(
        ...,
        description="Path to validation report (e.g., 'workspace/artifacts/scene-0204-validation-report.md')",
        min_length=1,
        max_length=500
    )
    word_count: int = Field(
        ...,
        description="Final word count of generated scene",
        ge=0
    )
    total_duration_seconds: float = Field(
        ...,
        description="Total time from start_generation to completion in seconds",
        ge=0
    )
    retry_count: int = Field(
        default=0,
        description="Number of generation retries before success (0 if succeeded on first attempt)",
        ge=0,
        le=3
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v


class LogQuestionAnswerInput(BaseModel):
    """Input model for log_question_answer tool (BONUS feature)."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    scene_id: str = Field(
        ...,
        description="Scene ID (4 digits, e.g., '0204')",
        pattern=r"^[0-9]{4}$",
        min_length=4,
        max_length=4
    )
    question: str = Field(
        ...,
        description="Question asked to user via QuestionTool",
        min_length=1,
        max_length=2000
    )
    answer: str = Field(
        ...,
        description="User's answer to the question",
        min_length=1,
        max_length=5000
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO format timestamp (auto-generated if not provided)"
    )

    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Scene ID must be exactly 4 digits (e.g., '0204')")
        return v


# Shared Utility Functions

def _get_active_session() -> Optional[str]:
    """Get active session name from session.lock.

    Returns:
        Session name or None if no active session
    """
    if not SESSION_LOCK_FILE.exists():
        return None

    try:
        with open(SESSION_LOCK_FILE, 'r') as f:
            lock_data = json.load(f)
        return lock_data.get("active")
    except Exception:
        return None


def _get_state_file_path(scene_id: str) -> Path:
    """Get path to state file for scene ID.

    Checks session directory first (if active session exists), then global.

    Args:
        scene_id: Scene ID (4 digits)

    Returns:
        Path to state file (may not exist)
    """
    session_name = _get_active_session()

    # If active session, prefer session directory
    if session_name:
        session_state_path = SESSIONS_PATH / session_name / f"generation-state-{scene_id}.json"
        # Return session path if it exists, or if no global exists (for new states)
        if session_state_path.exists():
            return session_state_path

        # Check if global exists - if so, return global for reading
        global_state_path = WORKSPACE_PATH / f"generation-state-{scene_id}.json"
        if global_state_path.exists():
            return global_state_path

        # Neither exists - return session path for writing (session-aware)
        return session_state_path

    # No active session - use global
    return WORKSPACE_PATH / f"generation-state-{scene_id}.json"


def _load_state_file(scene_id: str) -> Optional[Dict[str, Any]]:
    """Load state file for scene ID.

    Args:
        scene_id: Scene ID (4 digits)

    Returns:
        State dict or None if file doesn't exist

    Raises:
        ValueError: If state file is corrupted or invalid JSON
    """
    state_path = _get_state_file_path(scene_id)

    if not state_path.exists():
        return None

    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        return state
    except json.JSONDecodeError as e:
        raise ValueError(f"State file corrupted: {state_path}. JSON error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to read state file {state_path}: {str(e)}")


def _save_state_file(scene_id: str, state: Dict[str, Any]) -> None:
    """Save state file for scene ID.

    Args:
        scene_id: Scene ID (4 digits)
        state: State dictionary to save

    Raises:
        ValueError: If failed to write state file
    """
    state_path = _get_state_file_path(scene_id)

    # Ensure parent directory exists (workspace or session dir)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ValueError(f"Failed to write state file {state_path}: {str(e)}")


def _list_state_files() -> List[Path]:
    """List all state files in workspace (global and session).

    Checks session directory first (if active), then global directory.

    Returns:
        List of state file paths
    """
    state_files = []

    # Check session directory first if active session exists
    session_name = _get_active_session()
    if session_name:
        session_dir = SESSIONS_PATH / session_name
        if session_dir.exists():
            session_pattern = str(session_dir / STATE_FILE_PATTERN)
            state_files.extend([Path(p) for p in glob.glob(session_pattern)])

    # Check global directory
    if WORKSPACE_PATH.exists():
        global_pattern = str(WORKSPACE_PATH / STATE_FILE_PATTERN)
        state_files.extend([Path(p) for p in glob.glob(global_pattern)])

    return state_files


def _validate_state(state: Dict[str, Any], scene_id: str) -> List[str]:
    """Validate state structure and content.

    Args:
        state: State dictionary to validate
        scene_id: Expected scene ID

    Returns:
        List of validation warnings (empty if valid)
    """
    warnings = []

    # Check required fields
    required_fields = ['scene_id', 'workflow_status', 'current_step', 'started_at']
    for field in required_fields:
        if field not in state:
            warnings.append(f"Missing required field: {field}")

    # Check scene_id matches
    if state.get('scene_id') != scene_id:
        warnings.append(f"Scene ID mismatch: expected {scene_id}, got {state.get('scene_id')}")

    # Check workflow_status is valid
    if state.get('workflow_status') not in [s.value for s in WorkflowStatus]:
        warnings.append(f"Invalid workflow_status: {state.get('workflow_status')}")

    # Check current_step is valid (1-7)
    current_step = state.get('current_step')
    if current_step is not None and (current_step < 1 or current_step > 7):
        warnings.append(f"Invalid current_step: {current_step} (must be 1-7)")

    return warnings


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "3m 45s", "1h 23m 15s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m {secs}s"


def _calculate_elapsed_time(started_at: str, updated_at: Optional[str] = None) -> str:
    """Calculate elapsed time from started_at to now or updated_at.

    Args:
        started_at: ISO format timestamp
        updated_at: Optional ISO format timestamp (defaults to now)

    Returns:
        Human-readable elapsed time
    """
    try:
        start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))

        if updated_at:
            end = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)

        delta = (end - start).total_seconds()
        return _format_duration(delta)
    except Exception:
        return "unknown"


def _format_status_markdown(state: Dict[str, Any], detailed: bool = False) -> str:
    """Format state as human-readable markdown.

    Args:
        state: State dictionary
        detailed: Include detailed step information

    Returns:
        Formatted markdown string
    """
    lines = []

    # Header
    scene_id = state.get('scene_id', 'unknown')
    status = state.get('workflow_status', 'unknown')
    lines.append(f"# 📊 GENERATION STATUS: Scene {scene_id}")
    lines.append("")

    # Session info
    session_id = state.get('session_id', 'unknown')
    lines.append(f"**Session ID**: {session_id}")

    started_at = state.get('started_at', '')
    elapsed = _calculate_elapsed_time(started_at, state.get('updated_at'))
    lines.append(f"**Started**: {started_at} ({elapsed} ago)")
    lines.append("")

    # Progress
    current_step = state.get('current_step', 0)
    current_phase = state.get('current_phase', 'unknown')
    lines.append(f"**Progress**: Step {current_step}/7 ({status})")
    lines.append(f"**Current Phase**: {current_phase}")
    lines.append("")

    # Step-by-step progress
    if detailed and 'steps' in state:
        lines.append("## 📋 Detailed Progress")
        lines.append("")

        step_names = {
            'step_1_file_check': 'File System Check',
            'step_2_blueprint_validation': 'Blueprint Validation',
            'step_3_verification_plan': 'Verification Plan',
            'step_4_generation': 'Prose Generation',
            'step_5_fast_compliance': 'Fast Compliance Check',
            'step_6_full_validation': 'Full Validation',
            'step_7_final_output': 'Final Output'
        }

        for step_key, step_name in step_names.items():
            if step_key in state['steps']:
                step_data = state['steps'][step_key]
                step_status = step_data.get('status', 'PENDING')

                # Status icon
                if step_status == 'COMPLETED':
                    icon = '✓'
                elif step_status == 'IN_PROGRESS':
                    icon = '⏳'
                elif step_status == 'FAILED':
                    icon = '❌'
                else:
                    icon = '⋯'

                # Duration
                duration_sec = step_data.get('duration_seconds', 0)
                duration = _format_duration(duration_sec) if duration_sec else ''

                lines.append(f"{icon} **{step_name}** ({step_status}){' - ' + duration if duration else ''}")

        lines.append("")

    # Generation attempts (if in Step 4)
    if 'generation_attempts' in state:
        attempts = state['generation_attempts']
        current = attempts.get('current_attempt', 0)
        max_attempts = attempts.get('max_attempts', 3)
        lines.append(f"**Generation Attempts**: {current}/{max_attempts}")
        lines.append("")

    # Artifacts
    if 'artifacts' in state:
        lines.append("## 📁 Artifacts")
        for key, path in state['artifacts'].items():
            if path:
                lines.append(f"- **{key}**: {path}")
        lines.append("")

    # Errors (if any)
    if state.get('errors'):
        lines.append("## ⚠️ Errors")
        for error in state['errors']:
            lines.append(f"- {error.get('message', 'Unknown error')}")
        lines.append("")

    return "\n".join(lines)


def _handle_error(e: Exception) -> str:
    """Format exception as error message.

    Args:
        e: Exception to format

    Returns:
        Formatted error message
    """
    if isinstance(e, ValueError):
        return f"Error: {str(e)}"
    elif isinstance(e, FileNotFoundError):
        return f"Error: File not found - {str(e)}"
    elif isinstance(e, PermissionError):
        return f"Error: Permission denied - {str(e)}"
    else:
        return f"Error: Unexpected error occurred: {type(e).__name__} - {str(e)}"


def _get_step_index(step_name: str) -> int:
    """Get step index (0-based) from step name.

    Args:
        step_name: Semantic step name (e.g., 'scene:gen:setup:files')

    Returns:
        0-based index in STEP_ORDER (0-5)

    Raises:
        ValueError: If step_name not in VALID_STEP_NAMES
    """
    if step_name not in VALID_STEP_NAMES:
        raise ValueError(f"Invalid step_name: {step_name}")
    return STEP_ORDER.index(step_name)


def _initialize_state_structure(
    scene_id: str,
    blueprint_path: str,
    initiated_by: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create initial state structure for new generation workflow.

    Args:
        scene_id: Scene ID (4 digits)
        blueprint_path: Path to blueprint file
        initiated_by: Name of initiator
        metadata: Optional metadata dict

    Returns:
        Complete initial state structure
    """
    now = datetime.now(timezone.utc).isoformat()
    session_id = f"{now[:10]}-{now[11:19].replace(':', '')}-scene-{scene_id}"

    return {
        "scene_id": scene_id,
        "session_id": session_id,
        "started_at": now,
        "updated_at": now,
        "current_phase": "INITIALIZED",
        "current_step": None,  # Will be set on first start_step() call
        "workflow_status": WorkflowStatus.IN_PROGRESS.value,
        "steps": {},  # Keys are step names (e.g., "scene:gen:setup:files")
        "generation_attempts": {
            "current_attempt": 0,
            "max_attempts": 3,
            "attempts_history": []
        },
        "artifacts": {
            "blueprint_path": blueprint_path
        },
        "user_interactions": [],
        "user_questions": [],  # For log_question_answer
        "errors": [],
        "metadata": {
            "initiated_by": initiated_by,
            "total_duration_seconds": 0,
            **(metadata or {})
        }
    }


def _update_step_status(
    state: Dict[str, Any],
    step_name: str,
    status: str,
    **kwargs
) -> None:
    """Update step status in state dict (modifies in place).

    Args:
        state: State dictionary to modify
        step_name: Semantic step name (e.g., 'scene:gen:setup:files')
        status: New status (PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED)
        **kwargs: Additional fields to set (duration_seconds, agent_used, etc.)
    """
    if step_name not in state['steps']:
        state['steps'][step_name] = {}

    state['steps'][step_name]['status'] = status
    state['updated_at'] = datetime.now(timezone.utc).isoformat()

    # Set additional fields
    for key, value in kwargs.items():
        if value is not None:
            state['steps'][step_name][key] = value


def _advance_workflow(state: Dict[str, Any], completed_step_name: str) -> None:
    """Advance workflow to next step (modifies state in place).

    Args:
        state: State dictionary to modify
        completed_step_name: Step name that was just completed
    """
    current_index = _get_step_index(completed_step_name)

    # Advance to next step if not at end
    if current_index < len(STEP_ORDER) - 1:
        state['current_step'] = STEP_ORDER[current_index + 1]
    else:
        # Workflow complete
        state['current_step'] = completed_step_name  # Keep on last step

    state['updated_at'] = datetime.now(timezone.utc).isoformat()


# Tool Definitions

@mcp.tool(
    name="resume_generation",
    annotations={
        "title": "Resume Generation Workflow",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def resume_generation(params: ResumeGenerationInput) -> str:
    """Resume a failed or interrupted scene generation workflow from saved state.

    This tool loads the saved state for a scene generation workflow and determines
    the appropriate resume point. It validates the state, checks for warnings,
    and provides guidance for continuing the workflow.

    Args:
        params (ResumeGenerationInput): Validated input parameters containing:
            - scene_id (str): Scene ID to resume (4 digits, e.g., '0204')
            - force (bool): Force resume even if warnings present (default: False)

    Returns:
        str: Markdown-formatted resume plan including:
            - Loaded state summary
            - Resume point (which step to continue from)
            - Completed steps (will be skipped)
            - Pending steps (will be executed)
            - Any warnings or recommendations
            - Time saved by resuming (vs starting from scratch)

    Error Handling:
        - Returns "Error: No state found for scene {ID}" if state file doesn't exist
        - Returns "Error: State file corrupted" if JSON is invalid
        - Returns "Error: Scene {ID} already completed" if workflow finished
        - Returns "Error: Scene {ID} is currently running" if workflow active
        - Returns validation warnings if state has issues (can be overridden with force=True)

    Examples:
        - Use when: Generation failed at Step 4 and you want to retry
        - Use when: Workflow was cancelled and you want to continue
        - Don't use when: Scene hasn't been generated yet (no state exists)
        - Don't use when: You want to start fresh generation (use generation-coordinator instead)
    """
    scene_id = params.scene_id

    try:
        # Load state file
        state = _load_state_file(scene_id)

        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}\n\n" \
                   f"Possible reasons:\n" \
                   f"  1. Scene never generated\n" \
                   f"  2. State file deleted\n" \
                   f"  3. Wrong scene ID\n\n" \
                   f"💡 Next steps:\n" \
                   f"  - Check scene exists: acts/.../scene-{scene_id}-blueprint.md\n" \
                   f"  - List all generations: Use list_generations tool\n" \
                   f"  - Start new generation: \"Generate scene {scene_id}\""

        # Validate state
        warnings = _validate_state(state, scene_id)
        if warnings and not params.force:
            return f"⚠️ WARNING: State validation issues for scene {scene_id}\n\n" \
                   + "\n".join(f"  - {w}" for w in warnings) + "\n\n" \
                   f"💡 To proceed anyway, use: resume_generation(scene_id='{scene_id}', force=True)"

        # Check workflow status
        workflow_status = state.get('workflow_status')

        if workflow_status == WorkflowStatus.COMPLETED.value:
            return f"❌ ERROR: Scene {scene_id} already completed\n\n" \
                   f"Completed at: {state.get('updated_at', 'unknown')}\n" \
                   f"Session ID: {state.get('session_id', 'unknown')}\n\n" \
                   f"💡 View final output: {state.get('artifacts', {}).get('final_scene_path', 'unknown')}"

        if workflow_status == WorkflowStatus.IN_PROGRESS.value:
            return f"❌ ERROR: Scene {scene_id} is currently running\n\n" \
                   f"Current status: Step {state.get('current_step', '?')}/7 ({state.get('current_phase', 'unknown')})\n" \
                   f"Started: {state.get('started_at', 'unknown')}\n\n" \
                   f"💡 Options:\n" \
                   f"  - Wait for completion (~2-3 minutes remaining)\n" \
                   f"  - Check progress: get_generation_status(scene_id='{scene_id}')\n" \
                   f"  - Cancel if needed: cancel_generation(scene_id='{scene_id}')"

        # Find resume point
        steps = state.get('steps', {})
        resume_step = 1
        completed_steps = []

        step_order = [
            'step_1_file_check',
            'step_2_blueprint_validation',
            'step_3_verification_plan',
            'step_4_generation',
            'step_5_fast_compliance',
            'step_6_full_validation',
            'step_7_final_output'
        ]

        for i, step_key in enumerate(step_order, start=1):
            if step_key in steps:
                step_status = steps[step_key].get('status')
                if step_status == StepStatus.COMPLETED.value:
                    completed_steps.append(i)
                    resume_step = i + 1
                else:
                    break

        # Calculate time saved
        time_saved = sum(
            steps.get(step_order[i-1], {}).get('duration_seconds', 0)
            for i in completed_steps
        )

        # Build resume plan
        lines = [
            f"🔧 RESUMING GENERATION: Scene {scene_id}",
            "",
            f"📂 Loading state: workspace/generation-state-{scene_id}.json",
            "",
            "✓ State loaded:",
            f"  - Session ID: {state.get('session_id', 'unknown')}",
            f"  - Started: {state.get('started_at', 'unknown')}",
            f"  - Failed at: Step {state.get('current_step', '?')} ({state.get('current_phase', 'unknown')})",
            f"  - Reason: {state.get('errors', [{}])[0].get('message', 'Unknown') if state.get('errors') else 'Unknown'}",
            "",
            "📋 Recovery Plan:",
            ""
        ]

        step_names = [
            "File System Check",
            "Blueprint Validation",
            "Verification Plan",
            "Prose Generation",
            "Fast Compliance Check",
            "Full Validation",
            "Final Output"
        ]

        for i in range(1, 8):
            if i in completed_steps:
                duration = steps.get(step_order[i-1], {}).get('duration_seconds', 0)
                lines.append(f"✓ Step {i}: {step_names[i-1]} (SKIP - already completed, {_format_duration(duration)})")
            elif i == resume_step:
                lines.append(f"⚠️ Step {i}: {step_names[i-1]} (RESUME - was at this step)")
                lines.append(f"   → Will reset attempts counter")
                lines.append(f"   → Will re-read blueprint (may have been fixed)")
                lines.append(f"   → Will use enhanced constraint emphasis")
            else:
                lines.append(f"⏭️ Step {i}: {step_names[i-1]} (will run after Step {i-1})")

        lines.append("")
        lines.append(f"⚡ Time saved: ~{_format_duration(time_saved)} (Steps {min(completed_steps) if completed_steps else 'none'}-{max(completed_steps) if completed_steps else 'none'} already completed)")
        lines.append("")

        if warnings:
            lines.append("⚠️ Warnings (force=True used):")
            lines.extend(f"  - {w}" for w in warnings)
            lines.append("")

        lines.append("❓ Proceed with resume? The generation-coordinator will continue from this state.")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="get_generation_status",
    annotations={
        "title": "Get Generation Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_generation_status(params: GetGenerationStatusInput) -> str:
    """Get current status and progress of a scene generation workflow.

    This tool reads the state file for a scene generation and formats it as
    human-readable markdown showing current progress, timing, and next steps.

    Args:
        params (GetGenerationStatusInput): Validated input parameters containing:
            - scene_id (str): Scene ID to check (4 digits, e.g., '0204')
            - detailed (bool): Include detailed step breakdown (default: False)

    Returns:
        str: Markdown-formatted status report including:
            - Current step (X/7) and phase name
            - Time elapsed since start
            - Step-by-step progress (if detailed=True)
            - Generation attempts (if in Step 4)
            - Artifact paths
            - Error messages (if any)
            - Next action required

    Error Handling:
        - Returns "Error: No state found for scene {ID}" if state file doesn't exist
        - Returns "Error: State file corrupted" if JSON is invalid
        - Returns formatted status even if state has validation warnings

    Examples:
        - Use when: Want to check progress of running generation
        - Use when: Need to see which step failed and why
        - Use when: Want to monitor long-running Step 4 (generation)
        - Don't use when: Scene hasn't been generated yet (will return NOT_FOUND)
    """
    scene_id = params.scene_id

    try:
        # Load state file
        state = _load_state_file(scene_id)

        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}\n\n" \
                   f"Scene has not been generated yet, or state file was deleted.\n\n" \
                   f"💡 Next steps:\n" \
                   f"  - Start generation: \"Generate scene {scene_id}\"\n" \
                   f"  - List all generations: Use list_generations tool"

        # Format status
        return _format_status_markdown(state, detailed=params.detailed)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="cancel_generation",
    annotations={
        "title": "Cancel Generation Workflow",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def cancel_generation(params: CancelGenerationInput) -> str:
    """Cancel a currently running scene generation workflow.

    This tool updates the state file to mark the workflow as CANCELLED and
    preserves all completed work. The workflow can be resumed later from the
    cancellation point.

    Args:
        params (CancelGenerationInput): Validated input parameters containing:
            - scene_id (str): Scene ID to cancel (4 digits, e.g., '0204')
            - reason (Optional[str]): Optional reason for cancellation

    Returns:
        str: Markdown-formatted cancellation report including:
            - Cancellation confirmation
            - Current progress at time of cancellation
            - Completed steps (preserved)
            - Interrupted step (partially completed)
            - State file path (for future resume)
            - Cleanup actions taken

    Error Handling:
        - Returns "Error: No state found for scene {ID}" if state file doesn't exist
        - Returns "Error: State file corrupted" if JSON is invalid
        - Returns "Error: Already completed" if workflow finished
        - Returns "Error: Already cancelled" if workflow previously cancelled
        - Returns info message if workflow not currently running (but allows cancel)

    Examples:
        - Use when: Realized blueprint has error mid-generation
        - Use when: Need to stop generation to make urgent changes
        - Use when: Generation is taking too long (stuck)
        - Don't use when: Want to fail and retry automatically (use generation-coordinator retry logic)
    """
    scene_id = params.scene_id

    try:
        # Load state file
        state = _load_state_file(scene_id)

        if state is None:
            return f"❌ ERROR: No generation found for scene {scene_id}\n\n" \
                   f"State file does not exist.\n\n" \
                   f"💡 Next steps:\n" \
                   f"  - List all generations: Use list_generations tool"

        # Check workflow status
        workflow_status = state.get('workflow_status')

        if workflow_status == WorkflowStatus.COMPLETED.value:
            return f"❌ ERROR: Cannot cancel completed workflow\n\n" \
                   f"Scene {scene_id} completed at: {state.get('updated_at', 'unknown')}\n\n" \
                   f"💡 If you want to regenerate, start a new generation: \"Generate scene {scene_id}\""

        if workflow_status == WorkflowStatus.CANCELLED.value:
            return f"❌ ERROR: Scene {scene_id} was already cancelled\n\n" \
                   f"Cancelled at: {state.get('updated_at', 'unknown')}\n" \
                   f"Reason: {state.get('cancellation_reason', 'No reason provided')}\n\n" \
                   f"💡 To resume: Use resume_generation(scene_id='{scene_id}')"

        # Update state to CANCELLED
        old_status = workflow_status
        state['workflow_status'] = WorkflowStatus.CANCELLED.value
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        state['cancellation_reason'] = params.reason or "User requested cancellation"

        # Save updated state
        _save_state_file(scene_id, state)

        # Build cancellation report
        lines = [
            f"🛑 CANCELLING GENERATION: Scene {scene_id}",
            "",
            f"⏸️ Previous status: {old_status} (Step {state.get('current_step', '?')}/7)",
            "",
            "✓ Cancelled successfully",
            "",
            "📊 Work completed before cancellation:"
        ]

        # List completed steps
        steps = state.get('steps', {})
        step_order = [
            'step_1_file_check',
            'step_2_blueprint_validation',
            'step_3_verification_plan',
            'step_4_generation',
            'step_5_fast_compliance',
            'step_6_full_validation',
            'step_7_final_output'
        ]

        step_names = [
            "File System Check",
            "Blueprint Validation",
            "Verification Plan",
            "Prose Generation",
            "Fast Compliance Check",
            "Full Validation",
            "Final Output"
        ]

        current_step = state.get('current_step', 0)

        for i, (step_key, step_name) in enumerate(zip(step_order, step_names), start=1):
            if step_key in steps:
                step_status = steps[step_key].get('status')
                duration = steps[step_key].get('duration_seconds', 0)

                if step_status == StepStatus.COMPLETED.value:
                    lines.append(f"   ✓ Step {i}: {step_name} ({_format_duration(duration)})")
                elif i == current_step:
                    lines.append(f"   ⏳ Step {i}: {step_name} ({_format_duration(duration)}, INTERRUPTED)")

        lines.append("")
        lines.append(f"💾 State saved: workspace/generation-state-{scene_id}.json")
        lines.append(f"   - Can resume later with: resume_generation(scene_id='{scene_id}')")

        if params.reason:
            lines.append("")
            lines.append(f"📝 Cancellation reason: {params.reason}")

        lines.append("")
        lines.append("🗑️ Cleanup:")
        lines.append("   - State preserved for future resume")

        # List preserved artifacts
        artifacts = state.get('artifacts', {})
        if artifacts:
            lines.append("   - Artifacts preserved:")
            for key, path in artifacts.items():
                if path:
                    lines.append(f"     • {path}")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="list_generations",
    annotations={
        "title": "List All Generations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_generations(params: ListGenerationsInput) -> str:
    """List all scene generations with their current status.

    This tool scans the workspace directory for all state files and presents
    them in a formatted table with key information about each generation.

    Args:
        params (ListGenerationsInput): Validated input parameters containing:
            - filter (FilterType): Filter by status - 'all', 'active', 'failed', 'completed' (default: 'all')
            - sort_by (str): Sort by field - 'scene_id', 'started_at', 'status' (default: 'started_at')

    Returns:
        str: Markdown-formatted table with columns:
            - Scene ID
            - Status (IN_PROGRESS, COMPLETED, FAILED, CANCELLED, etc.)
            - Current Step (X/7)
            - Started time (with relative time)
            - Duration (elapsed time)
            - Quick actions (links to status/resume commands)

        Also includes:
            - Total count
            - Legend for status types
            - Quick action suggestions
            - Filter information

    Error Handling:
        - Returns empty list if no state files found
        - Skips corrupted state files with warning
        - Returns error if workspace directory doesn't exist

    Examples:
        - Use when: Want to see all ongoing generations
        - Use when: Need to find failed generations to resume
        - Use when: Want to check which scenes have been completed
        - Use when: Monitoring multiple parallel generations
    """
    try:
        # List all state files
        state_files = _list_state_files()

        if not state_files:
            return "📋 GENERATION STATES (0 total)\n\n" \
                   "No generation states found.\n\n" \
                   "💡 Start a generation: \"Generate scene {scene_id}\""

        # Load all states
        generations = []
        corrupted_files = []

        for state_path in state_files:
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                generations.append(state)
            except Exception as e:
                corrupted_files.append(state_path.name)

        # Filter by status
        if params.filter == FilterType.ACTIVE:
            generations = [
                g for g in generations
                if g.get('workflow_status') in [
                    WorkflowStatus.IN_PROGRESS.value,
                    WorkflowStatus.WAITING_USER_APPROVAL.value,
                    WorkflowStatus.FAILED.value
                ]
            ]
        elif params.filter == FilterType.FAILED:
            generations = [
                g for g in generations
                if g.get('workflow_status') == WorkflowStatus.FAILED.value
            ]
        elif params.filter == FilterType.COMPLETED:
            generations = [
                g for g in generations
                if g.get('workflow_status') == WorkflowStatus.COMPLETED.value
            ]

        # Sort
        if params.sort_by == 'scene_id':
            generations.sort(key=lambda g: g.get('scene_id', ''))
        elif params.sort_by == 'status':
            generations.sort(key=lambda g: g.get('workflow_status', ''))
        else:  # started_at
            generations.sort(
                key=lambda g: g.get('started_at', ''),
                reverse=True  # Most recent first
            )

        # Build table
        lines = [
            f"📋 GENERATION STATES ({len(generations)} total)",
            ""
        ]

        if not generations:
            lines.append(f"No generations matching filter: {params.filter}")
            lines.append("")
            lines.append("💡 Try different filter: 'all', 'active', 'failed', 'completed'")
            return "\n".join(lines)

        # Table header
        lines.append("┌────────┬──────────────┬─────────┬──────────────┬──────────┬──────────┐")
        lines.append("│ Scene  │ Status       │ Step    │ Started      │ Duration │ Actions  │")
        lines.append("├────────┼──────────────┼─────────┼──────────────┼──────────┼──────────┤")

        # Table rows
        for gen in generations:
            scene_id = gen.get('scene_id', '????')
            status = gen.get('workflow_status', 'UNKNOWN')
            current_step = gen.get('current_step', 0)

            # Format started time
            started_at = gen.get('started_at', '')
            if started_at:
                try:
                    start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    start_str = start_dt.strftime('%H:%M')

                    # Calculate relative time
                    now = datetime.now(timezone.utc)
                    delta = (now - start_dt).total_seconds()

                    if delta < 3600:  # Less than 1 hour
                        relative = f"{int(delta // 60)}m"
                    elif delta < 86400:  # Less than 1 day
                        relative = f"{int(delta // 3600)}h"
                    else:
                        relative = "Yesterday" if delta < 172800 else f"{int(delta // 86400)}d ago"

                    started_str = f"{start_str} ({relative})"
                except Exception:
                    started_str = "unknown"
            else:
                started_str = "unknown"

            # Calculate duration
            duration = _calculate_elapsed_time(started_at, gen.get('updated_at'))

            # Actions based on status
            if status == WorkflowStatus.IN_PROGRESS.value:
                actions = "[Status]"
            elif status == WorkflowStatus.FAILED.value or status == WorkflowStatus.CANCELLED.value:
                actions = "[Resume]"
            elif status == WorkflowStatus.COMPLETED.value:
                actions = "[View]"
            else:
                actions = "-"

            # Truncate fields to fit table
            status_short = status[:12].ljust(12)
            started_short = started_str[:12].ljust(12)
            duration_short = duration[:8].ljust(8)

            lines.append(
                f"│ {scene_id}   │ {status_short} │ {current_step}/7     │ "
                f"{started_short} │ {duration_short} │ {actions.ljust(8)} │"
            )

        lines.append("└────────┴──────────────┴─────────┴──────────────┴──────────┴──────────┘")
        lines.append("")

        # Legend
        lines.append("Legend:")
        lines.append("  • IN_PROGRESS: Workflow currently running")
        lines.append("  • WAITING_USER_APPROVAL: Paused at Step 3, needs approval")
        lines.append("  • COMPLETED: Successfully finished all 7 steps")
        lines.append("  • FAILED: Stopped due to error (can resume)")
        lines.append("  • CANCELLED: Manually stopped by user (can resume)")
        lines.append("")

        # Quick actions
        lines.append("💡 Quick actions:")

        # Suggest checking first in-progress generation
        in_progress = [g for g in generations if g.get('workflow_status') == WorkflowStatus.IN_PROGRESS.value]
        if in_progress:
            first_scene = in_progress[0].get('scene_id')
            lines.append(f"   - Check details: get_generation_status(scene_id='{first_scene}')")
            lines.append(f"   - Cancel running: cancel_generation(scene_id='{first_scene}')")

        # Suggest resuming first failed generation
        failed = [g for g in generations if g.get('workflow_status') == WorkflowStatus.FAILED.value]
        if failed:
            first_failed = failed[0].get('scene_id')
            lines.append(f"   - Resume failed: resume_generation(scene_id='{first_failed}')")

        lines.append("")

        # Filters
        lines.append("🔍 Filters:")
        lines.append("   --active     Show only IN_PROGRESS, WAITING_USER_APPROVAL, FAILED")
        lines.append("   --completed  Show only COMPLETED")
        lines.append("   --failed     Show only FAILED (resumable)")
        lines.append("")

        # Warnings for corrupted files
        if corrupted_files:
            lines.append("⚠️ Warnings:")
            for filename in corrupted_files:
                lines.append(f"   - Skipped corrupted file: {filename}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="start_generation",
    annotations={
        "title": "Start Generation Workflow",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def start_generation(params: StartGenerationInput) -> str:
    """Initialize a new scene generation workflow by creating state file.

    This tool creates a new generation state file for a scene and initializes
    all workflow tracking structures. It's the first step in the 7-step generation
    workflow and must be called before any other state management tools.

    Args:
        params (StartGenerationInput): Validated input parameters containing:
            - scene_id (str): Scene ID to initialize (4 digits, e.g., '0204')
            - blueprint_path (str): Path to blueprint file
            - initiated_by (str): Name of initiator (default: 'generation-coordinator')
            - metadata (Optional[Dict]): Optional tracking metadata

    Returns:
        str: Markdown-formatted initialization report including:
            - Session ID (unique identifier for this workflow run)
            - Initial workflow status
            - State file path
            - Next steps guidance

    Error Handling:
        - Returns warning (not error) if state file already exists (idempotent behavior)
        - Returns error if workspace directory cannot be created
        - Returns error if state file cannot be written

    Examples:
        - Use when: Starting generation for scene 0204
        - Use when: Coordinator begins new workflow
        - Don't use when: Resuming existing workflow (use resume_generation instead)
        - Don't use when: Scene already has active state file

    Idempotency:
        - If state file exists and workflow IN_PROGRESS: Returns warning with existing session info
        - If state file exists and workflow terminal (COMPLETED/FAILED): Returns error suggesting new session_id
        - If state file doesn't exist: Creates new state file
    """
    scene_id = params.scene_id

    try:
        state_path = _get_state_file_path(scene_id)

        # Idempotency check: If state file exists, return info (don't fail)
        if state_path.exists():
            existing_state = _load_state_file(scene_id)
            if existing_state:
                status = existing_state.get('workflow_status')
                session_id = existing_state.get('session_id', 'unknown')

                if status == WorkflowStatus.IN_PROGRESS.value:
                    return f"⚠️ WARNING: Generation already in progress for scene {scene_id}\n\n" \
                           f"**Existing session**: {session_id}\n" \
                           f"**Status**: {status} (Step {existing_state.get('current_step', '?')}/7)\n" \
                           f"**Started**: {existing_state.get('started_at', 'unknown')}\n\n" \
                           f"💡 Options:\n" \
                           f"  - Continue existing workflow (no action needed)\n" \
                           f"  - Check progress: get_generation_status(scene_id='{scene_id}')\n" \
                           f"  - Cancel existing: cancel_generation(scene_id='{scene_id}')"

                elif status in [WorkflowStatus.COMPLETED.value, WorkflowStatus.FAILED.value]:
                    return f"❌ ERROR: Scene {scene_id} already has terminal state: {status}\n\n" \
                           f"**Session ID**: {session_id}\n" \
                           f"**Completed**: {existing_state.get('updated_at', 'unknown')}\n\n" \
                           f"💡 To start fresh generation:\n" \
                           f"  1. Archive existing state file\n" \
                           f"  2. Call start_generation again\n" \
                           f"  3. Or manually delete: workspace/generation-state-{scene_id}.json"

        # Create new state structure
        state = _initialize_state_structure(
            scene_id=scene_id,
            blueprint_path=params.blueprint_path,
            initiated_by=params.initiated_by,
            metadata=params.metadata
        )

        # Save to file
        _save_state_file(scene_id, state)

        # Build success report
        lines = [
            f"✅ GENERATION STARTED: Scene {scene_id}",
            "",
            f"**Session ID**: {state['session_id']}",
            f"**Blueprint**: {params.blueprint_path}",
            f"**Initiated by**: {params.initiated_by}",
            f"**Started**: {state['started_at']}",
            "",
            "📊 Initial Status:",
            f"  - Workflow: {state['workflow_status']}",
            f"  - Current Step: {state['current_step'] or 'Not started'}",
            f"  - Max Attempts: {state['generation_attempts']['max_attempts']}",
            "",
            f"💾 State file: workspace/generation-state-{scene_id}.json",
            "",
            "🚀 Next Steps:",
            "  1. Call start_step(scene_id='{}', step_name='scene:gen:setup:files')".format(scene_id),
            "  2. Perform step operations",
            "  3. Call complete_step(scene_id='{}', step_name='scene:gen:setup:files', duration_seconds=X)".format(scene_id),
            "  4. Continue with remaining steps"
        ]

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="start_step",
    annotations={
        "title": "Start Workflow Step",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def start_step(params: StartStepInput) -> str:
    """Mark a workflow step as IN_PROGRESS and record start timestamp.

    Args:
        params (StartStepInput): Validated input containing:
            - scene_id (str): Scene ID (4 digits)
            - step_name (str): Semantic step name (e.g., 'scene:gen:setup:files')
            - metadata (Optional[dict]): Optional metadata

    Returns:
        str: Markdown confirmation with current step status

    Error Handling:
        - Returns error if state file doesn't exist
        - Returns error if workflow in terminal state
        - Returns error if step order violated

    Idempotency:
        - If step already IN_PROGRESS: Updates started_at timestamp
        - If step already COMPLETED: Returns error
    """
    scene_id = params.scene_id
    step_name = params.step_name

    try:
        # Load state
        state = _load_state_file(scene_id)
        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}\n\n" \
                   f"💡 Initialize first: start_generation(scene_id='{scene_id}', blueprint_path='...')"

        # Check workflow status
        workflow_status = state.get('workflow_status')
        if workflow_status in [WorkflowStatus.COMPLETED.value, WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value]:
            return f"❌ ERROR: Cannot start step - workflow in terminal state: {workflow_status}\n\n" \
                   f"💡 For new generation: Archive current state and call start_generation"

        # Check step order (unless this is the first step)
        current_step = state.get('current_step')
        if current_step is None:
            # First step - must be first in STEP_ORDER
            if step_name != STEP_ORDER[0]:
                return f"❌ ERROR: First step must be {STEP_ORDER[0]}, got {step_name}"
        else:
            # Not first step - check order
            expected_index = _get_step_index(current_step)
            requested_index = _get_step_index(step_name)

            if requested_index != expected_index and requested_index != expected_index + 1:
                return f"❌ ERROR: Step order violation\n\n" \
                       f"**Current**: {current_step}\n" \
                       f"**Requested**: {step_name}\n\n" \
                       f"💡 Steps must be executed in order"

        # Check if step already completed
        if step_name in state['steps'] and state['steps'][step_name].get('status') == StepStatus.COMPLETED.value:
            return f"❌ ERROR: Step {step_name} already COMPLETED\n\n" \
                   f"💡 Cannot restart completed step"

        # Update step status
        now = datetime.now(timezone.utc).isoformat()
        _update_step_status(
            state,
            step_name,
            StepStatus.IN_PROGRESS.value,
            started_at=now,
            **(params.metadata or {})
        )

        # Update current step
        state['current_step'] = step_name

        # Save updated state
        _save_state_file(scene_id, state)

        # Build response
        step_index = _get_step_index(step_name)
        lines = [
            f"⏳ STEP STARTED: {step_name}",
            "",
            f"**Scene**: {scene_id}",
            f"**Session**: {state.get('session_id', 'unknown')}",
            f"**Started**: {now}",
            "",
            "📊 Workflow Status:",
            f"  - Progress: {step_index + 1}/{len(STEP_ORDER)}",
            f"  - Step: {step_name}",
            f"  - Status: IN_PROGRESS",
            "",
            "🔄 Next Action:",
            f"  - Perform step operations",
            f"  - Call complete_step(scene_id='{scene_id}', step_name='{step_name}', duration_seconds=X)"
        ]

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="complete_step",
    annotations={
        "title": "Complete Workflow Step",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def complete_step(params: CompleteStepInput) -> str:
    """Mark a workflow step as COMPLETED, record duration, and advance workflow.

    Args:
        params (CompleteStepInput): Validated input containing:
            - scene_id (str): Scene ID (4 digits)
            - step_name (str): Semantic step name
            - duration_seconds (float): Step execution time
            - artifacts (Optional[Dict]): Artifact paths produced
            - metadata (Optional[Dict]): Metadata (use {'workflow_complete': True} for final step)

    Returns:
        str: Markdown summary with completed step info

    Idempotency:
        - If step already COMPLETED: Returns info message
        - If step IN_PROGRESS: Marks as COMPLETED and advances workflow
    """
    scene_id = params.scene_id
    step_name = params.step_name

    try:
        # Load state
        state = _load_state_file(scene_id)
        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}"

        # Idempotency: Check if already completed
        if step_name in state['steps'] and state['steps'][step_name].get('status') == StepStatus.COMPLETED.value:
            existing_duration = state['steps'][step_name].get('duration_seconds', 0)
            return f"ℹ️ INFO: Step {step_name} already COMPLETED\n\n" \
                   f"**Existing duration**: {_format_duration(existing_duration)}\n\n" \
                   f"💡 Idempotent call - no changes made"

        # Check if step was started
        if step_name not in state['steps'] or state['steps'][step_name].get('status') != StepStatus.IN_PROGRESS.value:
            return f"❌ ERROR: Step {step_name} not IN_PROGRESS\n\n" \
                   f"💡 Call start_step first"

        # Update step status
        now = datetime.now(timezone.utc).isoformat()
        _update_step_status(
            state,
            step_name,
            StepStatus.COMPLETED.value,
            completed_at=now,
            duration_seconds=params.duration_seconds
        )

        # Update artifacts if provided
        if params.artifacts:
            if 'artifacts' not in state:
                state['artifacts'] = {}
            state['artifacts'].update(params.artifacts)

        # Update metadata if provided
        if params.metadata:
            state['steps'][step_name]['metadata'] = params.metadata

        # Check if this is final step with workflow_complete flag
        is_workflow_complete = params.metadata and params.metadata.get('workflow_complete') is True

        if is_workflow_complete:
            # Mark workflow as complete
            state['workflow_status'] = WorkflowStatus.COMPLETED.value
            state['completed_at'] = now
        else:
            # Advance to next step
            _advance_workflow(state, step_name)

        # Update total duration
        started_at = datetime.fromisoformat(state['started_at'].replace('Z', '+00:00'))
        total_duration = (datetime.now(timezone.utc) - started_at).total_seconds()
        state['metadata']['total_duration_seconds'] = total_duration

        # Save updated state
        _save_state_file(scene_id, state)

        # Build response
        step_index = _get_step_index(step_name)
        lines = [
            f"✅ STEP COMPLETED: {step_name}",
            "",
            f"**Scene**: {scene_id}",
            f"**Duration**: {_format_duration(params.duration_seconds)}",
            f"**Completed**: {now}",
            ""
        ]

        if params.artifacts:
            lines.append("📁 Artifacts produced:")
            for key, path in params.artifacts.items():
                lines.append(f"  - {key}: {path}")
            lines.append("")

        lines.append("📊 Workflow Progress:")
        lines.append(f"  - Steps completed: {step_index + 1}/{len(STEP_ORDER)}")
        lines.append(f"  - Total time: {_format_duration(total_duration)}")
        lines.append("")

        if is_workflow_complete:
            lines.append("🎉 WORKFLOW COMPLETE:")
            lines.append(f"  - Status: COMPLETED")
            lines.append(f"  - Final scene available in artifacts")
        elif step_index < len(STEP_ORDER) - 1:
            next_step_name = STEP_ORDER[step_index + 1]
            lines.append("🔄 Next Step:")
            lines.append(f"  - {next_step_name}")
            lines.append(f"  - Call start_step(scene_id='{scene_id}', step_name='{next_step_name}')")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="fail_step",
    annotations={
        "title": "Fail Step (Recoverable or Terminal)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def fail_step(params: FailStepInput) -> str:
    """Record step failure with errors.

    NOT necessarily terminal - coordinator can call retry_step() afterwards.
    Terminal failure = fail_step() with metadata={'terminal': True} WITHOUT subsequent retry_step().

    Args:
        params (FailStepInput): Validated input containing:
            - scene_id (str): Scene ID
            - step_name (str): Semantic step name
            - failure_reason (str): Detailed failure description
            - metadata (Optional[dict]): Metadata (e.g., {'attempt': 1, 'severity': 'MEDIUM', 'terminal': False})

    Returns:
        str: Markdown confirmation with error details

    Examples:
        - Use when: Generation attempt 1 failed (will retry)
        - Use when: Validation found blocking issues
        - Terminal when: metadata={'terminal': True} (max retries exhausted, unrecoverable error)
    """
    scene_id = params.scene_id
    step_name = params.step_name

    try:
        # Load state
        state = _load_state_file(scene_id)
        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}"

        # Create error entry
        now = datetime.now(timezone.utc).isoformat()
        error_entry = {
            "step": step_name,
            "timestamp": now,
            "message": params.failure_reason,
            **(params.metadata or {})
        }

        # Append to errors array
        if 'errors' not in state:
            state['errors'] = []
        state['errors'].append(error_entry)

        # Check if terminal failure
        is_terminal = params.metadata and params.metadata.get('terminal') is True

        if is_terminal:
            # Mark workflow as FAILED
            state['workflow_status'] = WorkflowStatus.FAILED.value
            state['failed_at_step'] = step_name
            state['failure_reason'] = params.failure_reason

        # Mark step as FAILED
        _update_step_status(
            state,
            step_name,
            StepStatus.FAILED.value,
            failed_at=now,
            failure_reason=params.failure_reason,
            **(params.metadata or {})
        )

        # Update timestamp
        state['updated_at'] = now

        # Save updated state
        _save_state_file(scene_id, state)

        # Build response
        total_errors = len(state['errors'])
        severity = params.metadata.get('severity', 'UNKNOWN') if params.metadata else 'UNKNOWN'
        severity_icon = {
            "LOW": "ℹ️",
            "MEDIUM": "⚠️",
            "HIGH": "⚠️",
            "CRITICAL": "🚨"
        }.get(severity, "⚠️")

        lines = [
            f"{severity_icon} STEP FAILED: {step_name}",
            "",
            f"**Scene**: {scene_id}",
            f"**Severity**: {severity}",
            f"**Terminal**: {'YES' if is_terminal else 'NO (can retry)'}",
            "",
            f"**Failure Reason**:",
            f"{params.failure_reason}",
            "",
            f"📊 Error Count: {total_errors} total",
            ""
        ]

        if is_terminal:
            lines.append("💡 Workflow Status: FAILED (terminal)")
            lines.append("")
            lines.append("🔧 Recovery Options:")
            lines.append(f"  1. Fix issues (blueprint, constraints, etc.)")
            lines.append(f"  2. Use get_status(scene_id='{scene_id}') to review state")
            lines.append(f"  3. Start fresh with new generation")
        else:
            lines.append("💡 Workflow Status: IN_PROGRESS (can retry)")
            lines.append("")
            lines.append("🔄 Next Action:")
            lines.append(f"  - Call retry_step(scene_id='{scene_id}', step_name='{step_name}')")
            lines.append(f"  - Or fail terminally with metadata={{'terminal': True}}")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="retry_step",
    annotations={
        "title": "Retry Failed Step",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def retry_step(params: RetryStepInput) -> str:
    """Indicate coordinator is retrying a failed step.

    Only called after fail_step(). Clears FAILED status and allows new attempt.

    Args:
        params (RetryStepInput): Validated input containing:
            - scene_id (str): Scene ID
            - step_name (str): Semantic step name to retry
            - metadata (Optional[dict]): Metadata (e.g., {'attempt_number': 2})

    Returns:
        str: Markdown confirmation ready for retry
    """
    scene_id = params.scene_id
    step_name = params.step_name

    try:
        # Load state
        state = _load_state_file(scene_id)
        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}"

        # Check if step exists and is FAILED
        if step_name not in state['steps']:
            return f"❌ ERROR: Step {step_name} not found in state"

        step_status = state['steps'][step_name].get('status')
        if step_status != StepStatus.FAILED.value:
            return f"❌ ERROR: Step {step_name} not FAILED (status: {step_status})\n\n" \
                   f"💡 retry_step only works on FAILED steps"

        # Reset step status to PENDING (will be set to IN_PROGRESS by next start_step)
        state['steps'][step_name]['status'] = StepStatus.PENDING.value
        state['steps'][step_name]['retry_metadata'] = params.metadata or {}

        # Update timestamp
        state['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Save updated state
        _save_state_file(scene_id, state)

        # Build response
        attempt_number = params.metadata.get('attempt_number', 'unknown') if params.metadata else 'unknown'
        lines = [
            f"🔄 RETRY STEP: {step_name}",
            "",
            f"**Scene**: {scene_id}",
            f"**Attempt**: {attempt_number}",
            "",
            "💡 Step Status:",
            f"  - Previous: FAILED",
            f"  - Current: PENDING (ready for retry)",
            "",
            "🔄 Next Action:",
            f"  - Call start_step(scene_id='{scene_id}', step_name='{step_name}')",
            f"  - Then execute step operations",
            f"  - Call complete_step() on success or fail_step() on failure"
        ]

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="complete_generation",
    annotations={
        "title": "Complete Generation Workflow (Terminal)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def complete_generation(params: CompleteGenerationInput) -> str:
    """Mark workflow as COMPLETED (terminal state) after successful generation.

    This tool finalizes the workflow by setting status=COMPLETED and recording
    all final metrics (word count, duration, retry count). This is the last
    step in a successful generation workflow.

    Args:
        params (CompleteGenerationInput): Validated input parameters containing:
            - scene_id (str): Scene ID
            - final_scene_path (str): Path to generated scene file
            - validation_report_path (str): Path to validation report
            - word_count (int): Final word count
            - total_duration_seconds (float): Total workflow duration
            - retry_count (int): Number of retries (default: 0)

    Returns:
        str: Markdown success report with final metrics

    Error Handling:
        - Returns error if state file doesn't exist
        - Returns info message if already COMPLETED (idempotent)

    Examples:
        - Use when: All 7 steps completed successfully
        - Use when: Validation passed and scene file saved
        - Don't use when: Workflow incomplete or failed

    Idempotency:
        - If already COMPLETED: Returns success message with existing metrics
        - If not COMPLETED: Sets status=COMPLETED, records final metrics

    Terminal State:
        - After calling this, workflow is finished
        - State file becomes historical record
        - Can be used for analytics and performance tracking

    Success Metrics Schema:
        {
            "final_scene_path": str,
            "validation_report_path": str,
            "word_count": int,
            "total_duration_seconds": float,
            "retry_count": int
        }
    """
    scene_id = params.scene_id

    try:
        # Load state
        state = _load_state_file(scene_id)
        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}"

        # Idempotency: Check if already completed
        if state.get('workflow_status') == WorkflowStatus.COMPLETED.value:
            existing_metrics = state.get('completion_metrics', {})
            return f"ℹ️ INFO: Generation already COMPLETED for scene {scene_id}\n\n" \
                   f"**Completed**: {state.get('updated_at', 'unknown')}\n" \
                   f"**Word count**: {existing_metrics.get('word_count', 'unknown')}\n" \
                   f"**Duration**: {_format_duration(existing_metrics.get('total_duration_seconds', 0))}\n\n" \
                   f"💡 Idempotent call - workflow already successful"

        # Update workflow status
        state['workflow_status'] = WorkflowStatus.COMPLETED.value
        state['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Record final metrics
        state['completion_metrics'] = {
            "final_scene_path": params.final_scene_path,
            "validation_report_path": params.validation_report_path,
            "word_count": params.word_count,
            "total_duration_seconds": params.total_duration_seconds,
            "retry_count": params.retry_count
        }

        # Update artifacts
        if 'artifacts' not in state:
            state['artifacts'] = {}
        state['artifacts']['final_scene_path'] = params.final_scene_path
        state['artifacts']['validation_report_path'] = params.validation_report_path

        # Update metadata
        state['metadata']['total_duration_seconds'] = params.total_duration_seconds
        state['metadata']['final_word_count'] = params.word_count
        state['metadata']['generation_retries'] = params.retry_count

        # Save updated state
        _save_state_file(scene_id, state)

        # Build success report
        lines = [
            f"✅ GENERATION COMPLETED: Scene {scene_id}",
            "",
            f"**Session**: {state.get('session_id', 'unknown')}",
            f"**Started**: {state.get('started_at', 'unknown')}",
            f"**Completed**: {state['updated_at']}",
            "",
            "📊 Final Metrics:",
            f"  - Word count: {params.word_count:,} words",
            f"  - Total duration: {_format_duration(params.total_duration_seconds)}",
            f"  - Generation retries: {params.retry_count}/3",
            f"  - All steps: 7/7 completed",
            "",
            "📁 Final Artifacts:",
            f"  - Scene file: {params.final_scene_path}",
            f"  - Validation report: {params.validation_report_path}",
            "",
            f"💾 State archived: workspace/generation-state-{scene_id}.json",
            "",
            "🎉 Success Indicators:",
            "  ✓ All constraint validations passed",
            "  ✓ Blueprint compliance verified",
            "  ✓ Literary quality approved",
            "  ✓ Scene ready for publication"
        ]

        # Add performance note if fast
        if params.total_duration_seconds < 300:  # < 5 minutes
            lines.append("")
            lines.append(f"⚡ Performance: Excellent ({_format_duration(params.total_duration_seconds)})")

        # Add retry note if needed retries
        if params.retry_count > 0:
            lines.append("")
            lines.append(f"🔄 Note: Success achieved after {params.retry_count} retry(ies)")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="log_question_answer",
    annotations={
        "title": "Log QuestionTool Interaction (BONUS)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def log_question_answer(params: LogQuestionAnswerInput) -> str:
    """Log QuestionTool interaction to state for audit trail and decision tracking.

    BONUS FEATURE: This tool records questions asked to users via QuestionTool
    and their answers. Useful for tracking user decisions and ensuring they're
    not forgotten in subsequent workflow steps.

    Args:
        params (LogQuestionAnswerInput): Validated input parameters containing:
            - scene_id (str): Scene ID
            - question (str): Question asked to user
            - answer (str): User's answer
            - timestamp (Optional[str]): Timestamp (auto-generated if not provided)

    Returns:
        str: Markdown confirmation with question/answer summary

    Error Handling:
        - Returns error if state file doesn't exist
        - Always succeeds if state exists

    Examples:
        - Use when: Asked user to approve verification plan (Step 3)
        - Use when: Requested user to choose retry strategy
        - Use when: Any QuestionTool interaction during workflow
        - Don't use when: No user interaction occurred

    Idempotency:
        - NOT idempotent - each call adds new Q&A entry
        - Allows tracking multiple questions per workflow

    Use Cases:
        - Audit trail: What decisions were made during generation?
        - Context preservation: What did user approve/reject?
        - Analytics: Which questions are most common?
        - Debugging: What user choices led to failure/success?
    """
    scene_id = params.scene_id

    try:
        # Load state
        state = _load_state_file(scene_id)
        if state is None:
            return f"❌ ERROR: No state found for scene {scene_id}"

        # Create Q&A entry
        timestamp = params.timestamp or datetime.now(timezone.utc).isoformat()
        qa_entry = {
            "question": params.question,
            "answer": params.answer,
            "timestamp": timestamp
        }

        # Append to user_questions array
        if 'user_questions' not in state:
            state['user_questions'] = []
        state['user_questions'].append(qa_entry)

        # Update timestamp
        state['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Save updated state
        _save_state_file(scene_id, state)

        # Build response
        total_questions = len(state['user_questions'])

        lines = [
            f"💬 QUESTION/ANSWER LOGGED",
            "",
            f"**Scene**: {scene_id}",
            f"**Timestamp**: {timestamp}",
            "",
            f"**Question**:",
            f"{params.question[:200]}{'...' if len(params.question) > 200 else ''}",
            "",
            f"**Answer**:",
            f"{params.answer[:200]}{'...' if len(params.answer) > 200 else ''}",
            "",
            f"📊 Total Q&A entries: {total_questions}",
            "",
            "💡 Use Cases:",
            "  - Audit trail for user decisions",
            "  - Context for future workflow steps",
            "  - Analytics on user interaction patterns",
            "",
            f"💾 Logged to: workspace/generation-state-{scene_id}.json → user_questions array"
        ]

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


# Main entry point
if __name__ == "__main__":
    # Run server with stdio transport (default for Claude Code)
    mcp.run()
