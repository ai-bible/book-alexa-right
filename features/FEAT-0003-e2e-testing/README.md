# FEAT-0003: End-to-End Testing System for Scene Generation Workflow

**Status**: In Development
**Priority**: High
**Created**: 2025-11-03
**Dependencies**: FEAT-0001 (Reliable Scene Generation), FEAT-0002 (Workflow State Tracking)

---

## Problem Statement

The scene generation workflow (6 steps, 17 MCP call points, multiple agents) has no automated testing. Manual testing is time-consuming, error-prone, and cannot validate complex scenarios like retry logic, resume capability, or parallel validation. Without automated tests, regressions are difficult to catch and new features risk breaking existing functionality.

---

## User Journey

### Starting Point
Developer has implemented new features (MCP state tracking, generation workflow) and needs confidence that:
- All 7 workflow steps execute correctly
- MCP state transitions are valid
- Retry logic works (1-3 attempts)
- Resume capability recovers from failures
- Hooks catch missed MCP calls

### Step-by-Step Flow

1. **Developer runs test suite**
   ```bash
   pytest tests/
   ```

2. **Test system sees**
   - Colored progress: `✅ test_happy_path_single_attempt PASSED`
   - Real-time MCP call logging
   - Step-by-step workflow validation

3. **System responds with**
   - Test results: `95 passed, 0 failed` (target)
   - Detailed logs for each test
   - Coverage report: `>70% overall`

4. **On test failure, developer then**
   - Views preserved artifacts in `tests/failures/<test_name>/`
   - Reads diff report (expected vs actual state)
   - Re-runs single failed test: `pytest tests/e2e/test_happy_path.py::test_scenario_1 -v`

5. **Developer fixes issue and re-runs**
   - Tests pass
   - Commits with confidence

### End State
Developer has validated all workflow scenarios automatically, with detailed logs and artifacts for debugging failures.

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────┐
│  TEST ORCHESTRATOR (Python + claude_agent_sdk)      │
│                                                      │
│  ┌──────────────────────────────────────────┐      │
│  │  ClaudeSDKClient (Async Streaming API)   │      │
│  │  - Programmatic agent invocation         │      │
│  │  - Custom hooks for test control         │      │
│  │  - MCP server integration                │      │
│  └───────────┬──────────────────────────────┘      │
│              │                                       │
│              ├──────────────────┐                   │
│              ▼                  ▼                    │
│  ┌─────────────────┐  ┌──────────────────┐         │
│  │  Real MCP       │  │  Mock Tools      │         │
│  │  Server         │  │  (@tool decorator)│        │
│  │                 │  │                  │         │
│  │  State tracking │  │  - blueprint_val │         │
│  │  11 tools       │  │  - prose_writer  │         │
│  │                 │  │  - validators    │         │
│  └─────────────────┘  └──────────────────┘         │
│              │                                       │
│              ▼                                       │
│  ┌─────────────────────────────────────────┐       │
│  │  Test Workspace (Isolated)              │       │
│  │  tests/fixtures/workspace_{test_id}/    │       │
│  │  - State files                          │       │
│  │  - Artifacts                            │       │
│  │  - Logs                                 │       │
│  └─────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

### Test Layers

#### Layer 1: Unit Tests (50 tests)
**Scope**: Individual MCP tools and helper functions

**Examples**:
- `test_start_generation()` - Validates state file creation
- `test_get_step_key()` - Helper function correctness
- `test_format_duration()` - Time formatting

**Coverage Target**: >80% of `generation_state_mcp.py`

#### Layer 2: Integration Tests (30 tests)
**Scope**: MCP server with real file I/O

**Examples**:
- `test_full_workflow_state_transitions()` - State machine validation
- `test_start_generation_idempotency()` - Duplicate call handling
- `test_resume_generation_from_step_4()` - Resume logic

**Coverage Target**: All 11 MCP tools + error paths

#### Layer 3: E2E Tests (15 tests)
**Scope**: Complete 6-step workflow with mocked agents

**Examples**:
- `test_happy_path_single_attempt()` - Success on first try
- `test_retry_on_second_attempt()` - Failure → Success
- `test_resume_after_failure()` - Recovery from terminal failure
- `test_max_retries_exhausted()` - Graceful failure
- `test_user_rejects_plan()` - Cancellation at Step 3

**Coverage Target**: All workflow scenarios documented in `.workflows/generation.md`

---

## Edge Cases & Behaviors

| Scenario | Expected Behavior |
|----------|-------------------|
| **Blueprint not found** | Test validates `fail_generation()` called at Step 1, workflow_status=FAILED |
| **Blueprint invalid** | Test validates `fail_generation()` called at Step 2, errors array populated |
| **User rejects plan** | Test validates `cancel_generation()` called at Step 3, workflow_status=CANCELLED |
| **Generation fails 3x** | Test validates `record_error()` called 3x (LOW→MEDIUM→HIGH), then `fail_generation()` |
| **Validation blocks** | Test validates `fail_generation()` at Step 6, final_errors contains validation report |
| **Resume from Step 4** | Test validates Steps 1-3 skipped, Step 4 executes with previous context |
| **Concurrent workflows** | Test validates error returned: "Generation already running for scene X" |
| **Corrupted state file** | Test validates graceful error handling, doesn't crash MCP server |
| **MCP server unavailable** | Test validates graceful degradation, hooks catch missed calls |
| **Hook execution** | Test validates PostToolUse and Stop hooks log warnings when state not updated |

---

## Definition of Done (DoD)

### Must Have:
- [x] Phase 1: Dependencies added (`claude-agent-sdk`, `pytest`, `pytest-asyncio`)
- [x] Phase 1: Test structure created (`tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`, `tests/helpers/`)
- [x] Phase 1: pytest configuration (`conftest.py`) with fixtures
- [ ] Phase 1: Test fixtures created (blueprints, agent responses)
- [ ] Phase 2: `SDKClient` wrapper implemented with hooks support
- [ ] Phase 2: Mock tools created with `@tool` decorator (blueprint validator, prose writer, validators)
- [ ] Phase 2: `WorkflowRunner` orchestrator implemented
- [ ] Phase 3: 50 unit tests implemented, >80% coverage achieved
- [ ] Phase 4: 30 integration tests implemented, all MCP tools covered
- [ ] Phase 5: 15 e2e tests implemented, all scenarios covered
- [ ] Phase 6: Test reporter with detailed logs implemented
- [ ] Phase 6: Artifact preservation on failure working
- [ ] All tests passing: `pytest tests/ -v` shows green
- [ ] Coverage report: `pytest --cov=mcp_servers --cov=tests tests/` >70%

### Polish:
- [ ] Detailed test reports generated (`tests/reports/test-run-{timestamp}.md`)
- [ ] CI/CD integration (GitHub Actions workflow, optional)
- [ ] Performance benchmarks measured (step durations)
- [ ] Documentation updated (`mcp-servers/README.md` + this README)

---

## Technical Specifications

### Dependencies

```toml
[project]
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
    "claude-agent-sdk>=0.1.6",  # NEW
    "pytest>=8.0.0",              # NEW
    "pytest-asyncio>=0.23.0",     # NEW
]
```

### Key Components

#### 1. SDKClient Wrapper (`tests/helpers/sdk_client.py`)

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.tools import create_sdk_mcp_server

class TestSDKClient:
    """Wrapper for testing with custom tools and hooks."""

    def __init__(self, mock_tools: List[Callable], workspace: Path):
        # Create in-process MCP server with mock tools
        mcp_server = create_sdk_mcp_server(mock_tools)

        self.options = ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Bash"],
            permission_mode='acceptEdits',
            mcp_servers=[mcp_server]
        )
        self.workspace = workspace
        self.hooks = []

    def add_hook(self, hook_type: str, callback: Callable):
        """Add test hook for validation."""
        self.hooks.append({"type": hook_type, "callback": callback})

    async def query_agent(self, prompt: str) -> AsyncIterator:
        """Query agent with streaming response."""
        async with ClaudeSDKClient(options=self.options) as client:
            await client.query(prompt)
            async for msg in client.receive_response():
                yield msg
```

#### 2. Mock Tools (`tests/helpers/mock_tools.py`)

```python
from claude_agent_sdk import tool

@tool("validate_blueprint", "Mock blueprint validator", {
    "blueprint_path": str
})
async def mock_blueprint_validator(args):
    """Return fixture-based validation result."""
    fixture = Path("tests/fixtures/agent_responses/blueprint-validator-pass.json")
    result = json.loads(fixture.read_text())
    return {"content": [{"type": "text", "text": json.dumps(result)}]}
```

#### 3. WorkflowRunner (`tests/helpers/workflow_runner.py`)

```python
class WorkflowRunner:
    """E2E workflow orchestrator using SDK."""

    def __init__(self, sdk_client: TestSDKClient, mcp_client: MCPClient):
        self.sdk = sdk_client
        self.mcp = mcp_client
        self.mcp_calls = []

    async def run_generation(self, scene_id: str,
                            user_approves_plan: bool = True) -> WorkflowResult:
        """Run complete 6-step workflow."""

        # Monitor MCP calls via hook
        async def mcp_monitor_hook(input_data, tool_use_id, context):
            if "mcp" in input_data.get("tool_name", ""):
                self.mcp_calls.append(input_data)

        self.sdk.add_hook("PostToolUse", mcp_monitor_hook)

        # Invoke generation-coordinator via SDK
        prompt = f"Generate scene {scene_id}"

        async for message in self.sdk.query_agent(prompt):
            # Process streaming responses
            if "verification plan" in message.get("text", "").lower():
                # Simulate user approval
                if user_approves_plan:
                    await self.sdk.query_agent("Y")
                else:
                    await self.sdk.query_agent("n")

        # Read final state
        state = await self.mcp.call_tool("get_generation_status", {
            "scene_id": scene_id,
            "detailed": True
        })

        return WorkflowResult.from_state(state)
```

#### 4. Test Reporter (`tests/helpers/reporter.py`)

```python
class TestReporter:
    """Generate detailed test reports."""

    def generate_report(self, result: WorkflowResult,
                       mcp_calls: List[dict]) -> str:
        """Create markdown report with MCP sequence and state diff."""
        # ... implementation
```

### Test Scenarios Covered

1. **Happy Path** (5 tests)
   - Success on attempt 1 (16 MCP calls)
   - Success on attempt 2 (19 MCP calls)
   - User modifies plan once
   - Parallel validation timing
   - Complete workflow under 8 minutes

2. **Retry Path** (3 tests)
   - Failure on attempt 1, success on 2
   - Failures on attempt 1-2, success on 3
   - Error severity progression (LOW→MEDIUM→HIGH)

3. **Failure Path** (3 tests)
   - Blueprint not found (Step 1 fail)
   - Blueprint invalid (Step 2 fail)
   - Max retries exhausted (Step 4 fail)

4. **Resume Path** (3 tests)
   - Resume from Step 2 (blueprint fixed)
   - Resume from Step 4 (constraints adjusted)
   - Resume from Step 6 (validation tweaked)

5. **Edge Cases** (1 test)
   - User rejects plan (cancel at Step 3)

---

## Visual Description

### Before Testing System:
- Manual workflow testing: ~30 minutes per scenario
- No validation of MCP call sequence
- No artifact preservation on failure
- Regressions discovered by users

### After Testing System:
- Automated testing: `pytest tests/` runs all scenarios in ~10 minutes
- Full MCP call sequence validated
- Detailed reports: `tests/reports/test-run-{timestamp}.md`
- Artifacts preserved: `tests/failures/<test_name>/`
- Regressions caught before commit

### Interaction Example:

```bash
$ pytest tests/e2e/test_happy_path.py -v

tests/e2e/test_happy_path.py::test_successful_generation_first_attempt PASSED [10s]
  ✅ MCP calls: 16/16 expected
  ✅ State transitions: valid (IN_PROGRESS → COMPLETED)
  ✅ Artifacts created: scene-9999.md, validation-report.json
  ✅ Duration: 7.2s

tests/e2e/test_happy_path.py::test_retry_on_second_attempt PASSED [12s]
  ✅ MCP calls: 19/19 expected (3 record_error)
  ✅ State transitions: valid (errors logged)
  ✅ Retry count: 1 (as expected)
  ✅ Duration: 10.8s

======================== 2 passed in 22.5s =========================
```

---

## Open Questions

### Resolved:
- ✅ **Q**: Use real MCP server or mocks?
  - **A**: Hybrid - real MCP server + mocked agents (best of both)

- ✅ **Q**: How to invoke agents programmatically?
  - **A**: Use `claude_agent_sdk.ClaudeSDKClient` with streaming API

- ✅ **Q**: How to validate MCP call sequence?
  - **A**: Custom hook (`PostToolUse`) logs all MCP calls for assertion

### Pending:
- ⏳ **Q**: Should tests run in CI/CD pipeline?
  - **A**: TBD - depends on CI setup (GitHub Actions, GitLab CI)

- ⏳ **Q**: Performance benchmarks - what are acceptable durations?
  - **A**: TBD - measure actual durations during Phase 5, set SLA thresholds

- ⏳ **Q**: How to test hooks themselves?
  - **A**: TBD - may need separate hook unit tests

---

## Timeline & Phases

| Phase | Duration | Deliverables | Status |
|-------|----------|--------------|--------|
| **Phase 1: Foundation** | 3 days | Dependencies, structure, fixtures, pytest config | ✅ In Progress |
| **Phase 2: SDK Integration** | 5 days | SDKClient wrapper, mock tools, WorkflowRunner | 🔲 Pending |
| **Phase 3: Unit Tests** | 5 days | 50 unit tests, >80% coverage | 🔲 Pending |
| **Phase 4: Integration Tests** | 7 days | 30 integration tests, all MCP tools | 🔲 Pending |
| **Phase 5: E2E Tests** | 10 days | 15 e2e tests, all scenarios | 🔲 Pending |
| **Phase 6: Reporting** | 3 days | Test reporter, artifacts, docs | 🔲 Pending |
| **TOTAL** | **33 days** | **95 tests, full e2e coverage** | **0% complete** |

---

## Success Metrics

### Quantitative:
- ✅ 95 tests implemented (50 unit + 30 integration + 15 e2e)
- ✅ >70% code coverage overall
- ✅ >80% coverage for `generation_state_mcp.py`
- ✅ All tests passing: `pytest tests/ -v` green
- ✅ Test suite runtime <15 minutes

### Qualitative:
- ✅ Developer can validate changes before commit
- ✅ Regressions caught automatically
- ✅ Test failures provide actionable debugging info
- ✅ New features can be test-driven (TDD)

---

## Integration with Existing System

### Connects To:
- **FEAT-0001**: Validates 6-step generation workflow
- **FEAT-0002**: Tests all 11 MCP tools (state tracking)
- `.claude/agents/generation/generation-coordinator.md`: Tests coordinator logic
- `mcp-servers/generation_state_mcp.py`: Unit/integration tests

### Updates Required:
- `mcp-servers/README.md`: Add "Testing" section with examples
- `.github/workflows/tests.yml`: Optional CI/CD integration
- `CLAUDE.md`: Add section on running tests

---

## References

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk/overview)
- [FastMCP Testing Patterns](https://github.com/jlowin/fastmcp)
- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Generation Workflow](.workflows/generation.md)
- [MCP Server Implementation](mcp-servers/generation_state_mcp.py)

---

**Ready for Implementation**: ✅ Yes

**Approved By**: [Your Name]
**Start Date**: 2025-11-03
**Target Completion**: 2025-12-06 (33 days)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2025-11-03 | Initial feature specification |
| 0.2 | 2025-11-03 | Added Phase 1 implementation (dependencies, structure, conftest) |
