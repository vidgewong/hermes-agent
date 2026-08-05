"""Hermes subagent profiles exposed as Claude Code SDK AgentDefinition entries.

These are registered in ClaudeAgentOptions.agents so the SDK's Agent tool
can spawn them. They coexist with Hermes' delegate_task (MCP tool).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_hermes_agent_definitions() -> dict[str, Any] | None:
    """Build AgentDefinition entries for Hermes subagent profiles.

    Returns a dict suitable for ClaudeAgentOptions(agents=...), or None if
    the SDK types are unavailable.
    """
    try:
        from claude_agent_sdk import AgentDefinition
    except ImportError:
        return None

    agents: dict[str, AgentDefinition] = {}

    # Core profiles — all use Hermes MCP tools (mcp__hermes-tools__*) since
    # Claude Code built-ins (Read, Grep, Bash, etc.) are blocked at the parent
    # level via disallowed_tools. Subagents inherit MCP server access.
    agents["code-reviewer"] = AgentDefinition(
        description=(
            "Expert code reviewer for quality, security, and maintainability analysis. "
            "Use for focused code review of specific files or modules."
        ),
        prompt=(
            "You are a code review specialist. Analyze code for:\n"
            "- Security vulnerabilities\n"
            "- Performance issues\n"
            "- Best practice violations\n"
            "- Maintainability concerns\n\n"
            "Be thorough but concise. Cite specific lines.\n"
            "Use the hermes-tools MCP for file access: read_file, search_files, etc."
        ),
        disallowed_tools=["mcp__hermes-tools__terminal", "mcp__hermes-tools__write_file", "mcp__hermes-tools__patch"],
        model="sonnet",
    )

    agents["researcher"] = AgentDefinition(
        description=(
            "Research agent with web and file access. Use for searching documentation, "
            "investigating APIs, finding examples, or gathering context from the web."
        ),
        prompt=(
            "You are a research specialist. Search the web and codebase to find "
            "relevant information. Synthesize findings into clear, actionable summaries. "
            "Always cite your sources.\n"
            "Use hermes-tools MCP: web_search, web_extract, read_file, search_files."
        ),
        disallowed_tools=["mcp__hermes-tools__terminal", "mcp__hermes-tools__write_file", "mcp__hermes-tools__patch"],
    )

    agents["general-worker"] = AgentDefinition(
        description=(
            "General-purpose worker with full tool access. Use for implementation tasks, "
            "file operations, running commands, and other work that needs broad capabilities."
        ),
        prompt=(
            "You are a capable software engineer. Complete the assigned task efficiently. "
            "Make minimal, focused changes. Test your work when possible."
        ),
    )

    # Derive additional agents from Hermes skills with agent metadata
    _register_skill_based_agents(agents)

    return agents if agents else None


def _register_skill_based_agents(agents: dict[str, Any]) -> None:
    """Optionally derive AgentDefinition entries from Hermes skills.

    Looks for skills that have `agent: true` or similar metadata indicating
    they function as agent roles.
    """
    try:
        from claude_agent_sdk import AgentDefinition
        from tools.skills_tool import list_skills
    except ImportError:
        return

    try:
        skills = list_skills() or []
    except Exception:
        return

    for skill in skills:
        if not isinstance(skill, dict):
            continue
        # Only convert skills explicitly marked as agents
        if not skill.get("agent"):
            continue

        name = skill.get("name", "").strip()
        if not name or name in agents:
            continue

        description = skill.get("description", "")
        prompt = skill.get("prompt", skill.get("content", ""))
        tools = skill.get("tools")

        if not description or not prompt:
            continue

        try:
            agents[name] = AgentDefinition(
                description=description,
                prompt=prompt,
                tools=tools,
            )
        except Exception as exc:
            logger.debug("Failed to register skill '%s' as agent: %s", name, exc)
