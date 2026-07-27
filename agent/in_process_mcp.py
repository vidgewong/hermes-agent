"""In-process MCP server for the Claude Code SDK runtime.

Exposes all Hermes tools directly in the main process via the SDK's
McpSdkServerConfig API (type: "sdk"). Eliminates subprocess overhead and
enables tools that need AIAgent access (delegate_task, read_terminal, etc.).
"""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_BLOCKED_TOOLS: frozenset[str] = frozenset({
    "clarify",
    "computer_use",
})

_STATEFUL_TOOLS: frozenset[str] = frozenset({
    "memory",
    "todo",
    "session_search",
})


def build_hermes_in_process_mcp(agent) -> dict:
    """Build an in-process MCP server config exposing all Hermes tools.

    Returns an McpSdkServerConfig dict (type: "sdk") that the Claude Code SDK
    passes directly to the CLI — no subprocess spawned.

    The agent instance is captured in closures so tool handlers can access it.
    """
    from claude_agent_sdk import create_sdk_mcp_server, SdkMcpTool
    from model_tools import get_tool_definitions, handle_function_call

    all_defs = {
        td["function"]["name"]: td["function"]
        for td in (get_tool_definitions(quiet_mode=True) or [])
        if isinstance(td, dict) and td.get("type") == "function"
    }

    tools: list[SdkMcpTool] = []

    for name, spec in all_defs.items():
        if name in _BLOCKED_TOOLS or name in _STATEFUL_TOOLS:
            continue

        description = spec.get("description") or f"Hermes {name} tool"
        params_schema = spec.get("parameters") or {"type": "object", "properties": {}}

        sdk_tool = SdkMcpTool(
            name=name,
            description=description,
            input_schema=params_schema,
            handler=_make_handler(name, agent),
        )
        tools.append(sdk_tool)

    # Register stateful tools that need shared store instances.
    _register_stateful_tools(tools, agent)

    config = create_sdk_mcp_server(name="hermes-tools", tools=tools)

    logger.info(
        "in-process MCP: registered %d tools (%d blocked: %s)",
        len(tools),
        len(_BLOCKED_TOOLS),
        ", ".join(sorted(_BLOCKED_TOOLS)),
    )

    return config


def _make_handler(tool_name: str, agent):
    """Create an async handler for a tool that dispatches via handle_function_call."""
    from model_tools import handle_function_call

    async def _handler(args: dict) -> dict:
        try:
            result = handle_function_call(
                tool_name,
                args or {},
                agent=agent,
            )
        except Exception as exc:
            logger.exception("in-process MCP tool %s raised", tool_name)
            result = json.dumps({"error": str(exc), "tool": tool_name})

        return {"content": [{"type": "text", "text": result or ""}]}

    return _handler


def _register_stateful_tools(tools: list, agent) -> None:
    """Register memory, todo, session_search with shared store instances.

    Since we're in-process, these tools share the same stores that the agent
    loop uses — no need for separate per-process instances.
    """
    from claude_agent_sdk import SdkMcpTool

    # memory
    try:
        from tools.memory_tool import MemoryStore, memory_tool as _memory_tool_fn
        store = getattr(agent, "_memory_store", None)
        if store is None:
            store = MemoryStore()
            store.load_from_disk()

        _mem_schema, _mem_desc = _get_tool_schema_and_desc(
            "memory",
            "Read or write Hermes persistent memory."
        )

        async def _memory_handler(args: dict) -> dict:
            try:
                result = _memory_tool_fn(store=store, **args)
            except Exception as exc:
                logger.exception("memory tool raised")
                result = json.dumps({"error": str(exc)})
            return {"content": [{"type": "text", "text": result or ""}]}

        tools.append(SdkMcpTool(
            name="memory",
            description=_mem_desc,
            input_schema=_mem_schema,
            handler=_memory_handler,
        ))
    except Exception as exc:
        logger.warning("in-process MCP: could not register memory tool: %s", exc)

    # todo
    try:
        from tools.todo_tool import TodoStore, todo_tool as _todo_tool_fn
        todo_store = getattr(agent, "_todo_store", None)
        if todo_store is None:
            todo_store = TodoStore()

        _todo_schema, _todo_desc = _get_tool_schema_and_desc(
            "todo",
            "Read or write the in-session task list."
        )

        async def _todo_handler(args: dict) -> dict:
            try:
                result = _todo_tool_fn(store=todo_store, **args)
            except Exception as exc:
                logger.exception("todo tool raised")
                result = json.dumps({"error": str(exc)})
            return {"content": [{"type": "text", "text": result or ""}]}

        tools.append(SdkMcpTool(
            name="todo",
            description=_todo_desc,
            input_schema=_todo_schema,
            handler=_todo_handler,
        ))
    except Exception as exc:
        logger.warning("in-process MCP: could not register todo tool: %s", exc)

    # session_search
    try:
        from tools.session_search_tool import session_search as _session_search_fn

        _ss_schema, _ss_desc = _get_tool_schema_and_desc(
            "session_search",
            "Search past Hermes conversation sessions."
        )

        async def _session_search_handler(args: dict) -> dict:
            try:
                result = _session_search_fn(**args)
            except Exception as exc:
                logger.exception("session_search tool raised")
                result = json.dumps({"error": str(exc)})
            return {"content": [{"type": "text", "text": result or ""}]}

        tools.append(SdkMcpTool(
            name="session_search",
            description=_ss_desc,
            input_schema=_ss_schema,
            handler=_session_search_handler,
        ))
    except Exception as exc:
        logger.warning("in-process MCP: could not register session_search tool: %s", exc)


def _get_tool_schema_and_desc(tool_name: str, fallback_desc: str) -> tuple[dict, str]:
    """Pull authoritative schema and description from the Hermes tool registry."""
    try:
        from model_tools import get_tool_definitions
        spec = next(
            (td["function"] for td in (get_tool_definitions(quiet_mode=True) or [])
             if isinstance(td, dict) and td.get("function", {}).get("name") == tool_name),
            None,
        )
        schema = (spec or {}).get("parameters") or {"type": "object", "properties": {}}
        desc = (spec or {}).get("description") or fallback_desc
        return schema, desc
    except Exception:
        return {"type": "object", "properties": {}}, fallback_desc
