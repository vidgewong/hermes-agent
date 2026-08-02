"""Claude Code SDK session wrapper.

Manages a persistent ClaudeSDKClient subprocess — one per AIAgent instance,
reused across turns. Architecture mirrors CodexAppServerSession.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def _resolve_claude_home() -> Path:
    """Resolve the .claude config directory.

    Checks CLAUDE_HOME env var first, then falls back to ~/.claude.
    In container environments HOME may not match where .claude actually lives.
    """
    env_home = os.environ.get("CLAUDE_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".claude"


def _resolve_enabled_plugins(specialist_id: str | None = None) -> list[dict[str, str]]:
    """Resolve installed plugin paths for the SDK plugins option.

    Loads all installed plugins from installed_plugins.json (no settings.json
    enabledPlugins gate — in container/agent contexts all installed plugins
    are considered enabled). Remaps installPath from the original host path
    to the actual .claude directory in the current environment.

    When specialist_id is set, returns an empty list — specialist sessions
    operate without plugins to avoid polluting their isolated context.

    Returns a list of SdkPluginConfig dicts: [{"type": "local", "path": "..."}]
    """
    if specialist_id:
        return []

    claude_home = _resolve_claude_home()
    installed_path = claude_home / "plugins" / "installed_plugins.json"

    if not installed_path.exists():
        return []

    try:
        installed = json.loads(installed_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    installed_plugins = installed.get("plugins", {})
    plugins_dir = claude_home / "plugins"

    result = []
    for _plugin_key, installs in installed_plugins.items():
        if not installs:
            continue
        install_info = installs[0] if isinstance(installs, list) else installs
        install_path = install_info.get("installPath", "")
        if not install_path:
            continue

        # Remap: the recorded path may reference the original host's home.
        # Extract the relative portion after ".claude/plugins/" and resolve
        # it against the actual plugins directory in this environment.
        marker = ".claude/plugins/"
        idx = install_path.find(marker)
        if idx != -1:
            relative = install_path[idx + len(marker):]
            resolved = plugins_dir / relative
        else:
            resolved = Path(install_path)

        if resolved.is_dir():
            result.append({"type": "local", "path": str(resolved)})

    return result



@dataclass
class ClaudeCodeTurnResult:
    """Hermes-normalized result from one Claude Code SDK turn."""

    final_text: str | None = None
    projected_messages: list[dict[str, Any]] = field(default_factory=list)
    tool_iterations: int = 0
    token_usage: dict[str, int] | None = None
    cost_usd: float | None = None
    duration_ms: float | None = None
    session_id: str | None = None
    interrupted: bool = False
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class ClaudeCodeSession:
    """Wraps a persistent ClaudeSDKClient session.

    One instance per AIAgent, reused across turns. The SDK manages its own
    subprocess lifecycle (claude CLI node process).
    """

    def __init__(
        self,
        *,
        agent,
        cwd: str,
        model: str | None = None,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        mcp_servers: dict[str, Any] | Any | None = None,
        max_turns: int | None = None,
        extra_env: dict[str, str] | None = None,
        resume: str | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        on_stream_delta: Callable[[str], None] | None = None,
        specialist_id: str | None = None,
    ):
        self._agent = agent
        self._model = model
        self._system_prompt = system_prompt
        self._allowed_tools = allowed_tools
        self._mcp_servers = mcp_servers
        self._max_turns = max_turns
        self._extra_env = extra_env or {}
        self._resume = resume
        self._on_event = on_event
        self._on_stream_delta = on_stream_delta
        self._specialist_id = specialist_id
        self._client = None
        self._session_id: str | None = None

        # Specialist sessions use a dedicated cwd so Claude Code auto-discovers
        # the specialist-specific CLAUDE.md rather than the master's.
        if specialist_id:
            from hermes_constants import get_hermes_home
            specialist_dir = get_hermes_home() / ".claude-code" / "specialists" / specialist_id
            if specialist_dir.exists() and (specialist_dir / "CLAUDE.md").exists():
                self._cwd = str(specialist_dir)
            else:
                # Fallback: no specialist CLAUDE.md deployed yet, use normal cwd
                self._cwd = cwd
        else:
            self._cwd = cwd

    async def _ensure_client(self):
        """Lazily create and connect the SDK client."""
        if self._client is not None:
            return self._client

        # Auto-install SDK if missing (hermes lazy-deps pattern)
        try:
            from tools.lazy_deps import ensure as _lazy_ensure
            _lazy_ensure("runtime.claude_code_sdk", prompt=False)
        except ImportError:
            pass
        except Exception:
            pass

        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        except ImportError:
            raise RuntimeError(
                "claude-agent-sdk is not installed. "
                "Install with: pip install claude-agent-sdk"
            )

        from agent.claude_code_provider_bridge import resolve_provider_for_sdk

        provider_config = resolve_provider_for_sdk(self._agent)
        if not provider_config.compatible:
            raise RuntimeError(provider_config.fallback_reason)

        env = {
            **provider_config.env,
            **self._extra_env,
        }

        # Prefer the system-installed claude CLI over the SDK-bundled one.
        # The bundled version may not support enterprise auth (bearer tokens,
        # custom Bedrock endpoints). Fall back to bundled if not found.
        import shutil
        system_cli = shutil.which("claude")

        # For Bedrock/Vertex: don't pass --model flag — rely on ANTHROPIC_MODEL
        # env var instead. The --model flag may not accept the exact model string
        # required by the corporate endpoint (e.g. "claude-sonnet-4.6" vs
        # "claude-sonnet-4-5"). When ANTHROPIC_MODEL is set in env, the CLI
        # picks it up automatically.
        sdk_model = None
        if "ANTHROPIC_MODEL" not in env:
            sdk_model = provider_config.model or self._model

        # SkillGateway (Hermes skills → ~/.claude/skills/) is intentionally
        # NOT run. ~/.claude/ skills are managed independently by Claude Code.

        if not self._specialist_id:
            # Master DM: sync Hermes memory (USER.md/MEMORY.md) into ~/.claude/CLAUDE.md
            try:
                from agent.sync_translators.memory_sync import sync_hermes_to_claude, MemoryWatcher
                sync_hermes_to_claude()
                self._memory_watcher = MemoryWatcher()
                self._memory_watcher.start()
            except Exception:
                logger.debug("memory sync failed", exc_info=True)
        else:
            # Specialist sessions: strip any residual Hermes memory markers
            # from the global ~/.claude/CLAUDE.md so they don't bleed in.
            try:
                from agent.sync_translators.memory_sync import _remove_section
                _remove_section()
            except Exception:
                logger.debug("specialist: failed to clean global CLAUDE.md", exc_info=True)

        # Use Claude Code's default system prompt as the base and append
        # Hermes' platform instructions (MEDIA: tags, messaging conventions,
        # skills index, memory, etc.) on top. This preserves Claude Code's
        # built-in tool behaviour while adding Hermes-specific guidance.
        # Passing a raw string as system_prompt would replace the default
        # entirely, causing Claude to lose file-delivery conventions.
        _sdk_delegation_guidance = (
            "\n\n## Delegation & User Interaction\n"
            "You have TWO delegation mechanisms:\n"
            "- **Agent tool** (built-in): for focused subtasks with context isolation and "
            "tool restrictions. Subagents run independently and return a summary. Best for "
            "code review, research, analysis, and parallel work.\n"
            "- **delegate_task** (MCP tool): for Hermes-aware work that needs gateway "
            "session routing, depth tracking, background result delivery, or access to "
            "Hermes-specific state. Best for long-running background tasks and orchestrated workflows.\n\n"
            "For **AskUserQuestion**: only ask when the decision genuinely requires user "
            "input (ambiguous requirements, multiple valid approaches, destructive actions). "
            "For routine decisions, proceed autonomously."
        )
        _combined_prompt = (
            (self._system_prompt or "") + _sdk_delegation_guidance
        )
        _sdk_system_prompt = (
            {"type": "preset", "preset": "claude_code", "append": _combined_prompt}
            if _combined_prompt.strip()
            else None
        )

        # Block all Claude Code built-in tools so every tool call routes through
        # the hermes-tools MCP server instead. Claude Code's --allowedTools does
        # NOT filter MCP tools (they are always accessible when an MCP server is
        # connected), but --disallowedTools DOES block built-ins. We use this to
        # push shell, file, cron, and web operations through Hermes' own layer
        # (approval guards, secret redaction, rate limiting, cronjob scheduler).
        # MCP tools from the hermes-tools server are implicitly allowed because
        # they are not built-ins and therefore not subject to disallowedTools.
        _builtin_tools_to_block = [
            # Shell / file — replaced by terminal, read_file, write_file, patch, search_files
            "Bash", "Read", "Write", "Edit", "Glob", "Grep",
            # Workflow — Hermes owns orchestration; stays blocked intentionally
            "Workflow",
            # Web — replaced by hermes web_search / web_extract
            "WebFetch",
            # Deferred built-ins — all replaced by hermes equivalents
            "CronCreate", "CronDelete", "CronList", "ScheduleWakeup",
            "TaskCreate", "TaskGet", "TaskList", "TaskOutput", "TaskStop", "TaskUpdate",
            "SendMessage", "EnterWorktree", "ExitWorktree",
            "LSP", "NotebookEdit", "ToolSearch",
            # Other built-ins not needed
            "ReportFindings",
            # NOT blocked (enabled):
            # - AskUserQuestion: bridged via canUseTool callback to Hermes gateway/TUI
            # - Agent: SDK native subagents, coexists with delegate_task
            # - Monitor: background process watching, runs within CLI subprocess
            # - Skill: needed for plugin-provided skills; Hermes skills are also
            #   synced to ~/.agents/skills/ via SkillGateway so both coexist.
        ]
        # Build canUseTool callback that bridges AskUserQuestion to Hermes
        from agent.ask_user_bridge import can_use_tool_callback as _ask_user_cb

        _agent_ref = self._agent

        async def _can_use_tool(tool_name, input_data, context):
            return await _ask_user_cb(tool_name, input_data, context, agent=_agent_ref)

        # Build subagent definitions from Hermes profiles
        try:
            from agent.sdk_subagent_profiles import build_hermes_agent_definitions
            _agents = build_hermes_agent_definitions()
        except Exception:
            logger.debug("sdk subagent profiles unavailable", exc_info=True)
            _agents = None

        # Resolve Claude Code plugins (specialist sessions get none)
        _plugins = _resolve_enabled_plugins(self._specialist_id)
        if _plugins:
            logger.debug("loading %d Claude Code plugin(s)", len(_plugins))

        options = ClaudeAgentOptions(
            model=sdk_model,
            system_prompt=_sdk_system_prompt,
            cwd=self._cwd,
            permission_mode="bypassPermissions",
            allowed_tools=[*(self._allowed_tools or []), "Agent", "Monitor", "Skill"],
            disallowed_tools=_builtin_tools_to_block,
            mcp_servers=self._mcp_servers,
            max_turns=self._max_turns,
            resume=self._resume,
            can_use_tool=_can_use_tool,
            agents=_agents,
            plugins=_plugins,
            include_partial_messages=True,
            include_hook_events=True,
            env=env,
            extra_args=provider_config.extra_args,
            cli_path=system_cli,
            # Default 1MB is too small when MCP tool results contain large
            # payloads (vision analysis errors, file contents, etc.).
            max_buffer_size=16 * 1024 * 1024,  # 16MB
        )

        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        return self._client

    async def run_turn(self, user_input: str | list) -> ClaudeCodeTurnResult:
        """Run one conversational turn, consuming all events."""
        client = await self._ensure_client()

        # Multimodal content (images, files) arrives as a list of content blocks.
        # The SDK client.query() accepts AsyncIterable[dict] for this case —
        # wrap the list in a single message dict and stream it.
        if isinstance(user_input, list):
            async def _multimodal_iter():
                yield {
                    "type": "user",
                    "message": {"role": "user", "content": user_input},
                    "parent_tool_use_id": None,
                    "session_id": "default",
                }
            await client.query(_multimodal_iter())
        else:
            await client.query(user_input)

        projected_messages: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        final_text: str | None = None
        tool_iterations = 0
        token_usage: dict[str, int] | None = None
        cost_usd: float | None = None
        duration_ms: float | None = None
        error: str | None = None
        text_parts: list[str] = []

        try:
            from claude_agent_sdk.types import (
                AssistantMessage,
                UserMessage,
                SystemMessage,
                ResultMessage,
                StreamEvent,
                RateLimitEvent,
            )
        except ImportError:
            raise RuntimeError("claude-agent-sdk types not available")

        async for message in client.receive_response():
            event = self._normalize_event(message)
            if event:
                events.append(event)
                if self._on_event:
                    try:
                        self._on_event(event)
                    except Exception:
                        logger.debug("on_event callback raised", exc_info=True)

            if isinstance(message, AssistantMessage):
                self._process_assistant_message(
                    message, text_parts, projected_messages
                )
                from claude_agent_sdk.types import ToolUseBlock as _TUB
                for block in message.content or []:
                    if isinstance(block, _TUB):
                        tool_iterations += 1

            elif isinstance(message, UserMessage):
                self._process_user_message(message, projected_messages)
                # Emit tool result as event for real-time display
                from claude_agent_sdk.types import ToolResultBlock as _TRB
                for block in message.content or []:
                    if isinstance(block, _TRB):
                        content = getattr(block, "content", "")
                        if isinstance(content, list):
                            content = " ".join(
                                getattr(c, "text", str(c))[:100] for c in content
                            )
                        elif not isinstance(content, str):
                            content = str(content)
                        tool_result_event = {
                            "type": "tool_result",
                            "tool_use_id": getattr(block, "tool_use_id", ""),
                            "content": content[:500],
                            "is_error": getattr(block, "is_error", False),
                        }
                        events.append(tool_result_event)
                        if self._on_event:
                            try:
                                self._on_event(tool_result_event)
                            except Exception:
                                pass

            elif isinstance(message, ResultMessage):
                final_text = "".join(text_parts) if text_parts else None
                self._session_id = getattr(message, "session_id", None)
                token_usage = self._extract_usage(message)
                cost_usd = getattr(message, "cost_usd", None)
                duration_ms = getattr(message, "duration_ms", None)
                if getattr(message, "is_error", False):
                    error = str(getattr(message, "error", "Unknown error"))

            elif isinstance(message, StreamEvent):
                pass

        return ClaudeCodeTurnResult(
            final_text=final_text,
            projected_messages=projected_messages,
            tool_iterations=tool_iterations,
            token_usage=token_usage,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            session_id=self._session_id,
            interrupted=False,
            error=error,
            events=events,
        )

    def _process_assistant_message(
        self,
        message,
        text_parts: list[str],
        projected_messages: list[dict[str, Any]],
    ) -> None:
        """Process an AssistantMessage: extract text, tool_use blocks."""
        from claude_agent_sdk.types import TextBlock, ToolUseBlock

        for block in message.content or []:
            if isinstance(block, TextBlock):
                text = block.text or ""
                if text:
                    text_parts.append(text)
                    if self._on_stream_delta:
                        try:
                            self._on_stream_delta(text)
                        except Exception:
                            pass

            elif isinstance(block, ToolUseBlock):
                tool_input = getattr(block, "input", {})
                if not isinstance(tool_input, str):
                    tool_input = json.dumps(tool_input)
                projected_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": getattr(block, "id", ""),
                        "type": "function",
                        "function": {
                            "name": getattr(block, "name", ""),
                            "arguments": tool_input,
                        },
                    }],
                })

    def _process_user_message(
        self,
        message,
        projected_messages: list[dict[str, Any]],
    ) -> None:
        """Process a UserMessage: extract tool results."""
        from claude_agent_sdk.types import ToolResultBlock

        for block in message.content or []:
            if isinstance(block, ToolResultBlock):
                content = getattr(block, "content", "")
                if not isinstance(content, str):
                    content = str(content)
                projected_messages.append({
                    "role": "tool",
                    "tool_call_id": getattr(block, "tool_use_id", ""),
                    "content": content,
                })

    def _extract_usage(self, result_message) -> dict[str, int] | None:
        """Extract token usage from a ResultMessage."""
        usage = getattr(result_message, "usage", None)
        if usage is None:
            return None
        return {
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        }

    def _normalize_event(self, message) -> dict[str, Any] | None:
        """Convert SDK message to hermes-internal event dict for logging/gateway."""
        try:
            from claude_agent_sdk.types import (
                AssistantMessage,
                SystemMessage,
                ResultMessage,
                RateLimitEvent,
                TextBlock,
                ThinkingBlock,
                ToolUseBlock,
            )
        except ImportError:
            return None

        if isinstance(message, AssistantMessage):
            blocks = []
            for block in message.content or []:
                if isinstance(block, TextBlock):
                    blocks.append({"type": "text", "text": block.text or ""})
                elif isinstance(block, ThinkingBlock):
                    blocks.append({"type": "thinking", "text": getattr(block, "thinking", "") or ""})
                elif isinstance(block, ToolUseBlock):
                    blocks.append({
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}),
                    })
            if blocks:
                return {"type": "assistant", "blocks": blocks}

        elif isinstance(message, SystemMessage):
            return {
                "type": "system",
                "subtype": getattr(message, "subtype", "unknown"),
                "data": getattr(message, "data", None),
            }

        elif isinstance(message, ResultMessage):
            return {
                "type": "result",
                "session_id": getattr(message, "session_id", None),
                "cost_usd": getattr(message, "cost_usd", None),
                "duration_ms": getattr(message, "duration_ms", None),
                "is_error": getattr(message, "is_error", False),
            }

        elif isinstance(message, RateLimitEvent):
            return {"type": "rate_limit"}

        return None

    async def interrupt(self):
        """Interrupt the current turn."""
        if self._client:
            await self._client.interrupt()

    async def close(self):
        """Disconnect and clean up."""
        if hasattr(self, "_memory_watcher") and self._memory_watcher:
            try:
                self._memory_watcher.stop()
            except Exception:
                pass
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                logger.debug("claude code session disconnect failed", exc_info=True)
            self._client = None
