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
        _last_tool_id = []  # track tool_call_id for complete callback
        _last_tool_args = []  # track args for complete callback

        def _normalize_tool_name(raw: str) -> str:
            """Strip mcp__hermes-tools__ prefix so display matches native Hermes."""
            if raw.startswith("mcp__hermes-tools__"):
                return raw[len("mcp__hermes-tools__"):]
            return raw

        def _on_event(event: dict) -> None:
            progress_callback = getattr(agent, "tool_progress_callback", None)
            start_callback = getattr(agent, "tool_start_callback", None)
            complete_callback = getattr(agent, "tool_complete_callback", None)
            _quiet = getattr(agent, "quiet_mode", False)

            if event.get("type") == "assistant":
                for block in event.get("blocks", []):
                    if block.get("type") == "tool_use":
                        tool_name = _normalize_tool_name(block.get("name", ""))
                        tool_id = block.get("id", "") or f"cc_{id(block)}"
                        tool_input = block.get("input", {})
                        if isinstance(tool_input, dict):
                            preview = _build_tool_preview(tool_name, tool_input)
                        else:
                            preview = str(tool_input)[:100]
                        _last_tool_name.clear()
                        _last_tool_name.append(tool_name)
                        _last_tool_id.clear()
                        _last_tool_id.append(tool_id)
                        _last_tool_args.clear()
                        _last_tool_args.append(tool_input if isinstance(tool_input, dict) else {})

                        # Fire tool_start_callback — the TUI gateway uses this
                        # to emit tool.start WS events (tool_progress_callback's
                        # tool.started is intentionally skipped there).
                        if start_callback:
                            try:
                                start_callback(
                                    tool_id, tool_name,
                                    tool_input if isinstance(tool_input, dict) else {},
                                )
                            except Exception:
                                logger.debug("tool_start_callback raised", exc_info=True)

                        if progress_callback:
                            try:
                                progress_callback(
                                    "tool.started", tool_name, preview,
                                    tool_input if isinstance(tool_input, dict) else {},
                                )
                            except Exception:
                                logger.exception("tool_progress_callback raised")
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
                last_tool = _last_tool_name[0] if _last_tool_name else ""
                last_id = _last_tool_id[0] if _last_tool_id else ""
                last_args = _last_tool_args[0] if _last_tool_args else {}

                # Fire tool_complete_callback — produces tool.complete WS event
                if complete_callback:
                    try:
                        complete_callback(
                            last_id, last_tool,
                            last_args,
                            content[:2000] if content else "",
                        )
                    except Exception:
                        logger.debug("tool_complete_callback raised", exc_info=True)

                if progress_callback:
                    try:
                        progress_callback(
                            "tool.completed", last_tool, None, None,
                            is_error=is_error,
                            result=content[:200] if content else None,
                        )
                    except Exception:
                        pass
                if not _quiet and content:
                    try:
                        display = content[:200]
                        if len(content) > 200:
                            display += f"... ({len(content)} chars)"
                        prefix_char = "✗" if is_error else "↳"
                        agent._emit_status(f"   {prefix_char} {display}")
                    except Exception:
                        pass

        def _on_stream_delta(text: str) -> None:
            for cb in (
                getattr(agent, "stream_delta_callback", None),
                getattr(agent, "_stream_callback", None),
            ):
                if cb is not None:
                    try:
                        cb(text)
                    except Exception:
                        pass

        # Resume a previous claude CLI session if one was persisted for this
        # Hermes session (survives gateway restarts).
        _resume_id = _load_sdk_session_id(agent)
        if _resume_id and not getattr(agent, "quiet_mode", False):
            agent._vprint(f"{getattr(agent, 'log_prefix', '')}↩️  Resuming Claude Code SDK session {_resume_id}")

        agent._claude_code_session = ClaudeCodeSession(
            agent=agent,
            cwd=cwd,
            model=agent.model if "claude" in (agent.model or "").lower() else None,
            system_prompt=getattr(agent, "_cached_system_prompt", None),
            max_turns=agent.max_iterations,
            mcp_servers=_build_hermes_tools_mcp_config(agent),
            resume=_resume_id,
            on_event=_on_event,
            on_stream_delta=_on_stream_delta,
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
        # Pass original_user_message when it's a content list (multimodal —
        # images, files) so image blocks reach the claude CLI intact.
        # user_message is always a plain string (text extracted for logging);
        # original_user_message preserves the raw platform payload.
        _turn_input = (
            original_user_message
            if isinstance(original_user_message, list)
            else user_message
        )

        async def _run_with_interrupt_watcher():
            """Run the SDK turn while watching for AIAgent.interrupt() signals."""
            session = agent._claude_code_session
            turn_task = asyncio.ensure_future(session.run_turn(user_input=_turn_input))

            async def _interrupt_watcher():
                while not turn_task.done():
                    if getattr(agent, "_interrupt_requested", False):
                        try:
                            await session.interrupt()
                        except Exception:
                            pass
                        break
                    await asyncio.sleep(0.1)

            watcher_task = asyncio.ensure_future(_interrupt_watcher())
            try:
                result = await turn_task
            finally:
                watcher_task.cancel()
                try:
                    await watcher_task
                except (asyncio.CancelledError, Exception):
                    pass
            return result

        turn: ClaudeCodeTurnResult = loop.run_until_complete(_run_with_interrupt_watcher())
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

    # Persist claude CLI session ID so it can be resumed after a gateway restart.
    if turn.session_id:
        _persist_sdk_session_id(agent, turn.session_id)

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


def _persist_sdk_session_id(agent, sdk_session_id: str) -> None:
    """Save the claude CLI session ID into the Hermes session's model_config.

    Stored as model_config._claude_code_sdk_session so it survives gateway
    restarts and can be passed as resume= on the next ClaudeCodeSession.
    """
    import json as _json
    try:
        db = getattr(agent, "_session_db", None)
        hermes_session_id = getattr(agent, "session_id", None)
        if not db or not hermes_session_id:
            return
        # Read current model_config, merge in the SDK session ID, write back.
        row = db.get_session(hermes_session_id)
        raw = (row.get("model_config") if row else None) or "{}"
        try:
            cfg = _json.loads(raw)
        except Exception:
            cfg = {}
        cfg["_claude_code_sdk_session"] = sdk_session_id
        db.update_session_meta(hermes_session_id, _json.dumps(cfg))
    except Exception as exc:
        logger.debug("Failed to persist sdk session id: %s", exc)


def _load_sdk_session_id(agent) -> str | None:
    """Return the previously persisted claude CLI session ID, if any."""
    import json as _json
    try:
        db = getattr(agent, "_session_db", None)
        hermes_session_id = getattr(agent, "session_id", None)
        if not db or not hermes_session_id:
            return None
        row = db.get_session(hermes_session_id)
        if not row:
            return None
        raw = row.get("model_config") or "{}"
        cfg = _json.loads(raw)
        return cfg.get("_claude_code_sdk_session") or None
    except Exception:
        return None


def _build_hermes_tools_mcp_config(agent=None) -> dict:
    """Build the mcp_servers config that injects Hermes tools into the Claude Code SDK session.

    Prefers the in-process MCP path (McpSdkServerConfig, type: "sdk") when
    claude-agent-sdk >= 0.2.110 is available. Falls back to spawning
    agent.transports.hermes_tools_mcp_server as a stdio subprocess.

    Returns an empty dict if neither path is available (graceful degradation).
    """
    # Try in-process MCP first (no subprocess, direct agent access).
    try:
        from agent.in_process_mcp import build_hermes_in_process_mcp
        config = build_hermes_in_process_mcp(agent)
        logger.info("using in-process MCP for hermes-tools")
        return {"hermes-tools": config}
    except ImportError as exc:
        logger.warning(
            "in-process MCP unavailable (SDK too old?), falling back to stdio: %s", exc
        )
    except Exception as exc:
        logger.warning(
            "in-process MCP setup failed, falling back to stdio: %s", exc
        )

    return _build_hermes_tools_mcp_config_stdio()


def _build_hermes_tools_mcp_config_stdio() -> dict:
    """Fallback: stdio MCP subprocess config (pre-0.2.110 path)."""
    import sys
    import os

    try:
        import mcp  # noqa: F401 — presence check only
    except ImportError:
        logger.debug("mcp package not installed; skipping hermes-tools MCP bridge")
        return {}

    hermes_root = str(_hermes_agent_root())

    return {
        "hermes-tools": {
            "type": "stdio",
            "command": sys.executable,
            "args": ["-m", "agent.transports.hermes_tools_mcp_server"],
            "env": {
                "PYTHONPATH": hermes_root,
                "HERMES_QUIET": "1",
                "HERMES_REDACT_SECRETS": "true",
                **{
                    k: os.environ[k]
                    for k in (
                        "HERMES_GATEWAY_SESSION",
                        "HERMES_INTERACTIVE",
                        "HERMES_EXEC_ASK",
                        "HERMES_CRON_SESSION",
                    )
                    if k in os.environ
                },
            },
        }
    }


def _hermes_agent_root() -> "Path":
    """Return the hermes-agent project root (parent of the agent/ package)."""
    from pathlib import Path
    return Path(__file__).resolve().parent.parent


def _build_tool_preview(tool_name: str, tool_input: dict) -> str:
    """Build a concise preview string for a tool call.

    tool_name is always the normalized (mcp__ prefix stripped) name.
    """
    # Shell execution — Bash (Claude Code built-in) or terminal (Hermes)
    if tool_name in ("Bash", "terminal") and "command" in tool_input:
        cmd = tool_input["command"]
        return cmd[:120] + "..." if len(cmd) > 120 else cmd
    # File tools — native or Hermes equivalents
    if tool_name in ("Read", "Write", "Edit", "read_file", "write_file", "patch") and "file_path" in tool_input:
        return tool_input["file_path"]
    if tool_name in ("Grep", "search_files") and "pattern" in tool_input:
        return f"/{tool_input['pattern']}/"
    if tool_name == "Glob" and "pattern" in tool_input:
        return tool_input["pattern"]
    if tool_name == "Agent" and "prompt" in tool_input:
        prompt = tool_input["prompt"]
        return prompt[:80] + "..." if len(prompt) > 80 else prompt
    # Generic fallback
    preview = str(tool_input)
    return preview[:100] + "..." if len(preview) > 100 else preview
