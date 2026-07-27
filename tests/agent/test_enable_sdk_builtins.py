"""Tests for the enable-sdk-builtins change.

Covers:
- Tool blocklist changes (AskUserQuestion, Agent, Monitor unblocked)
- AskUserQuestion bridge (format translation, session type routing)
- Subagent profile definitions
"""

import asyncio
import json
import os
from unittest.mock import patch, MagicMock

import pytest


class TestToolBlocklist:
    """Verify AskUserQuestion, Agent, Monitor are NOT blocked."""

    def test_ask_user_question_not_blocked(self):
        """AskUserQuestion should not be in _builtin_tools_to_block."""
        # We can't easily access the local var, so we verify the effect:
        # construct a session and check disallowed_tools doesn't contain it
        import agent.claude_code_session as mod
        source = open(mod.__file__).read()
        assert '"AskUserQuestion"' not in source.split("_builtin_tools_to_block")[1].split("]")[0]

    def test_agent_not_blocked(self):
        """Agent should not be in _builtin_tools_to_block."""
        import agent.claude_code_session as mod
        source = open(mod.__file__).read()
        block_section = source.split("_builtin_tools_to_block")[1].split("]")[0]
        # "Agent" should only appear in comments, not as a list item
        lines = block_section.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert '"Agent"' not in stripped, f"Agent still blocked: {stripped}"

    def test_monitor_not_blocked(self):
        """Monitor should not be in _builtin_tools_to_block."""
        import agent.claude_code_session as mod
        source = open(mod.__file__).read()
        block_section = source.split("_builtin_tools_to_block")[1].split("]")[0]
        lines = block_section.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert '"Monitor"' not in stripped

    def test_workflow_still_blocked(self):
        """Workflow should remain blocked."""
        import agent.claude_code_session as mod
        source = open(mod.__file__).read()
        block_section = source.split("_builtin_tools_to_block")[1].split("]")[0]
        assert '"Workflow"' in block_section


class TestAskUserBridge:
    """Tests for agent/ask_user_bridge.py."""

    def test_gateway_session_detected(self):
        from agent.ask_user_bridge import detect_session_type
        with patch.dict(os.environ, {"HERMES_GATEWAY_SESSION": "1"}):
            assert detect_session_type() == "gateway"

    def test_cron_session_detected(self):
        from agent.ask_user_bridge import detect_session_type
        with patch.dict(os.environ, {"HERMES_CRON_SESSION": "1"}):
            assert detect_session_type() == "cron"

    def test_tui_session_default(self):
        from agent.ask_user_bridge import detect_session_type
        with patch.dict(os.environ, {}, clear=True):
            # Remove both env vars
            os.environ.pop("HERMES_GATEWAY_SESSION", None)
            os.environ.pop("HERMES_CRON_SESSION", None)
            assert detect_session_type() == "tui"

    def test_cron_mode_denies(self):
        from agent.ask_user_bridge import handle_ask_user_question
        with patch.dict(os.environ, {"HERMES_CRON_SESSION": "1"}):
            result = asyncio.run(handle_ask_user_question(
                {"questions": [{"question": "test?"}]}
            ))
        assert result["behavior"] == "deny"
        assert "headless" in result["message"]

    def test_single_select_translation(self):
        from agent.ask_user_bridge import handle_ask_user_question

        class MockAgent:
            def clarify_callback(self, q, choices):
                return "1"

        input_data = {
            "questions": [{
                "question": "Which format?",
                "header": "Format",
                "options": [
                    {"label": "JSON", "description": "JSON output"},
                    {"label": "YAML", "description": "YAML output"},
                ],
                "multiSelect": False,
            }]
        }
        result = asyncio.run(handle_ask_user_question(input_data, agent=MockAgent()))
        assert result["behavior"] == "allow"
        assert result["updated_input"]["answers"]["Which format?"] == "JSON"

    def test_multi_select_translation(self):
        from agent.ask_user_bridge import handle_ask_user_question

        class MockAgent:
            def clarify_callback(self, q, choices):
                return "1, 3"

        input_data = {
            "questions": [{
                "question": "Select features",
                "header": "Features",
                "options": [
                    {"label": "Auth", "description": ""},
                    {"label": "DB", "description": ""},
                    {"label": "API", "description": ""},
                ],
                "multiSelect": True,
            }]
        }
        result = asyncio.run(handle_ask_user_question(input_data, agent=MockAgent()))
        assert result["behavior"] == "allow"
        assert result["updated_input"]["answers"]["Select features"] == "Auth, API"

    def test_free_text_passthrough(self):
        from agent.ask_user_bridge import handle_ask_user_question

        class MockAgent:
            def clarify_callback(self, q, choices):
                return "my custom answer"

        input_data = {
            "questions": [{
                "question": "What?",
                "header": "Q",
                "options": [{"label": "A", "description": ""}],
                "multiSelect": False,
            }]
        }
        result = asyncio.run(handle_ask_user_question(input_data, agent=MockAgent()))
        assert result["updated_input"]["answers"]["What?"] == "my custom answer"

    def test_callback_auto_allows_other_tools(self):
        from agent.ask_user_bridge import can_use_tool_callback

        result = asyncio.run(
            can_use_tool_callback("Bash", {"command": "ls"}, None, agent=None)
        )
        assert result["behavior"] == "allow"
        assert result["updated_input"] == {"command": "ls"}


class TestSubagentProfiles:
    """Tests for agent/sdk_subagent_profiles.py."""

    def test_returns_agent_definitions(self):
        from agent.sdk_subagent_profiles import build_hermes_agent_definitions
        agents = build_hermes_agent_definitions()
        assert agents is not None
        assert "code-reviewer" in agents
        assert "researcher" in agents
        assert "general-worker" in agents

    def test_code_reviewer_is_read_only(self):
        from agent.sdk_subagent_profiles import build_hermes_agent_definitions
        agents = build_hermes_agent_definitions()
        reviewer = agents["code-reviewer"]
        assert "Read" in reviewer.tools
        assert "Edit" not in (reviewer.tools or [])
        assert "Bash" not in (reviewer.tools or [])

    def test_researcher_has_web_access(self):
        from agent.sdk_subagent_profiles import build_hermes_agent_definitions
        agents = build_hermes_agent_definitions()
        researcher = agents["researcher"]
        assert "WebSearch" in researcher.tools

    def test_agent_definitions_are_valid(self):
        from agent.sdk_subagent_profiles import build_hermes_agent_definitions
        from claude_agent_sdk import AgentDefinition
        agents = build_hermes_agent_definitions()
        for name, defn in agents.items():
            assert isinstance(defn, AgentDefinition)
            assert defn.description
            assert defn.prompt
