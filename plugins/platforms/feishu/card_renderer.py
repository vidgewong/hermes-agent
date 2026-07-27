"""Render InteractiveCard IR to Feishu Schema 1.0 interactive card JSON.

Converts the platform-agnostic card model (gateway.cards) into the Feishu
Lark Open Platform interactive card format. Each button/select element
gets the session_key injected into its value dict for callback routing.
"""

from __future__ import annotations

import json
from typing import Any

from gateway.cards import (
    CardActions,
    CardDivider,
    CardListItem,
    CardMarkdown,
    CardNote,
    CardSelect,
    InteractiveCard,
)


def render_card_to_feishu(card: InteractiveCard, session_key: str) -> dict[str, Any]:
    """Convert an InteractiveCard to Feishu interactive card JSON dict."""
    elements: list[dict[str, Any]] = []
    for el in card.elements:
        rendered = _render_element(el, session_key)
        if rendered is not None:
            elements.append(rendered)

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": card.header.title},
            "template": card.header.color,
        },
        "elements": elements,
    }


def render_card_to_feishu_json(card: InteractiveCard, session_key: str) -> str:
    """Render card to JSON string ready for Feishu msg_type=interactive."""
    return json.dumps(render_card_to_feishu(card, session_key), ensure_ascii=False)


def _render_element(el: Any, session_key: str) -> dict[str, Any] | None:
    if isinstance(el, CardMarkdown):
        return {"tag": "markdown", "content": el.content}

    if isinstance(el, CardDivider):
        return {"tag": "hr"}

    if isinstance(el, CardActions):
        buttons = [_render_button(btn, session_key) for btn in el.buttons]
        if el.layout == "equal_columns":
            return _render_equal_columns_buttons(buttons)
        return {"tag": "action", "actions": buttons}

    if isinstance(el, CardListItem):
        return _render_list_item(el, session_key)

    if isinstance(el, CardSelect):
        return _render_select(el, session_key)

    if isinstance(el, CardNote):
        return {
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": el.text}],
        }

    return None


def _render_button(btn: Any, session_key: str) -> dict[str, Any]:
    value: dict[str, Any] = {"action": btn.value, "session_key": session_key}
    if btn.extra:
        value["extra"] = btn.extra
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": btn.text},
        "type": btn.type,
        "value": value,
    }


def _render_equal_columns_buttons(buttons: list[dict[str, Any]]) -> dict[str, Any]:
    """Render buttons in equal-width columns (bisect for 2, trisect for 3, etc.)."""
    flex_modes = {2: "bisect", 3: "trisect", 4: "flow"}
    flex_mode = flex_modes.get(len(buttons), "flow")

    columns = []
    for btn in buttons:
        columns.append({
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [{"tag": "action", "actions": [btn]}],
        })

    return {
        "tag": "column_set",
        "flex_mode": flex_mode,
        "columns": columns,
    }


def _render_list_item(item: CardListItem, session_key: str) -> dict[str, Any]:
    """Render a list item as a two-column layout: text (weight:5) + button (auto)."""
    from gateway.cards import CardButton

    btn = _render_button(
        CardButton(
            text=item.btn_text,
            type=item.btn_type,
            value=item.btn_value,
            extra=item.extra,
        ),
        session_key,
    )

    return {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
            {
                "tag": "column",
                "width": "weighted",
                "weight": 5,
                "vertical_align": "center",
                "elements": [
                    {"tag": "markdown", "content": item.text},
                ],
            },
            {
                "tag": "column",
                "width": "auto",
                "vertical_align": "center",
                "elements": [
                    {"tag": "action", "actions": [btn]},
                ],
            },
        ],
    }


def _render_select(sel: CardSelect, session_key: str) -> dict[str, Any]:
    """Render a static select dropdown."""
    options = [
        {"text": {"tag": "plain_text", "content": opt.text}, "value": opt.value}
        for opt in sel.options
    ]

    select_elem: dict[str, Any] = {
        "tag": "select_static",
        "placeholder": {"tag": "plain_text", "content": sel.placeholder},
        "options": options,
        "value": {"action": sel.action_value, "session_key": session_key},
    }
    if sel.init_value:
        select_elem["initial_option"] = sel.init_value

    return {"tag": "action", "actions": [select_elem]}
