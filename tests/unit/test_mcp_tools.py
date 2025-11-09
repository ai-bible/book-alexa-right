"""
Unit Tests for MCP Tools

Tests individual MCP tools from generation_state_mcp.py using FastMCP's call_tool method.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

# Step names from Scene Generation Workflow v2.0
STEP_NAMES = [
    "scene:gen:setup:files",
    "scene:gen:setup:blueprint",
    "scene:gen:setup:plan",
    "scene:gen:draft:prose",
    "scene:gen:review:validation",
    "scene:gen:publish:output"
]

# Import MCP server instance
# Note: This will work when mcp-servers is properly installed
try:
    from mcp_servers.generation_state_mcp import mcp
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    mcp = None


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_start_generation(test_workspace, test_scene_id, test_blueprint_path):
    """Test start_generation creates valid state file."""
    result = await mcp.call_tool("start_generation", {
        "scene_id": test_scene_id,
        "blueprint_path": test_blueprint_path,
        "initiated_by": "test"
    })

    # Verify result format
    assert result is not None
    assert len(result) > 0
    assert hasattr(result[0], 'text')

    # Verify response content
    response_text = result[0].text.lower()
    assert "workflow initialized" in response_text or "success" in response_text

    # Verify state file created
    state_path = test_workspace / f"generation-state-{test_scene_id}.json"
    assert state_path.exists()

    # Verify state file content
    state = json.loads(state_path.read_text())
    assert state["scene_id"] == test_scene_id
    assert state["workflow_status"] == "IN_PROGRESS"
    assert state["current_step"] == 1
    assert "started_at" in state


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_start_generation_idempotency(test_workspace, test_scene_id, test_blueprint_path):
    """Test start_generation is idempotent (calling twice doesn't create conflict)."""
    # First call
    result1 = await mcp.call_tool("start_generation", {
        "scene_id": test_scene_id,
        "blueprint_path": test_blueprint_path,
        "initiated_by": "test"
    })

    # Second call
    result2 = await mcp.call_tool("start_generation", {
        "scene_id": test_scene_id,
        "blueprint_path": test_blueprint_path,
        "initiated_by": "test"
    })

    # Both should succeed (idempotent)
    assert result1 is not None
    assert result2 is not None


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_get_generation_status_not_found(test_scene_id):
    """Test get_generation_status for non-existent workflow."""
    result = await mcp.call_tool("get_generation_status", {
        "scene_id": test_scene_id,
        "detailed": False
    })

    assert result is not None
    response_text = result[0].text.lower()
    assert "not found" in response_text or "not_found" in response_text


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_get_generation_status_found(mock_state_file, test_scene_id):
    """Test get_generation_status for existing workflow."""
    result = await mcp.call_tool("get_generation_status", {
        "scene_id": test_scene_id,
        "detailed": True
    })

    assert result is not None
    response_text = result[0].text

    # Parse response (should be JSON or markdown)
    if response_text.startswith('{'):
        state = json.loads(response_text)
        assert state["scene_id"] == test_scene_id
    else:
        # Markdown format
        assert test_scene_id in response_text
        assert "IN_PROGRESS" in response_text or "in progress" in response_text.lower()


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_start_step(mock_state_file, test_scene_id):
    """Test start_step marks step as IN_PROGRESS."""
    step_name = STEP_NAMES[1]  # scene:gen:setup:blueprint

    result = await mcp.call_tool("start_step", {
        "scene_id": test_scene_id,
        "step_name": step_name
    })

    assert result is not None

    # Verify state file updated
    state_path = mock_state_file
    state = json.loads(state_path.read_text())

    assert state["current_step"] == step_name
    assert step_name in state["steps"]
    assert state["steps"][step_name]["status"] == "IN_PROGRESS"


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_complete_step(mock_state_file, test_scene_id):
    """Test complete_step marks step as COMPLETED."""
    step_name = STEP_NAMES[0]  # scene:gen:setup:files

    # Start step first
    await mcp.call_tool("start_step", {
        "scene_id": test_scene_id,
        "step_name": step_name
    })

    # Complete step
    result = await mcp.call_tool("complete_step", {
        "scene_id": test_scene_id,
        "step_name": step_name,
        "duration_seconds": 5.2,
        "artifacts": {
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-blueprint.md"
        }
    })

    assert result is not None

    # Verify state
    state = json.loads(mock_state_file.read_text())
    step_data = state["steps"][step_name]

    assert step_data["status"] == "COMPLETED"
    assert step_data["duration_seconds"] == 5.2
    assert "artifacts" in step_data


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_fail_step_non_terminal(mock_state_file, test_scene_id):
    """Test fail_step logs error without failing workflow (non-terminal)."""
    step_name = STEP_NAMES[3]  # scene:gen:draft:prose

    result = await mcp.call_tool("fail_step", {
        "scene_id": test_scene_id,
        "step_name": step_name,
        "failure_reason": "Location constraint violated",
        "metadata": {
            "attempt": 1,
            "severity": "MEDIUM",
            "terminal": False
        }
    })

    assert result is not None

    # Verify error logged
    state = json.loads(mock_state_file.read_text())

    assert len(state["errors"]) > 0
    error = state["errors"][0]

    assert error["step_name"] == step_name
    assert error["severity"] == "MEDIUM"

    # Workflow should still be IN_PROGRESS
    assert state["workflow_status"] == "IN_PROGRESS"


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_fail_step_terminal(mock_state_file, test_scene_id):
    """Test fail_step sets workflow to FAILED (terminal)."""
    step_name = STEP_NAMES[3]  # scene:gen:draft:prose

    result = await mcp.call_tool("fail_step", {
        "scene_id": test_scene_id,
        "step_name": step_name,
        "failure_reason": "Max retries exhausted (3/3)",
        "metadata": {
            "attempt": 3,
            "severity": "CRITICAL",
            "terminal": True
        }
    })

    assert result is not None

    # Verify workflow failed
    state = json.loads(mock_state_file.read_text())

    assert state["workflow_status"] == "FAILED"
    assert state["failed_at_step"] == step_name
    assert "Max retries" in state["failure_reason"]


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_complete_workflow(mock_state_file, test_scene_id):
    """Test complete_step with workflow_complete=True sets workflow to COMPLETED."""
    step_name = STEP_NAMES[5]  # scene:gen:publish:output

    result = await mcp.call_tool("complete_step", {
        "scene_id": test_scene_id,
        "step_name": step_name,
        "duration_seconds": 10.5,
        "artifacts": {
            "final_scene_path": f"acts/.../content/scene-{test_scene_id}.md",
            "validation_report_path": "workspace/artifacts/validation-report.json"
        },
        "metadata": {
            "workflow_complete": True,
            "word_count": 487,
            "total_duration_seconds": 324.5,
            "retry_count": 0
        }
    })

    assert result is not None

    # Verify workflow completed
    state = json.loads(mock_state_file.read_text())

    assert state["workflow_status"] == "COMPLETED"
    assert "completion_metrics" in state
    assert state["completion_metrics"]["word_count"] == 487
    assert state["completion_metrics"]["total_duration_seconds"] == 324.5


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_log_question_answer(mock_state_file, test_scene_id):
    """Test log_question_answer records user interaction."""
    result = await mcp.call_tool("log_question_answer", {
        "scene_id": test_scene_id,
        "question": "Approve verification plan?",
        "answer": "Y"
    })

    assert result is not None

    # Verify question logged
    state = json.loads(mock_state_file.read_text())

    assert len(state["user_questions"]) > 0
    qa = state["user_questions"][0]

    assert qa["question"] == "Approve verification plan?"
    assert qa["answer"] == "Y"
    assert "timestamp" in qa


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_cancel_workflow(mock_state_file, test_scene_id):
    """Test cancellation via fail_step with cancelled_by metadata."""
    step_name = STEP_NAMES[2]  # scene:gen:setup:plan

    result = await mcp.call_tool("fail_step", {
        "scene_id": test_scene_id,
        "step_name": step_name,
        "failure_reason": "User rejected verification plan",
        "metadata": {
            "terminal": True,
            "cancelled_by": "user"
        }
    })

    assert result is not None

    # Verify workflow failed (cancellation is a type of failure)
    state = json.loads(mock_state_file.read_text())

    assert state["workflow_status"] == "FAILED"
    assert "User rejected" in state.get("failure_reason", "")


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_get_status_for_resume(mock_state_file, test_scene_id):
    """Test get_status provides information for resume (replaces resume_generation)."""
    step_name = STEP_NAMES[3]  # scene:gen:draft:prose

    # First fail the generation
    await mcp.call_tool("fail_step", {
        "scene_id": test_scene_id,
        "step_name": step_name,
        "failure_reason": "Test failure",
        "metadata": {"terminal": True}
    })

    # Get status to check what needs to be resumed
    result = await mcp.call_tool("get_status", {
        "scene_id": test_scene_id,
        "detailed": True
    })

    assert result is not None
    response_text = result[0].text.lower()

    # Should contain failure information
    assert "failed" in response_text
    assert "step" in response_text


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_list_generations_empty(test_workspace):
    """Test list_generations with no workflows."""
    result = await mcp.call_tool("list_generations", {
        "filter": "all",
        "sort_by": "started_at"
    })

    assert result is not None
    # Should return empty list or message


@pytest.mark.unit
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server not available")
@pytest.mark.asyncio
async def test_list_generations_with_workflows(mock_state_file, test_scene_id):
    """Test list_generations with existing workflows."""
    result = await mcp.call_tool("list_generations", {
        "filter": "active",
        "sort_by": "started_at"
    })

    assert result is not None
    response_text = result[0].text

    # Should contain test scene ID
    assert test_scene_id in response_text
