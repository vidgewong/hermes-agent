"""Claude Code SDK runtime — turn runner.

Delegates an entire turn to a Claude Code SDK session (subprocess running
the Claude CLI). Architecture mirrors agent/codex_runtime.py.

Called from conversation_loop.py when agent.api_mode == "claude_code_sdk".
Returns the same dict shape as the native loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def run_claude_code_sdk_turn(
    agent,
    *,
    user_message: str,
    original_user_message: Any,
    messages: List[Dict[str, Any]],
    effective_task_id: str,
    should_review_memory: bool = False,
) -> Dict[str, Any]:
    """Claude Code SDK runtime path.

    Delegates the entire turn to a ClaudeCodeSession (wrapping the SDK client).
    Mirrors run_codex_app_server_turn() architecture.
    """
    from agent.claude_code_session import ClaudeCodeSession, ClaudeCodeTurnResult

    # Lazy session creation (one per AIAgent instance, reused across turns)
    if not hasattr(agent, "_claude_code_session") or agent._claude_code_session is None:
        from agent.runtime_cwd import resolve_agent_cwd

        cwd = getattr(agent, "session_cwd", None) or str(resolve_agent_cwd())

        if not getattr(agent, "quiet_mode", False):
            agent._vprint(f"{getattr(agent, 'log_prefix', '')}⚡ Claude Code SDK runtime active (cwd: {cwd})")

        # Bridge Claude Code events to hermes callbacks for real-time visibility.
        # Uses the same callback interfaces the native loop uses so the CLI/TUI
        # renders tool progress identically.
        _last_tool_name = []  # mutable container for closure

        def _on_event(event: dict) -> None:
            progress_callback = getattr(agent, "tool_progress_callback", None)
            _quiet = getattr(agent, "quiet_mode", False)

            if event.get("type") == "assistant":
                for block in event.get("blocks", []):
                    if block.get("type") == "tool_use":
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        if isinstance(tool_input, dict):
                            preview = _build_tool_preview(tool_name, tool_input)
                        else:
                            preview = str(tool_input)[:100]
                        # Track for tool.completed
                        _last_tool_name.clear()
                        _last_tool_name.append(tool_name)
                        # Fire tool_progress_callback — this drives the CLI TUI
                        logger.info(
                            "Claude Code SDK tool.started: %s preview=%s has_callback=%s",
                            tool_name, preview[:50], bool(progress_callback),
                        )
                        if progress_callback:
                            try:
                                progress_callback(
                                    "tool.started", tool_name, preview,
                                    tool_input if isinstance(tool_input, dict) else {},
                                )
                            except Exception:
                                logger.exception("tool_progress_callback raised")
                        # Also emit via status for non-streaming CLI
                        if not _quiet:
                            try:
                                agent._emit_status(f"🔧 {tool_name}: {preview}")
                            except Exception:
                                pass

                    elif block.get("type") == "thinking":
                        thinking_cb = getattr(agent, "thinking_callback", None)
                        if thinking_cb:
                            try:
                                thinking_cb(block.get("text", ""))
                            except Exception:
                                pass

            elif event.get("type") == "tool_result":
                content = event.get("content", "")
                is_error = event.get("is_error", False)
                # Fire tool.completed with the last tool name for TUI rendering
                last_tool = _last_tool_name[0] if _last_tool_name else ""
                if progress_callback:
                    try:
                        progress_callback(
                            "tool.completed", last_tool, None, None,
                            is_error=is_error,
                            result=content[:200] if content else None,
                        )
                    except Exception:
                        pass
                # Also emit status
                if not _quiet and content:
                    try:
                        display = content[:200]
                        if len(content) > 200:
                            display += f"... ({len(content)} chars)"
                        prefix_char = "✗" if is_error else "↳"
                        agent._emit_status(f"   {prefix_char} {display}")
                    except Exception:
                        pass

        # Bridge streaming text to hermes' stream_delta_callback.
        # Even when streaming is disabled in config, we use _emit_status
        # to show progress.
        stream_callbacks = [
            cb
            for cb in (
                getattr(agent, "stream_delta_callback", None),
                getattr(agent, "_stream_callback", None),
            )
            if cb is not None
        ]

        def _on_stream_delta(text: str) -> None:
            if stream_callbacks:
                for cb in stream_callbacks:
                    try:
                        cb(text)
                    except Exception:
                        pass

        agent._claude_code_session = ClaudeCodeSession(
            agent=agent,
            cwd=cwd,
            model=agent.model if "claude" in (agent.model or "").lower() else None,
            system_prompt=getattr(agent, "active_system_prompt", None),
            max_turns=agent.max_iterations,
            on_event=_on_event,
            on_stream_delta=_on_stream_delta if stream_callbacks else None,
        )

    # Run the turn — bridge async SDK into the synchronous conversation_loop.
    # The event loop must persist across turns because the SDK client holds
    # internal state (subprocess handles, anyio tasks) tied to the loop where
    # connect() was called. Creating a new loop per turn breaks the client.
    if not getattr(agent, "quiet_mode", False):
        _prefix = getattr(agent, "log_prefix", "")
        agent._vprint(f"{_prefix}🔄 Claude Code SDK processing turn...")

    if not hasattr(agent, "_claude_code_loop") or agent._claude_code_loop is None or agent._claude_code_loop.is_closed():
        agent._claude_code_loop = asyncio.new_event_loop()
        agent._claude_code_loop.set_exception_handler(lambda l, ctx: None)

    loop = agent._claude_code_loop
    try:
        asyncio.set_event_loop(loop)
        turn: ClaudeCodeTurnResult = loop.run_until_complete(
            agent._claude_code_session.run_turn(user_input=user_message)
        )
    except Exception as exc:
        logger.exception("claude-code-sdk turn failed")
        try:
            loop.run_until_complete(agent._claude_code_session.close())
        except Exception:
            pass
        agent._claude_code_session = None
        agent._claude_code_loop = None
        try:
            loop.close()
        except Exception:
            pass
        return {
            "final_response": f"Claude Code SDK turn failed: {exc}",
            "messages": messages,
            "api_calls": 0,
            "completed": False,
            "partial": True,
            "error": str(exc),
        }

    # Log turn completion
    if not getattr(agent, "quiet_mode", False):
        _prefix = getattr(agent, "log_prefix", "")
        _tools = f", {turn.tool_iterations} tool call(s)" if turn.tool_iterations else ""
        _cost = f", ${turn.cost_usd:.4f}" if turn.cost_usd else ""
        agent._vprint(f"{_prefix}✅ Claude Code SDK turn complete{_tools}{_cost}")

    # Splice projected messages into conversation history
    if turn.projected_messages:
        messages.extend(turn.projected_messages)

    # Append the final assistant message if present
    if turn.final_text:
        messages.append({"role": "assistant", "content": turn.final_text})

    # Token accounting
    _record_usage(agent, turn)

    # Skill review counter (same cadence as other runtimes)
    agent._iters_since_skill = (
        getattr(agent, "_iters_since_skill", 0) + turn.tool_iterations
    )

    # Background memory/skill review
    should_review_skills = False
    if (
        getattr(agent, "_skill_nudge_interval", 0) > 0
        and agent._iters_since_skill >= agent._skill_nudge_interval
        and "skill_manage" in getattr(agent, "valid_tool_names", set())
    ):
        should_review_skills = True
        agent._iters_since_skill = 0

    if (
        turn.final_text
        and not turn.interrupted
        and (should_review_memory or should_review_skills)
    ):
        try:
            agent._spawn_background_review(
                messages_snapshot=list(messages),
                review_memory=should_review_memory,
                review_skills=should_review_skills,
            )
        except Exception:
            logger.debug("background review spawn raised", exc_info=True)

    # External memory sync
    if not turn.interrupted and turn.error is None:
        try:
            agent._sync_external_memory_for_turn(
                original_user_message=original_user_message,
                final_response=turn.final_text,
                interrupted=False,
                messages=messages,
            )
        except Exception:
            logger.debug("external memory sync raised", exc_info=True)

    # Persist session
    try:
        agent._persist_session(messages, None)
    except Exception:
        logger.debug("session persist raised", exc_info=True)

    return {
        "final_response": turn.final_text,
        "messages": messages,
        "api_calls": 1,
        "completed": not turn.interrupted and turn.error is None,
        "partial": turn.interrupted or turn.error is not None,
        "error": turn.error,
        "claude_code_session_id": turn.session_id,
    }


def _record_usage(agent, turn) -> None:
    """Record token usage from Claude Code SDK turn into hermes accounting."""
    agent.session_api_calls += 1

    if turn.token_usage:
        input_tokens = turn.token_usage.get("input_tokens", 0)
        output_tokens = turn.token_usage.get("output_tokens", 0)
        cache_read_tokens = turn.token_usage.get("cache_read_tokens", 0)

        agent.session_input_tokens += input_tokens
        agent.session_output_tokens += output_tokens
        agent.session_cache_read_tokens += cache_read_tokens
        agent.session_prompt_tokens += input_tokens + cache_read_tokens
        agent.session_completion_tokens += output_tokens
        agent.session_total_tokens += input_tokens + output_tokens + cache_read_tokens

    if turn.cost_usd:
        agent.session_estimated_cost_usd += turn.cost_usd

    # Persist to session DB
    if getattr(agent, "_session_db", None) and getattr(agent, "session_id", None):
        try:
            if not getattr(agent, "_session_db_created", False):
                agent._ensure_db_session()
            agent._session_db.update_token_counts(
                agent.session_id,
                input_tokens=turn.token_usage.get("input_tokens", 0) if turn.token_usage else 0,
                output_tokens=turn.token_usage.get("output_tokens", 0) if turn.token_usage else 0,
                cache_read_tokens=turn.token_usage.get("cache_read_tokens", 0) if turn.token_usage else 0,
                estimated_cost_usd=turn.cost_usd,
                model=agent.model,
                api_call_count=1,
            )
        except Exception as exc:
            logger.debug(
                "claude-code-sdk token persistence failed (session=%s): %s",
                agent.session_id,
                exc,
            )


def _build_tool_preview(tool_name: str, tool_input: dict) -> str:
    """Build a concise preview string for a tool call."""
    if tool_name == "Bash" and "command" in tool_input:
        cmd = tool_input["command"]
        return cmd[:120] + "..." if len(cmd) > 120 else cmd
    if tool_name in ("Read", "Write", "Edit") and "file_path" in tool_input:
        return tool_input["file_path"]
    if tool_name == "Grep" and "pattern" in tool_input:
        return f"/{tool_input['pattern']}/"
    if tool_name == "Glob" and "pattern" in tool_input:
        return tool_input["pattern"]
    if tool_name == "Agent" and "prompt" in tool_input:
        prompt = tool_input["prompt"]
        return prompt[:80] + "..." if len(prompt) > 80 else prompt
    # Generic fallback
    preview = str(tool_input)
    return preview[:100] + "..." if len(preview) > 100 else preview
