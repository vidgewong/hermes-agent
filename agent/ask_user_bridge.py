"""Bridge between Claude Code SDK's AskUserQuestion tool and Hermes' user interaction surfaces.

When the SDK calls AskUserQuestion, it triggers the canUseTool callback.
This module translates between the SDK's structured question format and
Hermes' clarify protocol (gateway/TUI/headless).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def detect_session_type() -> str:
    """Detect the current session type: 'gateway', 'tui', or 'cron'."""
    from utils import env_var_enabled

    if env_var_enabled("HERMES_CRON_SESSION"):
        return "cron"
    if env_var_enabled("HERMES_GATEWAY_SESSION"):
        return "gateway"
    return "tui"


async def handle_ask_user_question(
    input_data: dict[str, Any],
    agent=None,
) -> dict[str, Any]:
    """Handle an AskUserQuestion tool call from the SDK.

    Bridges to Hermes' clarify_callback (gateway or TUI) and returns
    the answer in SDK format.

    Returns:
        SDK permission result dict — either allow (with answers) or deny.
    """
    session_type = detect_session_type()

    if session_type == "cron":
        return _deny_headless()

    questions = input_data.get("questions", [])
    if not questions:
        return _deny_headless()

    callback = getattr(agent, "clarify_callback", None) if agent else None
    if callback is None:
        return _deny_headless()

    answers = {}
    for q in questions:
        question_text = q.get("question", "")
        options = q.get("options", [])
        multi_select = q.get("multiSelect", False)

        choices = [opt.get("label", "") for opt in options] if options else None

        # Format the question with header for clarity
        header = q.get("header", "")
        display_question = f"[{header}] {question_text}" if header else question_text

        try:
            user_response = callback(display_question, choices)
        except Exception as exc:
            logger.warning("clarify_callback failed for AskUserQuestion: %s", exc)
            return _deny_headless()

        answer = _parse_response(user_response, options, multi_select)
        answers[question_text] = answer

    return {
        "behavior": "allow",
        "updated_input": {
            "questions": questions,
            "answers": answers,
        },
    }


def _parse_response(
    response: str,
    options: list[dict[str, Any]],
    multi_select: bool,
) -> str:
    """Parse user response — number selection(s) or free text."""
    response = (response or "").strip()
    if not response or not options:
        return response

    if multi_select:
        # Try comma-separated numbers
        try:
            indices = [int(s.strip()) - 1 for s in response.split(",")]
            labels = [
                options[i]["label"]
                for i in indices
                if 0 <= i < len(options)
            ]
            if labels:
                return ", ".join(labels)
        except (ValueError, IndexError):
            pass
        return response

    # Single select — try number
    try:
        idx = int(response) - 1
        if 0 <= idx < len(options):
            return options[idx]["label"]
    except (ValueError, IndexError):
        pass

    return response


def _deny_headless() -> dict[str, Any]:
    """Return a deny result for headless/cron mode."""
    return {
        "behavior": "deny",
        "message": (
            "No user available in headless mode — "
            "make a reasonable decision or skip this step."
        ),
    }


async def can_use_tool_callback(
    tool_name: str,
    input_data: dict[str, Any],
    context: Any,
    agent=None,
) -> dict[str, Any]:
    """canUseTool callback for Claude Code SDK sessions.

    Routes AskUserQuestion to the Hermes bridge. All other tools are
    auto-allowed (Hermes handles its own guardrails via in-process MCP).
    """
    if tool_name == "AskUserQuestion":
        return await handle_ask_user_question(input_data, agent=agent)

    # Auto-allow everything else
    return {"behavior": "allow", "updated_input": input_data}
