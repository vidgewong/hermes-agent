"""Claude Code SDK session wrapper.

Manages a persistent ClaudeSDKClient subprocess — one per AIAgent instance,
reused across turns. Architecture mirrors CodexAppServerSession.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


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
        mcp_servers: dict[str, Any] | None = None,
        max_turns: int | None = None,
        extra_env: dict[str, str] | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        on_stream_delta: Callable[[str], None] | None = None,
    ):
        self._agent = agent
        self._cwd = cwd
        self._model = model
        self._system_prompt = system_prompt
        self._allowed_tools = allowed_tools
        self._mcp_servers = mcp_servers
        self._max_turns = max_turns
        self._extra_env = extra_env or {}
        self._on_event = on_event
        self._on_stream_delta = on_stream_delta
        self._client = None
        self._session_id: str | None = None

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

        options = ClaudeAgentOptions(
            model=sdk_model,
            system_prompt=self._system_prompt,
            cwd=self._cwd,
            permission_mode="bypassPermissions",
            allowed_tools=self._allowed_tools or [
                "Bash", "Read", "Write", "Edit", "Glob", "Grep",
                "Agent", "Workflow", "WebFetch", "ToolSearch",
                "LSP", "NotebookEdit",
            ],
            mcp_servers=self._mcp_servers,
            max_turns=self._max_turns,
            include_partial_messages=True,
            include_hook_events=True,
            env=env,
            extra_args=provider_config.extra_args,
            cli_path=system_cli,
        )

        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        return self._client

    async def run_turn(self, user_input: str) -> ClaudeCodeTurnResult:
        """Run one conversational turn, consuming all events."""
        client = await self._ensure_client()
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
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                logger.debug("claude code session disconnect failed", exc_info=True)
            self._client = None
