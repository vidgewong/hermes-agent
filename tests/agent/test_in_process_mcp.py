"""Tests for agent.in_process_mcp — in-process MCP server builder."""

import json
import sys
from unittest.mock import patch, MagicMock

import pytest


class MockAgent:
    """Minimal mock for AIAgent."""
    _delegate_depth = 0
    _memory_store = None
    _todo_store = None
    _read_terminal_callback = None


class TestBuildHermesInProcessMcp:
    """Tests for build_hermes_in_process_mcp()."""

    def test_returns_mcp_sdk_server_config(self):
        """Config has type='sdk' and an instance."""
        from agent.in_process_mcp import build_hermes_in_process_mcp

        config = build_hermes_in_process_mcp(MockAgent())

        assert config["type"] == "sdk"
        assert config["name"] == "hermes-tools"
        assert "instance" in config

    def test_blocked_tools_excluded(self):
        """clarify and computer_use must not be registered."""
        from agent.in_process_mcp import build_hermes_in_process_mcp, _BLOCKED_TOOLS

        agent = MockAgent()
        config = build_hermes_in_process_mcp(agent)
        server = config["instance"]

        # Get registered tool names from the server
        from mcp.server.lowlevel.server import Server
        assert isinstance(server, Server)

        # The blocked tools should not be in the registered tools
        # We verify by checking the tool list from the server
        import asyncio

        async def _list_tools():
            from mcp.types import ListToolsRequest
            result = await server.request_handlers.get("tools/list")(
                ListToolsRequest(method="tools/list")
            )
            return [t.name for t in result.tools]

        tool_names = asyncio.run(_list_tools())
        for blocked in _BLOCKED_TOOLS:
            assert blocked not in tool_names, f"{blocked} should be blocked"

    def test_expected_tools_registered(self):
        """Common Hermes tools should be present."""
        from agent.in_process_mcp import build_hermes_in_process_mcp

        agent = MockAgent()
        config = build_hermes_in_process_mcp(agent)
        server = config["instance"]

        import asyncio
        from mcp.types import ListToolsRequest

        async def _list_tools():
            result = await server.request_handlers.get("tools/list")(
                ListToolsRequest(method="tools/list")
            )
            return [t.name for t in result.tools]

        tool_names = asyncio.run(_list_tools())

        # These should always be registered
        for expected in ("web_search", "terminal", "memory", "todo", "session_search"):
            # web_search may not be available if check_fn fails, but others should be
            if expected in ("memory", "todo", "session_search"):
                assert expected in tool_names, f"{expected} should be registered"

    def test_delegate_task_not_blocked(self):
        """delegate_task should be available (not in _BLOCKED_TOOLS)."""
        from agent.in_process_mcp import _BLOCKED_TOOLS

        assert "delegate_task" not in _BLOCKED_TOOLS


class TestErrorIsolation:
    """Tests for error handling in tool handlers."""

    def test_handler_exception_returns_json_error(self):
        """Tool handler exceptions must not crash, must return error JSON."""
        from agent.in_process_mcp import _make_handler
        import asyncio

        agent = MockAgent()

        with patch("model_tools.handle_function_call") as mock_hfc:
            mock_hfc.side_effect = RuntimeError("boom")

            handler = _make_handler("test_tool", agent)
            result = asyncio.run(handler({"arg": "val"}))

        assert "content" in result
        text = result["content"][0]["text"]
        parsed = json.loads(text)
        assert "error" in parsed
        assert "boom" in parsed["error"]
        assert parsed["tool"] == "test_tool"


class TestHandleFunctionCallAgentParam:
    """Tests for the agent parameter in handle_function_call."""

    def test_agent_loop_tools_blocked_without_agent(self):
        """_AGENT_LOOP_TOOLS should be blocked when agent=None."""
        from model_tools import handle_function_call

        result = handle_function_call("delegate_task", {"goal": "x"})
        parsed = json.loads(result)
        assert "must be handled by the agent loop" in parsed["error"]

    def test_agent_loop_tools_unblocked_with_agent(self):
        """_AGENT_LOOP_TOOLS should NOT be blocked when agent is provided."""
        from model_tools import handle_function_call

        result = handle_function_call("delegate_task", {"goal": "x"}, agent=MockAgent())
        parsed = json.loads(result)
        # Should not be the "must be handled" error — will be a different error
        # since MockAgent doesn't fully implement AIAgent
        assert "must be handled by the agent loop" not in parsed.get("error", "")


class TestFallbackToStdio:
    """Tests for graceful fallback to stdio MCP."""

    def test_fallback_when_sdk_import_fails(self):
        """If create_sdk_mcp_server is not importable, fall back to stdio."""
        from agent.claude_code_sdk_runtime import _build_hermes_tools_mcp_config

        with patch("agent.in_process_mcp.build_hermes_in_process_mcp") as mock_build:
            mock_build.side_effect = ImportError("no such module")

            # The outer function catches ImportError and falls back
            with patch(
                "agent.claude_code_sdk_runtime._build_hermes_tools_mcp_config_stdio"
            ) as mock_stdio:
                mock_stdio.return_value = {
                    "hermes-tools": {"type": "stdio", "command": "python"}
                }
                config = _build_hermes_tools_mcp_config(MockAgent())

            assert config["hermes-tools"]["type"] == "stdio"
