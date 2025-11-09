"""
Workflow Runner - E2E Test Orchestrator

Orchestrates complete 6-step generation workflow with SDK client and MCP integration.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import time
import asyncio

# Step names from Scene Generation Workflow v2.0
STEP_NAMES = [
    "scene:gen:setup:files",
    "scene:gen:setup:blueprint",
    "scene:gen:setup:plan",
    "scene:gen:draft:prose",
    "scene:gen:review:validation",
    "scene:gen:publish:output"
]


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    scene_id: str
    status: str  # COMPLETED, FAILED, CANCELLED
    total_steps: int
    retry_count: int
    duration_seconds: float
    failed_step: Optional[int] = None
    failure_reason: Optional[str] = None
    artifacts: Optional[Dict[str, str]] = None
    mcp_calls_count: int = 0
    errors: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "WorkflowResult":
        """
        Create WorkflowResult from state dictionary.

        Args:
            state: State dictionary from MCP

        Returns:
            WorkflowResult instance
        """
        return cls(
            scene_id=state.get("scene_id", "unknown"),
            status=state.get("workflow_status", "UNKNOWN"),
            total_steps=len([s for s in state.get("steps", {}).values() if s.get("status") == "COMPLETED"]),
            retry_count=len(state.get("errors", [])),
            duration_seconds=state.get("total_duration_seconds", 0),
            failed_step=state.get("failed_at_step"),
            failure_reason=state.get("failure_reason"),
            artifacts=state.get("artifacts"),
            errors=state.get("errors", [])
        )


class WorkflowRunner:
    """
    E2E workflow orchestrator using SDK and MCP.

    Simulates complete 7-step generation workflow with:
    - Agent invocation via SDK
    - MCP state tracking
    - User interaction simulation
    - Hook-based monitoring
    """

    def __init__(self, sdk_client, mcp_client=None):
        """
        Initialize workflow runner.

        Args:
            sdk_client: TestSDKClient or MockSDKClient instance
            mcp_client: MCPClient or MockMCPClient instance (optional)
        """
        self.sdk = sdk_client
        self.mcp = mcp_client
        self.mcp_calls: List[Dict[str, Any]] = []
        self.user_responses: List[Dict[str, str]] = []

    async def run_generation(
        self,
        scene_id: str,
        blueprint_path: Optional[str] = None,
        user_approves_plan: bool = True,
        user_modifications: Optional[List[str]] = None,
        max_retries: int = 3
    ) -> WorkflowResult:
        """
        Run complete 7-step generation workflow.

        Args:
            scene_id: Scene ID to generate
            blueprint_path: Path to blueprint (default: test blueprint)
            user_approves_plan: Whether user approves verification plan
            user_modifications: List of plan modification requests
            max_retries: Maximum retry attempts

        Returns:
            WorkflowResult with execution details
        """
        workflow_start_time = time.time()

        if blueprint_path is None:
            blueprint_path = f"tests/fixtures/blueprints/scene-{scene_id}-blueprint.md"

        user_modifications = user_modifications or []

        # Add MCP monitoring hook
        async def mcp_monitor_hook(msg, tool_use_id, context):
            """Monitor MCP calls."""
            if isinstance(msg, dict) and "tool_name" in msg:
                self.mcp_calls.append(msg)

        self.sdk.add_hook("PostToolUse", mcp_monitor_hook)

        try:
            # STEP 0B: Initialize workflow via MCP
            if self.mcp:
                await self.mcp.call_tool("start_generation", {
                    "scene_id": scene_id,
                    "blueprint_path": blueprint_path,
                    "initiated_by": "test"
                })

            # Invoke generation-coordinator via SDK
            prompt = f"Generate scene {scene_id} using blueprint at {blueprint_path}"

            response_buffer = []
            verification_plan_shown = False

            async for message in self.sdk.query_agent(prompt):
                response_buffer.append(message)

                # Check if verification plan is presented
                msg_text = message.get("text", "").lower()

                if "verification plan" in msg_text and not verification_plan_shown:
                    verification_plan_shown = True

                    # Simulate user modifications
                    for modification in user_modifications:
                        mod_response = f"Please modify: {modification}"
                        self.user_responses.append({
                            "question": "verification_plan",
                            "answer": mod_response
                        })

                        # Send modification request
                        async for _ in self.sdk.query_agent(mod_response):
                            pass  # Consume responses

                    # Simulate user approval/rejection
                    if user_approves_plan:
                        approval_response = "Y"
                    else:
                        approval_response = "n"

                    self.user_responses.append({
                        "question": "approve_plan",
                        "answer": approval_response
                    })

                    # Send approval
                    async for _ in self.sdk.query_agent(approval_response):
                        pass  # Consume responses

                    # Log user interaction via MCP
                    if self.mcp:
                        await self.mcp.call_tool("log_question_answer", {
                            "scene_id": scene_id,
                            "question": "Approve verification plan?",
                            "answer": approval_response
                        })

            # Get final state from MCP
            if self.mcp:
                state = await self.mcp.call_tool("get_generation_status", {
                    "scene_id": scene_id,
                    "detailed": True
                })
            else:
                # Simulate successful completion
                state = {
                    "scene_id": scene_id,
                    "workflow_status": "COMPLETED" if user_approves_plan else "CANCELLED",
                    "current_step": 7 if user_approves_plan else 3,
                    "steps": {},
                    "errors": []
                }

            # Calculate duration
            duration = time.time() - workflow_start_time

            # Build result
            result = WorkflowResult.from_state(state)
            result.duration_seconds = duration
            result.mcp_calls_count = len(self.mcp_calls)

            return result

        except Exception as e:
            # Handle errors
            return WorkflowResult(
                scene_id=scene_id,
                status="FAILED",
                total_steps=0,
                retry_count=0,
                duration_seconds=time.time() - workflow_start_time,
                failure_reason=str(e),
                mcp_calls_count=len(self.mcp_calls)
            )

    async def resume_generation(
        self,
        scene_id: str,
        from_step: Optional[int] = None
    ) -> WorkflowResult:
        """
        Resume failed generation workflow.

        Args:
            scene_id: Scene ID to resume
            from_step: Step to resume from (auto-detected if None)

        Returns:
            WorkflowResult with execution details
        """
        workflow_start_time = time.time()

        try:
            # Get current state
            if self.mcp:
                state = await self.mcp.call_tool("get_generation_status", {
                    "scene_id": scene_id,
                    "detailed": True
                })

                # Check if resumable
                if state.get("workflow_status") not in ["FAILED", "CANCELLED"]:
                    raise ValueError(f"Cannot resume workflow in status: {state.get('workflow_status')}")

                # Get resume plan
                resume_plan = await self.mcp.call_tool("resume_generation", {
                    "scene_id": scene_id,
                    "force": False
                })

                resume_from_step = resume_plan.get("resume_from_step", from_step or 1)

            else:
                resume_from_step = from_step or 1

            # Invoke coordinator with resume request
            prompt = f"Resume generation for scene {scene_id} from step {resume_from_step}"

            async for message in self.sdk.query_agent(prompt):
                pass  # Consume responses

            # Get final state
            if self.mcp:
                state = await self.mcp.call_tool("get_generation_status", {
                    "scene_id": scene_id,
                    "detailed": True
                })
            else:
                state = {
                    "scene_id": scene_id,
                    "workflow_status": "COMPLETED",
                    "steps": {}
                }

            result = WorkflowResult.from_state(state)
            result.duration_seconds = time.time() - workflow_start_time
            result.mcp_calls_count = len(self.mcp_calls)

            return result

        except Exception as e:
            return WorkflowResult(
                scene_id=scene_id,
                status="FAILED",
                total_steps=0,
                retry_count=0,
                duration_seconds=time.time() - workflow_start_time,
                failure_reason=str(e),
                mcp_calls_count=len(self.mcp_calls)
            )

    def get_mcp_call_sequence(self) -> List[str]:
        """
        Get sequence of MCP tool calls.

        Returns:
            List of tool names in order called
        """
        return [call.get("tool_name", "unknown") for call in self.mcp_calls]

    def get_mcp_calls_by_step(self, step_name: str) -> List[Dict[str, Any]]:
        """
        Get MCP calls for specific step.

        Args:
            step_name: Step name to filter by (e.g., "scene:gen:draft:prose")

        Returns:
            List of MCP calls for that step
        """
        return [
            call for call in self.mcp_calls
            if call.get("arguments", {}).get("step_name") == step_name
        ]

    def get_user_responses(self) -> List[Dict[str, str]]:
        """
        Get all user responses during workflow.

        Returns:
            List of user response records
        """
        return self.user_responses

    def clear_history(self) -> None:
        """Clear call history and user responses."""
        self.mcp_calls.clear()
        self.user_responses.clear()
        if self.mcp and hasattr(self.mcp, 'clear_log'):
            self.mcp.clear_log()


class SimpleWorkflowRunner:
    """
    Simplified workflow runner for basic testing.

    Uses only MCP client without SDK integration.
    """

    def __init__(self, mcp_client):
        """
        Initialize simple runner.

        Args:
            mcp_client: MCPClient or MockMCPClient instance
        """
        self.mcp = mcp_client

    async def run_happy_path(self, scene_id: str) -> WorkflowResult:
        """
        Run happy path workflow (success on first try).

        Args:
            scene_id: Scene ID

        Returns:
            WorkflowResult
        """
        start_time = time.time()

        # Start generation
        await self.mcp.call_tool("start_generation", {
            "scene_id": scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Execute 6 steps
        for i, step_name in enumerate(STEP_NAMES):
            await self.mcp.call_tool("start_step", {
                "scene_id": scene_id,
                "step_name": step_name
            })

            await asyncio.sleep(0.1)  # Simulate work

            # Last step completes workflow
            metadata = {"workflow_complete": True} if i == len(STEP_NAMES) - 1 else None
            await self.mcp.call_tool("complete_step", {
                "scene_id": scene_id,
                "step_name": step_name,
                "duration_seconds": 0.1,
                "metadata": metadata
            })

        # Get final state
        state = await self.mcp.call_tool("get_status", {
            "scene_id": scene_id,
            "detailed": True
        })

        return WorkflowResult.from_state(state)

    async def run_retry_path(self, scene_id: str, retry_count: int = 1) -> WorkflowResult:
        """
        Run retry path workflow (failures then success).

        Args:
            scene_id: Scene ID
            retry_count: Number of retries before success

        Returns:
            WorkflowResult
        """
        start_time = time.time()

        await self.mcp.call_tool("start_generation", {
            "scene_id": scene_id,
            "blueprint_path": f"tests/fixtures/blueprints/scene-{scene_id}-blueprint.md",
            "initiated_by": "test"
        })

        # Steps 1-3
        for i in range(3):
            await self.mcp.call_tool("start_step", {
                "scene_id": scene_id,
                "step_name": STEP_NAMES[i]
            })
            await self.mcp.call_tool("complete_step", {
                "scene_id": scene_id,
                "step_name": STEP_NAMES[i],
                "duration_seconds": 0.1
            })

        # Step 4: Generation with retries
        step_name = STEP_NAMES[3]  # scene:gen:draft:prose
        for attempt in range(retry_count):
            await self.mcp.call_tool("fail_step", {
                "scene_id": scene_id,
                "step_name": step_name,
                "failure_reason": f"Attempt {attempt + 1} failed",
                "metadata": {
                    "attempt": attempt + 1,
                    "severity": "MEDIUM",
                    "terminal": False
                }
            })
            await self.mcp.call_tool("retry_step", {
                "scene_id": scene_id,
                "step_name": step_name,
                "metadata": {"attempt_number": attempt + 2}
            })

        # Final success
        await self.mcp.call_tool("complete_step", {
            "scene_id": scene_id,
            "step_name": step_name,
            "duration_seconds": 0.5
        })

        # Steps 5-6
        for i in range(4, 6):
            step_name = STEP_NAMES[i]
            await self.mcp.call_tool("start_step", {
                "scene_id": scene_id,
                "step_name": step_name
            })
            metadata = {"workflow_complete": True} if i == 5 else None
            await self.mcp.call_tool("complete_step", {
                "scene_id": scene_id,
                "step_name": step_name,
                "duration_seconds": 0.1,
                "metadata": metadata
            })

        # Get final state
        state = await self.mcp.call_tool("get_status", {
            "scene_id": scene_id,
            "detailed": True
        })

        return WorkflowResult.from_state(state)
