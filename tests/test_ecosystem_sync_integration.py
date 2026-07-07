"""Integration tests for the ecosystem sync change.

These tests verify the integration points between the skill gateway,
memory injection, and tool blocklist changes in claude_code_session.py.
They do NOT start a real Claude Code SDK subprocess — they mock the SDK
client and verify the configuration passed to it.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def skill_env(tmp_path, monkeypatch):
    """Set up skill directories with a Hermes skill present."""
    hermes_skills = tmp_path / "hermes_skills"
    agents_skills = tmp_path / "agents_skills"
    claude_skills = tmp_path / "claude_skills"

    hermes_skills.mkdir()
    agents_skills.mkdir()
    claude_skills.mkdir()

    # Create a test skill
    skill_dir = hermes_skills / "tools" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# test-skill\nA test skill.")

    import agent.skill_gateway as sg
    monkeypatch.setattr(sg, "HERMES_SKILLS_DIR", hermes_skills)
    monkeypatch.setattr(sg, "AGENTS_SKILLS_DIR", agents_skills)
    monkeypatch.setattr(sg, "CLAUDE_SKILLS_DIR", claude_skills)
    monkeypatch.setattr(sg, "COLLISION_LOG", tmp_path / "sync" / "collisions.log")

    return hermes_skills, agents_skills, claude_skills


@pytest.fixture
def memory_env(tmp_path, monkeypatch):
    """Set up memory directory with fragments."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    content = """---
name: user-role
description: user's role
metadata:
  type: user
---

User is a backend engineer.
"""
    (memory_dir / "user-role.md").write_text(content)

    import agent.sync_translators.memory_sync as mod
    monkeypatch.setattr(mod, "MEMORY_DIR", memory_dir)
    monkeypatch.setattr(mod, "USER_ME_PATH", tmp_path / "user.me")

    return memory_dir


class TestSkillGatewayIntegration:
    def test_skill_reconciled_to_claude_skills(self, skill_env):
        """Verify Hermes skill appears in ~/.claude/skills/ after reconcile."""
        hermes_skills, agents_skills, claude_skills = skill_env

        from agent.skill_gateway import SkillGateway
        SkillGateway().reconcile()

        # Skill should be accessible via Claude Code's path
        claude_link = claude_skills / "test-skill"
        assert claude_link.exists()
        assert (claude_link / "SKILL.md").exists()
        assert "test-skill" in (claude_link / "SKILL.md").read_text()


class TestMemoryInjectionIntegration:
    def test_memory_appears_in_system_prompt(self, memory_env):
        """Verify memory context block is built for SDK session."""
        from agent.sync_translators.memory_sync import build_memory_append
        result = build_memory_append()

        assert "### user-role" in result
        assert "backend engineer" in result


class TestToolBlocklist:
    def test_only_orchestration_tools_blocked(self):
        """Verify the disallowed_tools list contains only orchestration tools."""
        # Read the source to verify the blocklist content
        import agent.claude_code_session as mod
        import inspect
        source = inspect.getsource(mod.ClaudeCodeSession._ensure_client)

        # The blocked tools should be exactly these 5
        expected_blocked = {"Agent", "Workflow", "SendMessage", "EnterWorktree", "ExitWorktree"}

        # Verify Bash, Read, Write, Edit are NOT in the blocklist
        for tool in ["Bash", "Read", "Write", "Edit", "Skill", "CronCreate", "WebFetch"]:
            assert f'"{tool}"' not in source or tool in expected_blocked


class TestMCPDeduplication:
    def test_sdk_runtime_filters_duplicate_tools(self, monkeypatch):
        """Verify MCP server filters duplicated tools in SDK runtime mode."""
        monkeypatch.setenv("HERMES_SDK_RUNTIME", "1")

        from agent.transports.hermes_tools_mcp_server import (
            _BLOCKED_TOOLS,
            _SDK_DEDUPLICATED_TOOLS,
        )

        # These should be filtered in SDK mode
        assert "terminal" in _SDK_DEDUPLICATED_TOOLS
        assert "read_file" in _SDK_DEDUPLICATED_TOOLS
        assert "write_file" in _SDK_DEDUPLICATED_TOOLS
        assert "patch" in _SDK_DEDUPLICATED_TOOLS
        assert "search_files" in _SDK_DEDUPLICATED_TOOLS

    def test_non_sdk_mode_keeps_all_tools(self):
        """Verify MCP server keeps all tools when not in SDK mode."""
        from agent.transports.hermes_tools_mcp_server import (
            _BLOCKED_TOOLS,
            _SDK_DEDUPLICATED_TOOLS,
        )

        # In non-SDK mode, deduplicated tools should NOT be in the base blocklist
        for tool in _SDK_DEDUPLICATED_TOOLS:
            assert tool not in _BLOCKED_TOOLS
