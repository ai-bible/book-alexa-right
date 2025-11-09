"""
E2E Tests - Retry and Failure Scenarios

Tests workflows with retries, failures, and error handling.
"""

import pytest
from tests.helpers.sdk_client import create_test_sdk_client
from tests.helpers.mcp_client import create_mcp_client
from tests.helpers.workflow_runner import SimpleWorkflowRunner
from tests.helpers.mock_tools import create_mock_tool_list

# Step names from Scene Generation Workflow v2.0
STEP_NAMES = [
    "scene:gen:setup:files",
    "scene:gen:setup:blueprint",
    "scene:gen:setup:plan",
    "scene:gen:draft:prose",
    "scene:gen:review:validation",
    "scene:gen:publish:output"
]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_retry_on_second_attempt(test_workspace, test_scene_id):
    """Test workflow with one failed attempt, success on retry."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    runner = SimpleWorkflowRunner(mcp_client)

    # Execute with 1 retry
    result = await runner.run_retry_path(test_scene_id, retry_count=1)

    # Assertions
    assert result.scene_id == test_scene_id
    assert result.status == "COMPLETED"
    assert result.retry_count == 1

    # Verify error was logged
    state = mcp_client.get_state(test_scene_id)
    errors = state.get("errors", [])
    assert len(errors) == 1
    assert errors[0]["retry_count"] == 1


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_retries_then_success(test_workspace, test_scene_id):
    """Test workflow with multiple retries before success."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    runner = SimpleWorkflowRunner(mcp_client)

    # Execute with 2 retries
    result = await runner.run_retry_path(test_scene_id, retry_count=2)

    # Assertions
    assert result.status == "COMPLETED"
    assert result.retry_count == 2

    # Verify all errors logged
    state = mcp_client.get_state(test_scene_id)
    errors = state.get("errors", [])
    assert len(errors) == 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_severity_progression(test_workspace, test_scene_id):
    """Test error severity increases with retry count."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    async with mcp_client:
        await mcp_client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Record errors with increasing severity
        severities = ["LOW", "MEDIUM", "HIGH"]
        step_name = STEP_NAMES[3]  # scene:gen:draft:prose

        for i, severity in enumerate(severities):
            await mcp_client.call_tool("record_error", {
                "scene_id": test_scene_id,
                "step_name": step_name,
                "error_type": "constraint_violation",
                "error_message": f"Attempt {i + 1} failed",
                "severity": severity,
                "retry_count": i + 1
            })

        state = mcp_client.get_state(test_scene_id)
        errors = state.get("errors", [])

        # Verify severity progression
        assert errors[0]["severity"] == "LOW"
        assert errors[1]["severity"] == "MEDIUM"
        assert errors[2]["severity"] == "HIGH"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_max_retries_exhausted(test_workspace, test_scene_id):
    """Test workflow fails after max retries (3)."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    async with mcp_client:
        await mcp_client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Simulate 3 failed attempts
        step_name = STEP_NAMES[3]  # scene:gen:draft:prose

        for attempt in range(3):
            await mcp_client.call_tool("record_error", {
                "scene_id": test_scene_id,
                "step_name": step_name,
                "error_type": "constraint_violation",
                "error_message": f"Attempt {attempt + 1} failed",
                "severity": ["LOW", "MEDIUM", "HIGH"][attempt],
                "retry_count": attempt + 1
            })

        # Final failure
        await mcp_client.call_tool("fail_generation", {
            "scene_id": test_scene_id,
            "step_name": step_name,
            "failure_reason": "Max retries exhausted (3/3). Persistent violations: [location, character]",
            "final_errors": [
                {
                    "step_name": step_name,
                    "error_type": "constraint_violation",
                    "message": "Persistent violations after 3 attempts",
                    "severity": "CRITICAL"
                }
            ]
        })

        state = mcp_client.get_state(test_scene_id)

        # Verify failure
        assert state["workflow_status"] == "FAILED"
        assert state["failed_at_step"] == 4
        assert "3/3" in state["failure_reason"]
        assert len(state["errors"]) == 3


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_blueprint_validation_failure(test_workspace, test_scene_id):
    """Test workflow fails at Step 2 (blueprint invalid)."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    async with mcp_client:
        await mcp_client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Complete Step 1
        await mcp_client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[0]
        })

        await mcp_client.call_tool("complete_step", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[0],
            "duration_seconds": 0.5
        })

        # Fail at Step 2
        await mcp_client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[1]
        })

        await mcp_client.call_tool("fail_generation", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[1],
            "failure_reason": "Blueprint validation failed: Missing constraints section",
            "final_errors": [
                {
                    "step_name": STEP_NAMES[1],
                    "error_type": "blueprint_invalid",
                    "message": "Missing constraints section",
                    "severity": "CRITICAL"
                }
            ]
        })

        state = mcp_client.get_state(test_scene_id)

        # Verify early failure
        assert state["workflow_status"] == "FAILED"
        assert state["failed_at_step"] == 2
        assert state["current_step"] == 2  # Didn't progress beyond Step 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_user_rejects_plan(test_workspace, test_scene_id):
    """Test workflow cancels when user rejects verification plan."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    async with mcp_client:
        await mcp_client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Complete Steps 1-2
        for i in range(2):
            await mcp_client.call_tool("start_step", {
                "scene_id": test_scene_id,
                "step_name": STEP_NAMES[i]
            })

            await mcp_client.call_tool("complete_step", {
                "scene_id": test_scene_id,
                "step_name": STEP_NAMES[i],
                "duration_seconds": 1.0
            })

        # User rejects at Step 3
        await mcp_client.call_tool("log_question_answer", {
            "scene_id": test_scene_id,
            "question": "Approve verification plan?",
            "answer": "n"
        })

        await mcp_client.call_tool("cancel_generation", {
            "scene_id": test_scene_id,
            "reason": "User rejected verification plan",
            "cancelled_by": "user"
        })

        state = mcp_client.get_state(test_scene_id)

        # Verify cancellation
        assert state["workflow_status"] == "CANCELLED"
        assert "user rejected" in state.get("cancellation_reason", "").lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_blocks_publication(test_workspace, test_scene_id):
    """Test workflow fails at Step 5 (validation blocks)."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    async with mcp_client:
        await mcp_client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Complete Steps 1-4
        for i in range(4):
            await mcp_client.call_tool("start_step", {
                "scene_id": test_scene_id,
                "step_name": STEP_NAMES[i]
            })

            await mcp_client.call_tool("complete_step", {
                "scene_id": test_scene_id,
                "step_name": STEP_NAMES[i],
                "duration_seconds": 1.0
            })

        # Fail at Step 5
        await mcp_client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[4]
        })

        await mcp_client.call_tool("fail_generation", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[4],
            "failure_reason": "Critical validation failures: [blueprint_compliance, world_consistency]",
            "final_errors": [
                {
                    "step_name": STEP_NAMES[4],
                    "error_type": "validation_failure",
                    "message": "Critical issues in multiple validators",
                    "severity": "CRITICAL"
                }
            ]
        })

        state = mcp_client.get_state(test_scene_id)

        # Verify failure at validation step
        assert state["workflow_status"] == "FAILED"
        assert state["failed_at_step"] == 5
        assert "validation" in state["failure_reason"].lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_workflow_resume_after_failure(test_workspace, test_scene_id):
    """Test resuming workflow after fixing issues."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    async with mcp_client:
        # Initial workflow - fail at Step 4
        await mcp_client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Complete Steps 1-3
        for i in range(3):
            await mcp_client.call_tool("start_step", {
                "scene_id": test_scene_id,
                "step_name": STEP_NAMES[i]
            })

            await mcp_client.call_tool("complete_step", {
                "scene_id": test_scene_id,
                "step_name": STEP_NAMES[i],
                "duration_seconds": 1.0
            })

        # Fail at Step 4
        await mcp_client.call_tool("fail_generation", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[3],
            "failure_reason": "Max retries exhausted"
        })

        state1 = mcp_client.get_state(test_scene_id)
        assert state1["workflow_status"] == "FAILED"

        # Resume workflow
        resume_plan = await mcp_client.call_tool("resume_generation", {
            "scene_id": test_scene_id,
            "force": False
        })

        # Mock should provide resume plan
        assert resume_plan is not None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_logging_without_failure(test_workspace, test_scene_id):
    """Test that errors can be logged without failing workflow."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    runner = SimpleWorkflowRunner(mcp_client)

    # Run with retries (logs errors but completes successfully)
    result = await runner.run_retry_path(test_scene_id, retry_count=2)

    # Workflow should complete despite errors
    assert result.status == "COMPLETED"
    assert result.retry_count == 2

    # Errors should be logged
    state = mcp_client.get_state(test_scene_id)
    assert len(state.get("errors", [])) == 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mcp_calls_on_failure(test_workspace, test_scene_id):
    """Test MCP call count on failed workflow."""
    mcp_client = create_mcp_client(workspace=test_workspace, use_mock=True)

    async with mcp_client:
        await mcp_client.call_tool("start_generation", {
            "scene_id": test_scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Start Step 1
        await mcp_client.call_tool("start_step", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[0]
        })

        # Immediate failure
        await mcp_client.call_tool("fail_generation", {
            "scene_id": test_scene_id,
            "step_name": STEP_NAMES[0],
            "failure_reason": "Blueprint not found"
        })

        # Count MCP calls
        call_count = mcp_client.get_call_count()

        # Should be: start_generation + start_step + fail_generation = 3
        assert call_count == 3
