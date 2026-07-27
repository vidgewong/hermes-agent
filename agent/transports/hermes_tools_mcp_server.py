"""Hermes-tools-as-MCP server — STANDALONE MODE ONLY.

.. deprecated::
    The Claude Code SDK runtime now uses in-process MCP (agent/in_process_mcp.py)
    instead of spawning this as a subprocess. This module is retained for
    standalone/external-client use only (e.g., connecting external MCP clients
    to Hermes tools via stdio).

When running as a standalone process, this module exposes Hermes tools via
stdio MCP so external clients can call web_search, browser_*, vision, memory,
skills, etc.

Run with: python -m agent.transports.hermes_tools_mcp_server
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Tools that must NOT be exposed via MCP — everything else is auto-exposed.
#
# New Hermes tools are automatically picked up without touching this file;
# only add to this blocklist when a tool genuinely cannot work in a
# stateless MCP subprocess.
#
# memory / todo / session_search are handled separately by _build_memory_tools()
# (they need their own store instances) so they are excluded from the
# auto-dispatch loop below but still end up registered.
_BLOCKED_TOOLS: frozenset[str] = frozenset({
    # Requires a live AIAgent instance (gateway session routing,
    # _delegate_depth tracking, background result delivery).
    "delegate_task",
    # Needs the terminal environment manager tied to the AIAgent's session.
    "read_terminal",
    "close_terminal",
    # Requires desktop/GUI access — not available in an MCP subprocess.
    "computer_use",
    # Interactive UX — has no meaning inside a headless MCP process.
    "clarify",
    # Handled by _build_memory_tools() with dedicated store instances.
    "memory",
    "todo",
    "session_search",
})


def _register_tool(mcp: Any, handler: Any, name: str, description: str, params_schema: dict) -> bool:
    """Register a tool on *mcp* using the Hermes JSON schema.

    Uses FastMCP internals to inject the authoritative Hermes parameter schema
    directly, bypassing FastMCP's signature-inspection which would wrap all
    arguments inside a single 'kwargs' field for **kwargs handlers.

    Returns True on success, False if the fast-path fails (falls back to
    mcp.add_tool which uses the broken **kwargs inference).
    """
    try:
        from mcp.server.fastmcp.tools.base import Tool as _MCPTool
        from mcp.server.fastmcp.utilities.func_metadata import (
            ArgModelBase as _ArgModelBase,
            FuncMetadata as _FuncMetadata,
        )
        from pydantic import create_model as _create_model
        from pydantic.config import ConfigDict as _ConfigDict

        class _PassthroughArgModel(_ArgModelBase):
            model_config = _ConfigDict(extra="allow")

            def model_dump_one_level(self):
                return dict(self.__pydantic_extra__ or {})

        tool_obj = _MCPTool(
            fn=handler,
            name=name,
            description=description,
            parameters=params_schema,
            fn_metadata=_FuncMetadata(arg_model=_PassthroughArgModel),
            is_async=False,
            context_kwarg=None,
        )
        mcp._tool_manager._tools[name] = tool_obj
        return True
    except Exception as exc:
        logger.debug("direct Tool injection failed for %s: %s", name, exc)
        try:
            mcp.add_tool(handler, name=name, description=description)
            return True
        except Exception as exc2:
            logger.warning("failed to register tool %s: %s", name, exc2)
            return False


def _build_memory_tools(mcp: Any) -> None:
    """Register memory / todo / session_search as stateful MCP tools.

    These are _AGENT_LOOP_TOOLS in Hermes native (dispatched by the agent loop
    with live AIAgent state). Here we reconstruct the minimal dependencies each
    tool actually needs — all three are backed by files/SQLite and need no
    AIAgent instance at all.
    """
    # ── memory ──────────────────────────────────────────────────────────────
    # MemoryStore is pure file I/O on ~/.hermes/memories/MEMORY.md + USER.md.
    # One instance per MCP server process is correct: the file lock inside
    # MemoryStore serialises concurrent writes, and load_from_disk() is called
    # once at startup so the in-memory snapshot is stable.
    try:
        from tools.memory_tool import MemoryStore, memory_tool as _memory_tool_fn
        _store = MemoryStore()
        _store.load_from_disk()

        # Pull schema from the Hermes tool registry so the MCP client sees
        # the correct parameter descriptions (same fix as EXPOSED_TOOLS loop).
        try:
            from model_tools import get_tool_definitions as _gtd
            _mem_spec = next(
                (td["function"] for td in (_gtd(quiet_mode=True) or [])
                 if isinstance(td, dict) and td.get("function", {}).get("name") == "memory"),
                None,
            )
            _mem_schema = (_mem_spec or {}).get("parameters") or {"type": "object", "properties": {}}
            _mem_desc = (_mem_spec or {}).get("description") or (
                "Read or write Hermes persistent memory (MEMORY.md / USER.md). "
                "Actions: add, replace, remove, list. "
                "Target: 'memory' (agent notes) or 'user' (user profile)."
            )
        except Exception:
            _mem_schema = {"type": "object", "properties": {}}
            _mem_desc = (
                "Read or write Hermes persistent memory (MEMORY.md / USER.md). "
                "Actions: add, replace, remove, list. "
                "Target: 'memory' (agent notes) or 'user' (user profile)."
            )

        def _memory_handler(**kwargs: Any) -> str:
            try:
                return _memory_tool_fn(store=_store, **kwargs)
            except Exception as exc:
                logger.exception("memory tool raised")
                return json.dumps({"error": str(exc)})

        if _register_tool(mcp, _memory_handler, "memory", _mem_desc, _mem_schema):
            logger.info("hermes-tools MCP: registered memory tool")
        else:
            logger.warning("hermes-tools MCP: could not register memory tool")
    except Exception as exc:
        logger.warning("hermes-tools MCP: could not register memory tool: %s", exc)

    # ── todo ────────────────────────────────────────────────────────────────
    # TodoStore is in-memory within one MCP server lifetime.  Since the MCP
    # server process is long-lived (one per ClaudeCodeSession), todos persist
    # across turns in the same session — matching Hermes native behaviour.
    try:
        from tools.todo_tool import TodoStore, todo_tool as _todo_tool_fn
        _todo_store = TodoStore()

        try:
            from model_tools import get_tool_definitions as _gtd
            _todo_spec = next(
                (td["function"] for td in (_gtd(quiet_mode=True) or [])
                 if isinstance(td, dict) and td.get("function", {}).get("name") == "todo"),
                None,
            )
            _todo_schema = (_todo_spec or {}).get("parameters") or {"type": "object", "properties": {}}
            _todo_desc = (_todo_spec or {}).get("description") or (
                "Read or write the in-session task list (todos). "
                "Pass todos=[...] to write; omit to read current list. "
                "Pass merge=true to update by id instead of replacing."
            )
        except Exception:
            _todo_schema = {"type": "object", "properties": {}}
            _todo_desc = (
                "Read or write the in-session task list (todos). "
                "Pass todos=[...] to write; omit to read current list. "
                "Pass merge=true to update by id instead of replacing."
            )

        def _todo_handler(**kwargs: Any) -> str:
            try:
                return _todo_tool_fn(store=_todo_store, **kwargs)
            except Exception as exc:
                logger.exception("todo tool raised")
                return json.dumps({"error": str(exc)})

        if _register_tool(mcp, _todo_handler, "todo", _todo_desc, _todo_schema):
            logger.info("hermes-tools MCP: registered todo tool")
        else:
            logger.warning("hermes-tools MCP: could not register todo tool")
    except Exception as exc:
        logger.warning("hermes-tools MCP: could not register todo tool: %s", exc)

    # ── session_search ───────────────────────────────────────────────────────
    # session_search() already opens SessionDB itself when db=None.  No
    # agent context required — we just call through directly.
    try:
        from tools.session_search_tool import session_search as _session_search_fn

        try:
            from model_tools import get_tool_definitions as _gtd
            _ss_spec = next(
                (td["function"] for td in (_gtd(quiet_mode=True) or [])
                 if isinstance(td, dict) and td.get("function", {}).get("name") == "session_search"),
                None,
            )
            _ss_schema = (_ss_spec or {}).get("parameters") or {"type": "object", "properties": {}}
            _ss_desc = (_ss_spec or {}).get("description") or (
                "Search or browse past Hermes conversation sessions stored in "
                "the local SessionDB. Pass query= for semantic search, "
                "session_id= to read a specific session, or nothing to browse."
            )
        except Exception:
            _ss_schema = {"type": "object", "properties": {}}
            _ss_desc = (
                "Search or browse past Hermes conversation sessions stored in "
                "the local SessionDB. Pass query= for semantic search, "
                "session_id= to read a specific session, or nothing to browse."
            )

        def _session_search_handler(**kwargs: Any) -> str:
            try:
                return _session_search_fn(**kwargs)
            except Exception as exc:
                logger.exception("session_search tool raised")
                return json.dumps({"error": str(exc)})

        if _register_tool(mcp, _session_search_handler, "session_search", _ss_desc, _ss_schema):
            logger.info("hermes-tools MCP: registered session_search tool")
        else:
            logger.warning("hermes-tools MCP: could not register session_search tool")
    except Exception as exc:
        logger.warning("hermes-tools MCP: could not register session_search tool: %s", exc)


def _build_server() -> Any:
    """Create the FastMCP server with Hermes tools attached. Lazy imports
    so the module can be imported without the mcp package installed
    (we degrade to a clear error only when actually run)."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - install hint
        raise ImportError(
            f"hermes-tools MCP server requires the 'mcp' package: {exc}"
        ) from exc

    # Discover Hermes tools so dispatch works.
    from model_tools import (
        get_tool_definitions,
        handle_function_call,
    )

    mcp = FastMCP(
        "hermes-tools",
        instructions=(
            "Hermes Agent's complete tool surface. When running under the "
            "Claude Code SDK backend, ALL tool execution routes through this "
            "MCP server — including shell commands (terminal), file I/O "
            "(read_file, write_file, patch, search_files), cron scheduling "
            "(cronjob), web search/extract, browser automation, vision, image "
            "generation, persistent memory (memory), in-session task tracking "
            "(todo), past-session search (session_search), and the Hermes "
            "skill library. Do NOT use Claude Code built-in tools (Bash, Read, "
            "Write, Edit, Glob, Grep, Agent, Workflow, CronCreate, etc.) — "
            "use the Hermes equivalents provided here instead."
        ),
    )

    # Pull authoritative Hermes tool schemas for the ones we expose, so
    # MCP clients see the same parameter docs Hermes gives the model.
    all_defs = {
        td["function"]["name"]: td["function"]
        for td in (get_tool_definitions(quiet_mode=True) or [])
        if isinstance(td, dict) and td.get("type") == "function"
    }

    exposed_count = 0

    for name, spec in all_defs.items():
        if name in _BLOCKED_TOOLS:
            continue

        description = spec.get("description") or f"Hermes {name} tool"
        params_schema = spec.get("parameters") or {"type": "object", "properties": {}}

        def _make_handler(tool_name: str):
            def _dispatch(**kwargs: Any) -> str:
                try:
                    return handle_function_call(tool_name, kwargs or {})
                except Exception as exc:
                    logger.exception("tool %s raised", tool_name)
                    return json.dumps({"error": str(exc), "tool": tool_name})
            _dispatch.__name__ = tool_name
            return _dispatch

        if _register_tool(mcp, _make_handler(name), name, description, params_schema):
            exposed_count += 1

    logger.info(
        "hermes-tools MCP server registered %d stateless tools (%d blocked)",
        exposed_count,
        len([n for n in all_defs if n in _BLOCKED_TOOLS]),
    )

    # Register stateful tools (memory, todo, session_search) that own their
    # own store/db instances — no AIAgent context required.
    _build_memory_tools(mcp)

    return mcp


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for `python -m agent.transports.hermes_tools_mcp_server`."""
    argv = argv or sys.argv[1:]
    verbose = "--verbose" in argv or "-v" in argv

    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        stream=sys.stderr,  # MCP uses stdio for protocol — logs MUST go to stderr
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # tools.registry emits WARNING for every tool whose check_fn returns False
    # (missing API key, no kanban task, etc.). These are expected in the MCP
    # subprocess environment and would flood the parent process log on every
    # turn. Suppress them here; they still show in the main Hermes process.
    logging.getLogger("tools.registry").setLevel(logging.ERROR)

    # Quiet mode: keep Hermes' own banners off stdout (which is the MCP wire).
    os.environ.setdefault("HERMES_QUIET", "1")
    os.environ.setdefault("HERMES_REDACT_SECRETS", "true")

    try:
        server = _build_server()
    except ImportError as exc:
        sys.stderr.write(f"hermes-tools MCP server cannot start: {exc}\n")
        return 2

    # FastMCP runs with stdio transport by default when launched as a
    # subprocess.
    try:
        server.run()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logger.exception("hermes-tools MCP server crashed")
        sys.stderr.write(f"hermes-tools MCP server error: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
