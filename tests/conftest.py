"""
Pytest Configuration for End-to-End Testing System

This module provides shared fixtures and configuration for all tests.
"""

import pytest
import shutil
import json
from pathlib import Path
from typing import Generator
from datetime import datetime


@pytest.fixture
def test_workspace(tmp_path, request) -> Generator[Path, None, None]:
    """
    Create isolated workspace for each test.

    Preserves artifacts on test failure for debugging.

    Args:
        tmp_path: pytest's temporary directory fixture
        request: pytest request object for test metadata

    Yields:
        Path: Isolated workspace directory
    """
    # Create unique workspace for this test
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    workspace = tmp_path / f"workspace_{test_name}"
    workspace.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (workspace / "artifacts").mkdir(exist_ok=True)
    (workspace / "logs").mkdir(exist_ok=True)

    yield workspace

    # Preserve artifacts if test failed
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        preserve_dir = Path("tests/failures") / test_name
        preserve_dir.parent.mkdir(parents=True, exist_ok=True)

        if preserve_dir.exists():
            shutil.rmtree(preserve_dir)

        shutil.copytree(workspace, preserve_dir)
        print(f"\n⚠️  Test failed - artifacts preserved at: {preserve_dir}")


@pytest.fixture
def test_scene_id() -> str:
    """
    Provide consistent test scene ID.

    Returns:
        str: Test scene ID (9999)
    """
    return "9999"


@pytest.fixture
def test_blueprint_path(test_scene_id: str) -> str:
    """
    Provide path to test blueprint fixture.

    Args:
        test_scene_id: Scene ID from fixture

    Returns:
        str: Path to test blueprint
    """
    return f"tests/fixtures/blueprints/scene-{test_scene_id}-blueprint.md"


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, test_workspace):
    """
    Set environment variables for testing.

    Automatically applied to all tests.

    Args:
        monkeypatch: pytest's monkeypatch fixture
        test_workspace: Workspace from fixture
    """
    # Point MCP server to test workspace
    monkeypatch.setenv("WORKSPACE_PATH", str(test_workspace))
    monkeypatch.setenv("STATE_FILE_PATTERN", "generation-state-*.json")
    monkeypatch.setenv("TEST_MODE", "true")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    Store test result in request node for artifact preservation.

    This hook allows fixtures to access test outcomes.
    """
    outcome = yield
    rep = outcome.get_result()

    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture
def mock_state_file(test_workspace, test_scene_id) -> Path:
    """
    Create mock state file for testing state operations.

    Args:
        test_workspace: Workspace from fixture
        test_scene_id: Scene ID from fixture

    Returns:
        Path: Path to created state file
    """
    state_path = test_workspace / f"generation-state-{test_scene_id}.json"

    state = {
        "scene_id": test_scene_id,
        "session_id": f"2025-11-03-test-scene-{test_scene_id}",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "workflow_status": "IN_PROGRESS",
        "current_step": 1,
        "current_phase": "File Check",
        "steps": {},
        "user_questions": [],
        "errors": [],
        "metadata": {
            "trigger": "test",
            "user_id": "test_user"
        }
    }

    state_path.write_text(json.dumps(state, indent=2))
    return state_path


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest for async tests."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
