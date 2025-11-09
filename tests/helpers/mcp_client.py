"""
MCP Client Utilities for Testing

Provides simplified client for JSON-RPC communication with MCP server.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio


class MCPClient:
    """
    Simplified MCP client for testing.

    Communicates with MCP server via stdio using JSON-RPC 2.0 protocol.
    """

    def __init__(
        self,
        server_path: str = "mcp-servers/generation_state_mcp.py",
        workspace: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ):
        """
        Initialize MCP client.

        Args:
            server_path: Path to MCP server script
            workspace: Path to workspace directory
            env: Additional environment variables
        """
        self.server_path = Path(server_path)
        self.workspace = workspace or Path("tests/fixtures/workspace")
        self.env = env or {}
        self.proc: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.call_log: List[Dict[str, Any]] = []

        # Default environment
        self.env.update({
            "PYTHONUNBUFFERED": "1",
            "WORKSPACE_PATH": str(self.workspace),
            "STATE_FILE_PATTERN": "generation-state-*.json",
            "TEST_MODE": "true"
        })

    async def connect(self) -> None:
        """Start MCP server process."""
        if self.proc is not None:
            return  # Already connected

        self.proc = subprocess.Popen(
            ["python", str(self.server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            text=False  # Binary mode for proper encoding
        )

        # Wait a moment for server to initialize
        await asyncio.sleep(0.5)

    async def disconnect(self) -> None:
        """Stop MCP server process."""
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call MCP tool and return result.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            Tool result dictionary

        Raises:
            MCPError: If tool call fails
            ConnectionError: If not connected to server
        """
        if self.proc is None:
            raise ConnectionError("Not connected to MCP server. Call connect() first.")

        self.request_id += 1

        # Build JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Log the call
        self.call_log.append({
            "tool_name": tool_name,
            "arguments": arguments,
            "request_id": self.request_id
        })

        # Send request
        request_json = json.dumps(request) + "\n"
        self.proc.stdin.write(request_json.encode('utf-8'))
        self.proc.stdin.flush()

        # Read response
        response_line = self.proc.stdout.readline()
        if not response_line:
            raise ConnectionError("MCP server closed connection")

        response = json.loads(response_line.decode('utf-8'))

        # Check for errors
        if "error" in response:
            error = response["error"]
            raise MCPError(
                error.get("message", "Unknown error"),
                error.get("code", -1),
                error.get("data")
            )

        # Return result
        return response.get("result", {})

    def get_call_log(self) -> List[Dict[str, Any]]:
        """
        Get log of all MCP calls made.

        Returns:
            List of call records
        """
        return self.call_log

    def get_call_count(self) -> int:
        """
        Get total number of MCP calls made.

        Returns:
            Number of calls
        """
        return len(self.call_log)

    def get_calls_by_tool(self, tool_name: str) -> List[Dict[str, Any]]:
        """
        Get all calls to specific tool.

        Args:
            tool_name: Name of tool to filter by

        Returns:
            List of matching call records
        """
        return [
            call for call in self.call_log
            if call["tool_name"] == tool_name
        ]

    def clear_log(self) -> None:
        """Clear call log."""
        self.call_log.clear()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class MCPError(Exception):
    """MCP protocol error."""

    def __init__(self, message: str, code: int = -1, data: Any = None):
        """
        Initialize MCP error.

        Args:
            message: Error message
            code: JSON-RPC error code
            data: Additional error data
        """
        super().__init__(message)
        self.code = code
        self.data = data


class MockMCPClient:
    """
    Mock MCP client for testing without real server.

    Simulates MCP server behavior using in-memory state.
    """

    def __init__(self, workspace: Optional[Path] = None):
        """
        Initialize mock MCP client.

        Args:
            workspace: Path to workspace directory
        """
        self.workspace = workspace or Path("tests/fixtures/workspace")
        self.states: Dict[str, Dict[str, Any]] = {}
        self.call_log: List[Dict[str, Any]] = []

    async def connect(self) -> None:
        """Mock connect (no-op)."""
        pass

    async def disconnect(self) -> None:
        """Mock disconnect (no-op)."""
        pass

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Mock tool call with simulated behavior.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            Simulated tool result
        """
        # Log the call
        self.call_log.append({
            "tool_name": tool_name,
            "arguments": arguments
        })

        scene_id = arguments.get("scene_id")

        # Simulate tool behavior
        if tool_name == "start_generation":
            self.states[scene_id] = {
                "scene_id": scene_id,
                "workflow_status": "IN_PROGRESS",
                "current_step": 1,
                "steps": {},
                "errors": []
            }
            return {"success": True, "message": "Workflow initialized"}

        elif tool_name == "get_generation_status":
            if scene_id not in self.states:
                return {
                    "workflow_status": "NOT_FOUND",
                    "message": f"No workflow found for scene {scene_id}"
                }
            return self.states[scene_id]

        elif tool_name == "start_step":
            if scene_id in self.states:
                step_num = arguments.get("step_number")
                self.states[scene_id]["current_step"] = step_num
                self.states[scene_id]["steps"][f"step_{step_num}"] = {
                    "status": "IN_PROGRESS"
                }
            return {"success": True}

        elif tool_name == "complete_step":
            if scene_id in self.states:
                step_num = arguments.get("step_number")
                self.states[scene_id]["steps"][f"step_{step_num}"] = {
                    "status": "COMPLETED",
                    "duration_seconds": arguments.get("duration_seconds", 0)
                }
            return {"success": True}

        elif tool_name == "complete_generation":
            if scene_id in self.states:
                self.states[scene_id]["workflow_status"] = "COMPLETED"
            return {"success": True, "message": "Workflow completed"}

        elif tool_name == "fail_generation":
            if scene_id in self.states:
                self.states[scene_id]["workflow_status"] = "FAILED"
                self.states[scene_id]["failure_reason"] = arguments.get("failure_reason")
            return {"success": True, "message": "Workflow failed"}

        else:
            # Generic success for unknown tools
            return {"success": True, "message": f"Mock tool {tool_name} executed"}

    def get_call_log(self) -> List[Dict[str, Any]]:
        """Get call log."""
        return self.call_log

    def get_call_count(self) -> int:
        """Get call count."""
        return len(self.call_log)

    def get_calls_by_tool(self, tool_name: str) -> List[Dict[str, Any]]:
        """Get calls by tool name."""
        return [
            call for call in self.call_log
            if call["tool_name"] == tool_name
        ]

    def clear_log(self) -> None:
        """Clear log."""
        self.call_log.clear()

    def get_state(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for scene."""
        return self.states.get(scene_id)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


def create_mcp_client(
    workspace: Optional[Path] = None,
    use_mock: bool = False,
    **kwargs
) -> MCPClient | MockMCPClient:
    """
    Factory function to create appropriate MCP client.

    Args:
        workspace: Workspace directory path
        use_mock: If True, use MockMCPClient
        **kwargs: Additional arguments for MCPClient

    Returns:
        MCPClient or MockMCPClient instance
    """
    if use_mock:
        return MockMCPClient(workspace=workspace)
    else:
        return MCPClient(workspace=workspace, **kwargs)
