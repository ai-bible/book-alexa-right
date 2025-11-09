"""
Unit Tests for Mock Tools

Tests mock tool implementations from tests/helpers/mock_tools.py.
"""

import pytest
import json
from pathlib import Path
from tests.helpers.mock_tools import (
    create_mock_tools,
    create_mock_tool_list,
    mock_blueprint_validator_always_pass,
    mock_blueprint_validator_always_fail,
    mock_prose_writer_always_succeed,
    mock_validators_always_pass,
    mock_validators_always_fail
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestMockBlueprintValidator:
    """Tests for mock blueprint validator tool."""

    async def test_validator_pass_fixture(self):
        """Test validator returns PASS from fixture."""
        tools = create_mock_tools()
        validator = tools["validate_blueprint"]

        result = await validator({
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-blueprint.md"
        })

        assert result is not None
        assert "content" in result
        assert len(result["content"]) > 0

        # Parse JSON response
        response_text = result["content"][0]["text"]
        data = json.loads(response_text)

        assert data["status"] == "PASS"
        assert "constraints" in data
        assert "issues" in data

    async def test_validator_fail_fixture(self):
        """Test validator returns FAIL from fixture."""
        tools = create_mock_tools()
        validator = tools["validate_blueprint"]

        result = await validator({
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-fail-blueprint.md"
        })

        assert result is not None
        response_text = result["content"][0]["text"]
        data = json.loads(response_text)

        assert data["status"] == "FAIL"
        assert "issues" in data
        assert len(data["issues"]) > 0

    async def test_validator_always_pass(self):
        """Test always-pass validator."""
        result = await mock_blueprint_validator_always_pass({
            "blueprint_path": "any_path"
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["status"] == "PASS"

    async def test_validator_always_fail(self):
        """Test always-fail validator."""
        result = await mock_blueprint_validator_always_fail({
            "blueprint_path": "any_path"
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["status"] == "FAIL"
        assert len(data["issues"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestMockVerificationPlanner:
    """Tests for mock verification plan generator."""

    async def test_planner_generates_plan(self):
        """Test planner returns markdown plan."""
        tools = create_mock_tools()
        planner = tools["create_verification_plan"]

        result = await planner({
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-blueprint.md",
            "constraints": {
                "word_count": {"min": 800, "max": 1200}
            }
        })

        assert result is not None
        plan_text = result["content"][0]["text"]

        # Verify plan structure
        assert "# Verification Plan" in plan_text
        assert "Constraints to Verify" in plan_text
        assert "Validation Steps" in plan_text
        assert "800" in plan_text  # Word count min
        assert "1200" in plan_text  # Word count max


@pytest.mark.unit
@pytest.mark.asyncio
class TestMockProseWriter:
    """Tests for mock prose writer tool."""

    async def test_writer_success(self):
        """Test writer returns valid prose."""
        tools = create_mock_tools()
        writer = tools["generate_prose"]

        result = await writer({
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-blueprint.md",
            "constraints": {},
            "attempt": 1
        })

        assert result is not None
        prose = result["content"][0]["text"]

        # Verify prose has content
        assert len(prose) > 100
        assert "#" in prose  # Has markdown headers

    async def test_writer_fail_once(self):
        """Test writer fails on first attempt."""
        tools = create_mock_tools()
        writer = tools["generate_prose"]

        # First attempt with fail_once flag
        result1 = await writer({
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-fail_once-blueprint.md",
            "constraints": {},
            "attempt": 1
        })

        prose1 = result1["content"][0]["text"]
        assert "INVALID" in prose1

        # Second attempt should succeed
        result2 = await writer({
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-fail_once-blueprint.md",
            "constraints": {},
            "attempt": 2
        })

        prose2 = result2["content"][0]["text"]
        assert "INVALID" not in prose2

    async def test_writer_always_succeed(self):
        """Test always-succeed writer."""
        result = await mock_prose_writer_always_succeed({
            "blueprint_path": "any",
            "constraints": {},
            "attempt": 1
        })

        assert result is not None
        prose = result["content"][0]["text"]

        assert "Valid" in prose
        assert len(prose) > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestMockFastComplianceChecker:
    """Tests for mock fast compliance checker."""

    async def test_checker_pass(self):
        """Test checker returns PASS."""
        tools = create_mock_tools()
        checker = tools["check_compliance_fast"]

        result = await checker({
            "draft_path": "workspace/draft.md",
            "constraints": {}
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["status"] == "PASS"
        assert data["violations"] == []

    async def test_checker_fail(self):
        """Test checker returns FAIL for invalid draft."""
        tools = create_mock_tools()
        checker = tools["check_compliance_fast"]

        result = await checker({
            "draft_path": "workspace/invalid-draft.md",
            "constraints": {}
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["status"] == "FAIL"
        assert len(data["violations"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestMockValidationAggregator:
    """Tests for mock full validation aggregator."""

    async def test_aggregator_pass(self):
        """Test aggregator returns PASS."""
        tools = create_mock_tools()
        aggregator = tools["validate_full"]

        result = await aggregator({
            "draft_path": "workspace/draft.md",
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-blueprint.md",
            "constraints": {}
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["overall_status"] == "PASS"
        assert data["aggregated_score"] >= 0.70
        assert data["decision"] == "APPROVED_FOR_PUBLICATION"

    async def test_aggregator_fail(self):
        """Test aggregator returns FAIL."""
        tools = create_mock_tools()
        aggregator = tools["validate_full"]

        result = await aggregator({
            "draft_path": "workspace/fail-draft.md",
            "blueprint_path": "tests/fixtures/blueprints/scene-9999-blueprint.md",
            "constraints": {}
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["overall_status"] == "FAIL"
        assert data["critical_issues_count"] > 0
        assert data["decision"] == "REJECTED_RETRY_REQUIRED"

    async def test_validators_always_pass(self):
        """Test always-pass validators."""
        result = await mock_validators_always_pass({
            "draft_path": "any",
            "blueprint_path": "any",
            "constraints": {}
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["overall_status"] == "PASS"
        assert data["aggregated_score"] >= 0.90

    async def test_validators_always_fail(self):
        """Test always-fail validators."""
        result = await mock_validators_always_fail({
            "draft_path": "any",
            "blueprint_path": "any",
            "constraints": {}
        })

        assert result is not None
        data = json.loads(result["content"][0]["text"])

        assert data["overall_status"] == "FAIL"
        assert data["critical_issues_count"] > 0


@pytest.mark.unit
class TestMockToolsCreation:
    """Tests for mock tools factory functions."""

    def test_create_mock_tools_returns_dict(self):
        """Test create_mock_tools returns dictionary."""
        tools = create_mock_tools()

        assert isinstance(tools, dict)
        assert len(tools) >= 5  # At least 5 core tools

        # Check expected tools exist
        expected_tools = [
            "validate_blueprint",
            "create_verification_plan",
            "generate_prose",
            "check_compliance_fast",
            "validate_full"
        ]

        for tool_name in expected_tools:
            assert tool_name in tools

    def test_create_mock_tool_list_returns_list(self):
        """Test create_mock_tool_list returns list."""
        tools = create_mock_tool_list()

        assert isinstance(tools, list)
        assert len(tools) >= 5

        # All items should be callable
        for tool in tools:
            assert callable(tool)

    def test_custom_fixtures_dir(self):
        """Test custom fixtures directory."""
        custom_dir = Path("custom/fixtures")
        tools = create_mock_tools(fixtures_dir=custom_dir)

        # Should still create tools
        assert isinstance(tools, dict)
        assert len(tools) > 0
