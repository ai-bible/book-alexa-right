"""
Unit Tests for Helper Classes

Tests SDK client, MCP client, and workflow runner helpers.
"""

import pytest
from pathlib import Path
from tests.helpers.sdk_client import MockSDKClient, create_test_sdk_client
from tests.helpers.mcp_client import MockMCPClient, create_mcp_client
from tests.helpers.workflow_runner import WorkflowResult


@pytest.mark.unit
class TestMockSDKClient:
    """Tests for MockSDKClient."""

    @pytest.mark.asyncio
    async def test_mock_sdk_client_creation(self, test_workspace):
        """Test creating mock SDK client."""
        client = MockSDKClient(
            fixture_responses={"generate": "test response"},
            workspace=test_workspace
        )

        assert client is not None
        assert client.workspace == test_workspace

    @pytest.mark.asyncio
    async def test_mock_sdk_query(self, test_workspace):
        """Test querying mock SDK client."""
        responses = {
            "generate scene": {
                "text": "Generating scene 9999..."
            }
        }

        client = MockSDKClient(fixture_responses=responses, workspace=test_workspace)

        messages = []
        async for msg in client.query_agent("generate scene 9999"):
            messages.append(msg)

        assert len(messages) > 0
        assert "Generating" in messages[0]["text"]

    @pytest.mark.asyncio
    async def test_mock_sdk_hooks(self, test_workspace):
        """Test hook execution in mock SDK."""
        client = MockSDKClient(fixture_responses={}, workspace=test_workspace)

        hook_called = {"count": 0}

        async def test_hook(msg, tool_id, context):
            hook_called["count"] += 1

        client.add_hook("PostToolUse", test_hook)

        async for msg in client.query_agent("test"):
            pass

        assert hook_called["count"] > 0

    @pytest.mark.asyncio
    async def test_mock_sdk_history(self, test_workspace):
        """Test message history tracking."""
        client = MockSDKClient(
            fixture_responses={"test": {"text": "response"}},
            workspace=test_workspace
        )

        async for msg in client.query_agent("test"):
            pass

        history = client.get_message_history()
        assert len(history) > 0

        client.clear_history()
        assert len(client.get_message_history()) == 0


@pytest.mark.unit
class TestMockMCPClient:
    """Tests for MockMCPClient."""

    @pytest.mark.asyncio
    async def test_mock_mcp_client_creation(self, test_workspace):
        """Test creating mock MCP client."""
        client = MockMCPClient(workspace=test_workspace)

        assert client is not None
        assert client.workspace == test_workspace

    @pytest.mark.asyncio
    async def test_mock_mcp_start_generation(self, test_workspace):
        """Test start_generation with mock MCP."""
        client = MockMCPClient(workspace=test_workspace)

        result = await client.call_tool("start_generation", {
            "scene_id": "9999",
            "blueprint_path": "test.md",
            "initiated_by": "test"
        })

        assert result["success"] is True

        # Verify state created
        state = client.get_state("9999")
        assert state is not None
        assert state["workflow_status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_mock_mcp_workflow_progression(self, test_workspace):
        """Test complete workflow through mock MCP."""
        client = MockMCPClient(workspace=test_workspace)

        # Start
        await client.call_tool("start_generation", {
            "scene_id": "9999",
            "blueprint_path": "test.md",
            "initiated_by": "test"
        })

        # Progress through steps
        for step in range(1, 8):
            await client.call_tool("start_step", {
                "scene_id": "9999",
                "step_number": step
            })

            await client.call_tool("complete_step", {
                "scene_id": "9999",
                "step_number": step,
                "duration_seconds": 1.0
            })

        # Complete
        await client.call_tool("complete_generation", {
            "scene_id": "9999",
            "final_scene_path": "test.md",
            "validation_report_path": "report.json",
            "word_count": 500,
            "total_duration_seconds": 10.0,
            "retry_count": 0
        })

        # Verify final state
        state = client.get_state("9999")
        assert state["workflow_status"] == "COMPLETED"
        assert len(state["steps"]) == 7

    @pytest.mark.asyncio
    async def test_mock_mcp_call_logging(self, test_workspace):
        """Test call logging in mock MCP."""
        client = MockMCPClient(workspace=test_workspace)

        await client.call_tool("start_generation", {"scene_id": "9999"})
        await client.call_tool("get_generation_status", {"scene_id": "9999"})

        calls = client.get_call_log()
        assert len(calls) == 2

        assert calls[0]["tool_name"] == "start_generation"
        assert calls[1]["tool_name"] == "get_generation_status"

    @pytest.mark.asyncio
    async def test_mock_mcp_filter_by_tool(self, test_workspace):
        """Test filtering calls by tool name."""
        client = MockMCPClient(workspace=test_workspace)

        await client.call_tool("start_generation", {"scene_id": "9999"})
        await client.call_tool("start_step", {"scene_id": "9999", "step_number": 1})
        await client.call_tool("start_step", {"scene_id": "9999", "step_number": 2})

        start_step_calls = client.get_calls_by_tool("start_step")
        assert len(start_step_calls) == 2

        start_gen_calls = client.get_calls_by_tool("start_generation")
        assert len(start_gen_calls) == 1


@pytest.mark.unit
class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_test_sdk_client_real(self, test_workspace):
        """Test creating real SDK client."""
        client = create_test_sdk_client(
            workspace=test_workspace,
            use_mock=False
        )

        # Should create TestSDKClient (may not be usable without SDK installed)
        assert client is not None

    def test_create_test_sdk_client_mock(self, test_workspace):
        """Test creating mock SDK client."""
        client = create_test_sdk_client(
            workspace=test_workspace,
            use_mock=True,
            fixture_responses={"test": "response"}
        )

        assert isinstance(client, MockSDKClient)

    def test_create_mcp_client_real(self, test_workspace):
        """Test creating real MCP client."""
        client = create_mcp_client(
            workspace=test_workspace,
            use_mock=False
        )

        # Should create MCPClient
        assert client is not None

    def test_create_mcp_client_mock(self, test_workspace):
        """Test creating mock MCP client."""
        client = create_mcp_client(
            workspace=test_workspace,
            use_mock=True
        )

        assert isinstance(client, MockMCPClient)


@pytest.mark.unit
class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_workflow_result_creation(self):
        """Test creating WorkflowResult."""
        result = WorkflowResult(
            scene_id="9999",
            status="COMPLETED",
            total_steps=7,
            retry_count=0,
            duration_seconds=300.5,
            mcp_calls_count=16
        )

        assert result.scene_id == "9999"
        assert result.status == "COMPLETED"
        assert result.total_steps == 7
        assert result.retry_count == 0
        assert result.duration_seconds == 300.5
        assert result.mcp_calls_count == 16

    def test_workflow_result_from_state(self):
        """Test creating WorkflowResult from state dict."""
        state = {
            "scene_id": "9999",
            "workflow_status": "COMPLETED",
            "steps": {
                "step_1": {"status": "COMPLETED"},
                "step_2": {"status": "COMPLETED"},
                "step_3": {"status": "COMPLETED"}
            },
            "errors": []
        }

        result = WorkflowResult.from_state(state)

        assert result.scene_id == "9999"
        assert result.status == "COMPLETED"
        assert result.total_steps == 3
        assert result.retry_count == 0

    def test_workflow_result_with_failure(self):
        """Test WorkflowResult for failed workflow."""
        result = WorkflowResult(
            scene_id="9999",
            status="FAILED",
            total_steps=3,
            retry_count=3,
            duration_seconds=45.2,
            failed_step=4,
            failure_reason="Max retries exhausted",
            mcp_calls_count=21,
            errors=[
                {"error_type": "constraint_violation", "severity": "CRITICAL"}
            ]
        )

        assert result.status == "FAILED"
        assert result.failed_step == 4
        assert result.failure_reason == "Max retries exhausted"
        assert len(result.errors) == 1

    def test_workflow_result_optional_fields(self):
        """Test WorkflowResult with optional fields."""
        result = WorkflowResult(
            scene_id="9999",
            status="COMPLETED",
            total_steps=7,
            retry_count=0,
            duration_seconds=300,
            artifacts={
                "final_scene": "acts/.../scene-9999.md",
                "validation_report": "workspace/.../report.json"
            }
        )

        assert result.artifacts is not None
        assert "final_scene" in result.artifacts
        assert "validation_report" in result.artifacts


@pytest.mark.unit
class TestHelperIntegration:
    """Tests for integration between helpers."""

    @pytest.mark.asyncio
    async def test_sdk_and_mcp_together(self, test_workspace):
        """Test using SDK client and MCP client together."""
        sdk_client = MockSDKClient(
            fixture_responses={"generate": {"text": "OK"}},
            workspace=test_workspace
        )

        mcp_client = MockMCPClient(workspace=test_workspace)

        # SDK query
        async for msg in sdk_client.query_agent("generate scene 9999"):
            pass

        # MCP tracking
        await mcp_client.call_tool("start_generation", {"scene_id": "9999"})

        # Verify both worked
        assert len(sdk_client.get_message_history()) > 0
        assert mcp_client.get_call_count() == 1

    @pytest.mark.asyncio
    async def test_context_managers(self, test_workspace):
        """Test async context managers."""
        async with MockMCPClient(workspace=test_workspace) as client:
            await client.call_tool("start_generation", {"scene_id": "9999"})

            assert client.get_call_count() == 1

        # Context manager should have cleaned up (though mock doesn't do much)
