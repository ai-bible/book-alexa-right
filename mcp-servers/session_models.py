"""
Session Management Models

Pydantic models and Enums for session management MCP server.

This module contains:
- SessionStatus, ChangeType enums
- Input validation models for all MCP tools
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


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


# Pydantic Input Models

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
