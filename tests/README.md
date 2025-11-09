# End-to-End Testing System

**Feature**: FEAT-0003
**Status**: In Development
**Documentation**: [`features/FEAT-0003-e2e-testing/README.md`](../features/FEAT-0003-e2e-testing/README.md)

---

## Overview

Comprehensive testing framework for the scene generation workflow using `claude_agent_sdk` and FastMCP patterns.

### Test Layers

1. **Unit Tests** (`tests/unit/`) - 50 tests targeting MCP tools and helpers
2. **Integration Tests** (`tests/integration/`) - 30 tests for MCP server
3. **E2E Tests** (`tests/e2e/`) - 15 tests for complete workflow

**Target Coverage**: >70% overall, >80% for `mcp_servers/generation_state_mcp.py`

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install -e .

# Or using uv
uv sync
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test layer
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/e2e/          # E2E tests only

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest --cov=mcp_servers --cov=tests tests/

# Run specific test
pytest tests/e2e/test_happy_path.py::test_successful_generation_first_attempt -v
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only e2e tests
pytest -m e2e

# Skip slow tests
pytest -m "not slow"
```

---

## Directory Structure

```
tests/
├── unit/                           # Unit tests (MCP tools, helpers)
│   ├── test_mcp_tools.py          # Test individual MCP tools
│   └── test_state_helpers.py      # Test helper functions
│
├── integration/                    # Integration tests (MCP server)
│   ├── test_mcp_server.py         # Test server with real file I/O
│   └── test_state_transitions.py  # Test workflow state machine
│
├── e2e/                           # End-to-end tests (full workflow)
│   ├── test_happy_path.py         # Successful generation scenarios
│   ├── test_retry_path.py         # Retry logic scenarios
│   ├── test_failure_path.py       # Failure handling scenarios
│   └── test_resume_path.py        # Resume capability scenarios
│
├── fixtures/                      # Test data
│   ├── blueprints/                # Test blueprints
│   │   └── scene-9999-blueprint.md
│   ├── agent_responses/           # Mock agent outputs
│   │   ├── blueprint-validator-pass.json
│   │   ├── prose-writer-success.md
│   │   └── validators-pass.json
│   ├── expected_outputs/          # Expected test results
│   └── workspace/                 # Temporary workspace (git-ignored)
│
├── helpers/                       # Test utilities
│   ├── sdk_client.py             # ClaudeSDKClient wrapper
│   ├── mcp_client.py             # MCP client utilities
│   ├── mock_tools.py             # @tool decorators for mocking
│   ├── workflow_runner.py        # E2E orchestrator
│   └── reporter.py               # Test report generator
│
├── failures/                      # Preserved test artifacts (git-ignored)
│   └── test_name_timestamp/      # Created on test failure
│
├── conftest.py                    # pytest configuration & fixtures
├── __init__.py
└── README.md                      # This file
```

---

## Fixtures

### Built-in Fixtures (from `conftest.py`)

#### `test_workspace`
Isolated workspace for each test. Automatically preserves artifacts on failure.

```python
def test_example(test_workspace):
    # test_workspace is a Path object to temporary directory
    state_file = test_workspace / "generation-state-9999.json"
    state_file.write_text('{"scene_id": "9999"}')
```

#### `test_scene_id`
Provides consistent test scene ID (`"9999"`).

```python
def test_example(test_scene_id):
    assert test_scene_id == "9999"
```

#### `test_blueprint_path`
Path to test blueprint fixture.

```python
def test_example(test_blueprint_path):
    assert test_blueprint_path == "tests/fixtures/blueprints/scene-9999-blueprint.md"
```

#### `mock_state_file`
Creates mock state file in test workspace.

```python
def test_example(mock_state_file):
    # mock_state_file is a Path to created state file
    state = json.loads(mock_state_file.read_text())
    assert state["scene_id"] == "9999"
```

### Environment Variables

Automatically set by `setup_test_environment` fixture:
- `WORKSPACE_PATH`: Points to `test_workspace`
- `STATE_FILE_PATTERN`: `"generation-state-*.json"`
- `TEST_MODE`: `"true"`

---

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_mcp_tools.py
import pytest
from mcp_servers.generation_state_mcp import mcp

@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_generation():
    """Test start_generation creates valid state file."""
    result = await mcp.call_tool("start_generation", {
        "scene_id": "9999",
        "blueprint_path": "tests/fixtures/blueprints/scene-9999-blueprint.md",
        "initiated_by": "test"
    })

    assert "workflow initialized" in result[0].text.lower()
```

### Integration Test Example

```python
# tests/integration/test_mcp_server.py
import pytest
from tests.helpers.mcp_client import MCPClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_state_transitions(test_workspace):
    """Test complete state machine through all steps."""
    client = MCPClient(workspace=test_workspace)

    # Step 1: Start generation
    await client.call_tool("start_generation", {...})
    state = await client.call_tool("get_generation_status", {...})
    assert state["workflow_status"] == "IN_PROGRESS"
```

### E2E Test Example

```python
# tests/e2e/test_happy_path.py
import pytest
from tests.helpers.sdk_client import TestSDKClient
from tests.helpers.workflow_runner import WorkflowRunner

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_successful_generation_first_attempt(test_workspace):
    """Test complete workflow succeeding on first try."""
    sdk_client = TestSDKClient(
        mock_tools=[...],
        workspace=test_workspace
    )

    runner = WorkflowRunner(sdk_client)
    result = await runner.run_generation("9999")

    assert result.status == "COMPLETED"
    assert result.retry_count == 0
```

---

## Test Artifacts

### On Test Failure

When a test fails, artifacts are automatically preserved in `tests/failures/<test_name>/`:

```
tests/failures/
└── test_successful_generation_first_attempt_2025-11-03_14-30-15/
    ├── generation-state-9999.json     # State file snapshot
    ├── artifacts/                      # Generated artifacts
    │   └── scene-9999/
    │       ├── draft-attempt1.md
    │       └── verification-plan.md
    └── logs/                           # Execution logs
        └── generation-coordinator.log
```

### Viewing Preserved Artifacts

```bash
# List failed test artifacts
ls tests/failures/

# View specific test artifacts
cd tests/failures/test_name_timestamp/
cat generation-state-9999.json
```

---

## Test Reports

### Running with Report Generation

```bash
# Generate detailed report
pytest tests/ -v --html=tests/reports/test-run.html

# Generate coverage report
pytest --cov=mcp_servers --cov=tests --cov-report=html tests/
# View at: htmlcov/index.html
```

---

## Troubleshooting

### Test Failures

1. **Check preserved artifacts**: `tests/failures/<test_name>/`
2. **Review test log**: `tests/pytest.log`
3. **Re-run with verbose output**: `pytest tests/path/to/test.py::test_name -vv`
4. **Enable debug logging**: Set `log_cli = true` in `pytest.ini`

### MCP Server Issues

If MCP server fails to connect:

```bash
# Test MCP server directly
python mcp-servers/generation_state_mcp.py

# Check environment variables
echo $WORKSPACE_PATH
echo $STATE_FILE_PATTERN
```

### Import Errors

```bash
# Ensure package is installed in editable mode
pip install -e .

# Verify installation
python -c "import mcp_servers.generation_state_mcp; print('OK')"
```

---

## CI/CD Integration (Optional)

### GitHub Actions Example

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -e .
      - run: pytest tests/ --cov=mcp_servers
```

---

## Performance Benchmarks

Expected test durations:

| Test Layer | Count | Duration | Per Test |
|-----------|-------|----------|----------|
| Unit | 50 | ~2 min | ~2-3s |
| Integration | 30 | ~5 min | ~10s |
| E2E | 15 | ~8 min | ~30s |
| **Total** | **95** | **~15 min** | - |

---

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py`, `test_function_name()`
2. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.e2e`, etc.
3. **Leverage fixtures**: Use `test_workspace`, `test_scene_id`, etc.
4. **Document test purpose**: Add docstring explaining what the test validates
5. **Update this README**: If adding new test categories or helpers

---

## References

- [Feature Documentation](../features/FEAT-0003-e2e-testing/README.md)
- [pytest Documentation](https://docs.pytest.org/)
- [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Generation Workflow](../.workflows/generation.md)

---

**Last Updated**: 2025-11-03
**Phase**: 1 (Foundation) - Complete
**Next Phase**: 2 (SDK Integration)
