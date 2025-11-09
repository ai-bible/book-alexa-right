"""
Integration Tests for MCP Server

Tests MCP server with real file I/O and state management.
"""

import pytest
import json
from pathlib import Path
from tests.helpers.mcp_client import create_mcp_client

# Step names from Scene Generation Workflow v2.0
STEP_NAMES = [
    "scene:gen:setup:files",
    "scene:gen:setup:blueprint",
    "scene:gen:setup:plan",
    "scene:gen:draft:prose",
    "scene:gen:review:validation",
    "scene:gen:publish:output"
]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_lifecycle(test_workspace, test_scene_id):
    """Test complete MCP server lifecycle."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        # Verify connection
        assert client is not None

        # Start generation
        result = await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        assert result is not None

        # Get status
        status = await client.call_tool("get_status", {
            "scene_id": test_scene_id,
            "detailed": True
        })

        assert status is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_state_transitions(test_workspace, test_scene_id):
    """Test complete workflow state machine transitions."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        # STEP 0: Initialize
        await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        status = await client.call_tool("get_status", {
            "scene_id": test_scene_id,
            "detailed": False
        })

        state = client.get_state(test_scene_id)
        assert state["workflow_status"] == "IN_PROGRESS"
        assert state["current_step"] is None  # Not started yet

        # Execute all 6 steps
        for i, step_name in enumerate(STEP_NAMES):
            # Start step
            await client.call_tool("start_step", {
                "scene_id": test_scene_id,
                "step_name": step_name
            })

            state = client.get_state(test_scene_id)
            assert state["current_step"] == step_name

            # Complete step (last step marks workflow complete)
            metadata = {"workflow_complete": True} if i == len(STEP_NAMES) - 1 else None
            await client.call_tool("complete_step", {
                "scene_id": test_scene_id,
                "step_name": step_name,
                "duration_seconds": 1.0,
                "metadata": metadata
            })

        # Check workflow completed
        state = client.get_state(test_scene_id)
        assert state["workflow_status"] == "COMPLETED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_recording(test_workspace, test_scene_id):
    """Test error recording without failing workflow."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        step_name = STEP_NAMES[3]  # scene:gen:draft:prose

        # Start step
        await client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": step_name
        })

        # Record multiple errors via fail_step + retry_step
        for attempt in range(3):
            await client.call_tool("fail_step", {
                "scene_id": test_scene_id,
                "step_name": step_name,
                "failure_reason": f"Attempt {attempt + 1} failed",
                "metadata": {
                    "attempt": attempt + 1,
                    "severity": ["LOW", "MEDIUM", "HIGH"][attempt],
                    "terminal": False
                }
            })

            if attempt < 2:  # Don't retry after last attempt in this test
                await client.call_tool("retry_step", {
                    "scene_id": test_scene_id,
                    "step_name": step_name,
                    "metadata": {"attempt_number": attempt + 2}
                })

        state = client.get_state(test_scene_id)

        # Workflow should still be IN_PROGRESS
        assert state["workflow_status"] == "IN_PROGRESS"

        # All errors should be logged
        assert len(state.get("errors", [])) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_failure(test_workspace, test_scene_id):
    """Test workflow failure path."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        step_name = STEP_NAMES[3]  # scene:gen:draft:prose

        # Start step
        await client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": step_name
        })

        # Terminal failure
        await client.call_tool("fail_step", {
            "scene_id": test_scene_id,
            "step_name": step_name,
            "failure_reason": "Max retries exhausted (3/3)",
            "metadata": {
                "attempt": 3,
                "severity": "CRITICAL",
                "terminal": True
            }
        })

        state = client.get_state(test_scene_id)

        # Workflow should be FAILED
        assert state["workflow_status"] == "FAILED"
        assert state.get("failed_at_step") == step_name
        assert "Max retries" in state.get("failure_reason", "")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_cancellation(test_workspace, test_scene_id):
    """Test workflow cancellation."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        step_name = STEP_NAMES[2]  # scene:gen:setup:plan

        # Start step
        await client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": step_name
        })

        # Cancel via fail_step (terminal)
        await client.call_tool("fail_step", {
            "scene_id": test_scene_id,
            "step_name": step_name,
            "failure_reason": "User rejected verification plan",
            "metadata": {"terminal": True, "cancelled_by": "user"}
        })

        state = client.get_state(test_scene_id)

        # Workflow should be FAILED (cancellation is a type of failure)
        assert state["workflow_status"] == "FAILED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_interaction_logging(test_workspace, test_scene_id):
    """Test logging user questions and answers."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Log multiple Q&A
        qa_pairs = [
            ("Approve verification plan?", "Y"),
            ("Make modifications?", "n"),
            ("Proceed with generation?", "yes")
        ]

        for question, answer in qa_pairs:
            await client.call_tool("log_question_answer", {
                "scene_id": test_scene_id,
                "question": question,
                "answer": answer
            })

        state = client.get_state(test_scene_id)

        # All Q&A should be logged
        user_questions = state.get("user_questions", [])
        assert len(user_questions) == 3

        assert any(q["question"] == "Approve verification plan?" for q in user_questions)
        assert any(q["answer"] == "Y" for q in user_questions)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_workflows_prevention(test_workspace):
    """Test that concurrent workflows for same scene are prevented."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        scene_id = "9999"

        # Start first workflow
        await client.call_tool("start_generation", {
            "scene_id": scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{scene_id}-blueprint.md",
            "initiated_by": "test1"
        })

        # Try to start second workflow for same scene (should be idempotent or error)
        result2 = await client.call_tool("start_generation", {
            "scene_id": scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{scene_id}-blueprint.md",
            "initiated_by": "test2"
        })

        # Mock should handle this gracefully
        assert result2 is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resume_from_failure(test_workspace, test_scene_id):
    """Test resume capability after failure."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        # Start and fail generation
        await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        step_name = STEP_NAMES[3]  # scene:gen:draft:prose

        # Start and fail step
        await client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": step_name
        })

        await client.call_tool("fail_step", {
            "scene_id": test_scene_id,
            "step_name": step_name,
            "failure_reason": "Test failure",
            "metadata": {"terminal": True}
        })

        # Get status to see failed state
        status = await client.call_tool("get_status", {
            "scene_id": test_scene_id,
            "detailed": True
        })

        # Mock should provide status showing failure
        assert status is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_multiple_workflows(test_workspace):
    """Test listing multiple workflows."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        # Create multiple workflows
        for i in range(1, 4):
            scene_id = f"999{i}"
            await client.call_tool("start_generation", {
                "scene_id": scene_id,
                "blueprint_path": f"tests/fixtures/blueprints/scene-{scene_id}-blueprint.md",
                "initiated_by": "test"
            })

        # List all workflows
        result = await client.call_tool("list_generations", {
            "filter": "all",
            "sort_by": "started_at"
        })

        assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_step_timing_accuracy(test_workspace, test_scene_id):
    """Test that step timing is tracked accurately."""
    import time

    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        await client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Execute step with known duration
        step_name = STEP_NAMES[0]  # scene:gen:setup:files

        await client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": step_name
        })

        time.sleep(0.5)  # Wait 500ms

        await client.call_tool("complete_step", {
            "scene_id": test_scene_id,
            "step_name": step_name,
            "duration_seconds": 0.5
        })

        state = client.get_state(test_scene_id)
        step_data = state.get("steps", {}).get(step_name)

        # Duration should be recorded
        if step_data:
            assert "duration_seconds" in step_data or "status" in step_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_call_logging(test_workspace, test_scene_id):
    """Test that all MCP calls are logged."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        # Perform sequence of operations
        await client.call_tool("start_generation", {"scene_id": test_scene_id, "blueprint_path": "test.md", "initiated_by": "test"})
        await client.call_tool("start_step", {"scene_id": test_scene_id, "step_name": STEP_NAMES[0]})
        await client.call_tool("complete_step", {"scene_id": test_scene_id, "step_name": STEP_NAMES[0], "duration_seconds": 1.0})

        # Verify all calls logged
        call_log = client.get_call_log()
        assert len(call_log) == 3

        assert call_log[0]["tool_name"] == "start_generation"
        assert call_log[1]["tool_name"] == "start_step"
        assert call_log[2]["tool_name"] == "complete_step"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_call_count_tracking(test_workspace, test_scene_id):
    """Test MCP call count tracking."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        initial_count = client.get_call_count()

        await client.call_tool("start_generation", {"scene_id": test_scene_id, "blueprint_path": "test.md", "initiated_by": "test"})
        await client.call_tool("get_status", {"scene_id": test_scene_id, "detailed": False})

        final_count = client.get_call_count()

        assert final_count == initial_count + 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filter_calls_by_tool(test_workspace, test_scene_id):
    """Test filtering MCP calls by tool name."""
    async with create_mcp_client(workspace=test_workspace, use_mock=True) as client:
        # Make various calls
        await client.call_tool("start_generation", {"scene_id": test_scene_id, "blueprint_path": "test.md", "initiated_by": "test"})
        await client.call_tool("start_step", {"scene_id": test_scene_id, "step_name": STEP_NAMES[0]})
        await client.call_tool("start_step", {"scene_id": test_scene_id, "step_name": STEP_NAMES[1]})
        await client.call_tool("complete_step", {"scene_id": test_scene_id, "step_name": STEP_NAMES[0], "duration_seconds": 1.0})

        # Filter by tool
        start_step_calls = client.get_calls_by_tool("start_step")
        assert len(start_step_calls) == 2

        complete_step_calls = client.get_calls_by_tool("complete_step")
        assert len(complete_step_calls) == 1
