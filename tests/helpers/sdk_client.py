"""
ClaudeSDKClient Wrapper for Testing

Provides a wrapper around claude_agent_sdk for programmatic agent invocation
with custom tools, hooks, and MCP server integration.
"""

from typing import List, Callable, Dict, Any, AsyncIterator, Optional
from pathlib import Path
import json


class TestSDKClient:
    """
    Wrapper for ClaudeSDKClient with testing capabilities.

    Features:
    - Custom tool integration via @tool decorator
    - Hook support for test control
    - MCP server integration
    - Streaming response handling
    """

    def __init__(self, mock_tools: List[Callable], workspace: Path):
        """
        Initialize test SDK client.

        Args:
            mock_tools: List of mock tools decorated with @tool
            workspace: Path to test workspace directory
        """
        self.mock_tools = mock_tools
        self.workspace = workspace
        self.hooks: List[Dict[str, Any]] = []
        self.mcp_servers: List[Any] = []
        self.messages: List[Dict[str, Any]] = []

        # Import SDK components (will be available when installed)
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
            from claude_agent_sdk.tools import create_sdk_mcp_server

            self.ClaudeSDKClient = ClaudeSDKClient
            self.ClaudeAgentOptions = ClaudeAgentOptions
            self.create_sdk_mcp_server = create_sdk_mcp_server
            self.sdk_available = True
        except ImportError:
            self.sdk_available = False

        # Create in-process MCP server with mock tools
        if self.sdk_available and mock_tools:
            mcp_server = self.create_sdk_mcp_server(mock_tools)
            self.mcp_servers.append(mcp_server)

        # Configure options
        if self.sdk_available:
            self.options = self.ClaudeAgentOptions(
                allowed_tools=["Read", "Write", "Bash"],
                permission_mode='acceptEdits',
                mcp_servers=self.mcp_servers
            )
        else:
            self.options = None

    def add_hook(self, hook_type: str, callback: Callable) -> None:
        """
        Add test hook for validation.

        Args:
            hook_type: Type of hook ("PostToolUse", "PreToolUse", etc.)
            callback: Async callback function to execute
        """
        self.hooks.append({
            "type": hook_type,
            "callback": callback
        })

    async def query_agent(self, prompt: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Query agent with streaming response.

        Args:
            prompt: Prompt to send to agent

        Yields:
            Dict: Message objects from agent response stream
        """
        if not self.sdk_available:
            raise ImportError(
                "claude-agent-sdk not installed. "
                "Install with: pip install claude-agent-sdk>=0.1.6"
            )

        async with self.ClaudeSDKClient(options=self.options) as client:
            # Send query
            await client.query(prompt)

            # Stream responses
            async for msg in client.receive_response():
                # Store message for later inspection
                self.messages.append(msg)

                # Execute hooks
                for hook in self.hooks:
                    if hook["type"] == "PostToolUse":
                        await hook["callback"](msg, None, {})

                yield msg

    async def query_and_collect(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Query agent and collect all responses.

        Args:
            prompt: Prompt to send to agent

        Returns:
            List of all message objects
        """
        messages = []
        async for msg in self.query_agent(prompt):
            messages.append(msg)
        return messages

    def get_message_history(self) -> List[Dict[str, Any]]:
        """
        Get all messages received from agent.

        Returns:
            List of message objects
        """
        return self.messages

    def clear_history(self) -> None:
        """Clear message history."""
        self.messages.clear()


class MockSDKClient:
    """
    Mock SDK client for testing without actual SDK.

    Simulates SDK behavior using fixture-based responses.
    """

    def __init__(self, fixture_responses: Dict[str, Any], workspace: Path):
        """
        Initialize mock SDK client.

        Args:
            fixture_responses: Dict mapping prompts to fixture responses
            workspace: Path to test workspace directory
        """
        self.fixture_responses = fixture_responses
        self.workspace = workspace
        self.messages: List[Dict[str, Any]] = []
        self.hooks: List[Dict[str, Any]] = []

    def add_hook(self, hook_type: str, callback: Callable) -> None:
        """Add test hook."""
        self.hooks.append({"type": hook_type, "callback": callback})

    async def query_agent(self, prompt: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Query agent with fixture-based responses.

        Args:
            prompt: Prompt to send to agent

        Yields:
            Dict: Mock message objects
        """
        # Match prompt to fixture
        for pattern, response in self.fixture_responses.items():
            if pattern.lower() in prompt.lower():
                # Load fixture if path
                if isinstance(response, (str, Path)) and Path(response).exists():
                    fixture_path = Path(response)
                    if fixture_path.suffix == '.json':
                        with open(fixture_path) as f:
                            response = json.load(f)
                    else:
                        response = {"text": fixture_path.read_text()}

                # Yield mock message
                message = {
                    "type": "text",
                    "text": response.get("text", str(response)),
                    "data": response
                }
                self.messages.append(message)

                # Execute hooks
                for hook in self.hooks:
                    if hook["type"] == "PostToolUse":
                        await hook["callback"](message, None, {})

                yield message
                return

        # Default response
        yield {"type": "text", "text": "Mock response", "data": {}}

    async def query_and_collect(self, prompt: str) -> List[Dict[str, Any]]:
        """Query and collect all responses."""
        messages = []
        async for msg in self.query_agent(prompt):
            messages.append(msg)
        return messages

    def get_message_history(self) -> List[Dict[str, Any]]:
        """Get message history."""
        return self.messages

    def clear_history(self) -> None:
        """Clear history."""
        self.messages.clear()


def create_test_sdk_client(
    mock_tools: Optional[List[Callable]] = None,
    workspace: Optional[Path] = None,
    use_mock: bool = False,
    fixture_responses: Optional[Dict[str, Any]] = None
) -> TestSDKClient | MockSDKClient:
    """
    Factory function to create appropriate SDK client for testing.

    Args:
        mock_tools: List of mock tools (for real SDK)
        workspace: Test workspace path
        use_mock: If True, use MockSDKClient instead of real SDK
        fixture_responses: Fixture responses for MockSDKClient

    Returns:
        TestSDKClient or MockSDKClient instance
    """
    if workspace is None:
        workspace = Path("tests/fixtures/workspace")

    if use_mock:
        return MockSDKClient(
            fixture_responses=fixture_responses or {},
            workspace=workspace
        )
    else:
        return TestSDKClient(
            mock_tools=mock_tools or [],
            workspace=workspace
        )
