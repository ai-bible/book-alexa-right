"""
Workflow Orchestration Models

Pydantic models and Enums for workflow orchestration MCP server.

This module contains:
- WorkflowType, WorkflowStatus, StepStatus enums
- Workflow definitions (GENERATION_STEPS, PLANNING_PHASES)
- Input validation models for all MCP tools
"""

from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


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
