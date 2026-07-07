"""Feishu streaming progress card using Card Schema 2.0 + CardKit v1 API.

Provides a state machine that manages the lifecycle of a streaming progress
card during an agent turn: create → stream text → add tool entries → finish.

References cc-connect's feishuPreviewHandle + streaming patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

MAX_CARD_JSON_BYTES = 28000
STREAM_INTERVAL_MS = 1500
STREAM_MIN_DELTA_CHARS = 30
FALLBACK_PATCH_INTERVAL_MS = 3000


class CardStatus(str, Enum):
    THINKING = "thinking"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"


_STATUS_COLORS = {
    CardStatus.THINKING: "grey",
    CardStatus.WORKING: "blue",
    CardStatus.DONE: "green",
    CardStatus.ERROR: "red",
}

_STATUS_TITLES = {
    CardStatus.THINKING: "💭 Thinking...",
    CardStatus.WORKING: "⚙️ Working...",
    CardStatus.DONE: "✅ Complete",
    CardStatus.ERROR: "❌ Error",
}

MAIN_TEXT_ELEMENT_ID = "main_text"


@dataclass
class ToolEntry:
    name: str
    status: str = "running"  # "running" | "success" | "error"
    summary: str = ""
    input_preview: str = ""  # command/args preview (first ~200 chars)
    output_preview: str = ""  # tool output preview (first ~500 chars)
    index: int = 0  # sequential tool call number in this turn


@dataclass
class FeishuStreamCard:
    """State machine for a streaming progress card.

    Lifecycle:
        1. create() — POST /cardkit/v1/cards, send message
        2. append_text() / add_tool() / update_tool() — stream updates
        3. finish() — set final status, flush
    """

    chat_id: str
    session_key: str
    card_id: str | None = None
    message_id: str | None = None
    sequence: int = 0
    status: CardStatus = CardStatus.THINKING
    text: str = ""
    _last_sent_text: str = ""
    _last_flush_time: float = 0.0
    _tools: list[ToolEntry] = field(default_factory=list)
    _degraded: bool = False
    _cardkit_available: bool = True
    _flush_task: asyncio.Task | None = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Card JSON builders
    # ------------------------------------------------------------------

    def build_card_json(self) -> dict[str, Any]:
        """Build the Schema 2.0 card JSON."""
        elements: list[dict[str, Any]] = []

        # Tool calls — each rendered as a collapsible panel with command + output
        if self._tools:
            for t in self._tools[-8:]:  # Keep last 8 for size
                tool_el = self._build_tool_panel(t)
                elements.append(tool_el)

        # Main text element (streaming target)
        elements.append({
            "tag": "markdown",
            "element_id": MAIN_TEXT_ELEMENT_ID,
            "content": self.text or "...",
        })

        # Footer
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "markdown",
            "content": f"Status: {self.status.value}",
            "text_size": "notation",
        })

        return {
            "schema": "2.0",
            "config": {
                "streaming_mode": True,
                "update_multi": True,
                "enable_forward_interaction": True,
            },
            "header": {
                "template": _STATUS_COLORS[self.status],
                "title": {"tag": "plain_text", "content": _STATUS_TITLES[self.status]},
            },
            "body": {"elements": elements},
        }

    def _build_tool_panel(self, t: "ToolEntry") -> dict[str, Any]:
        """Build a collapsible panel for a single tool call (cc-connect style)."""
        icon = "🟢" if t.status == "success" else "🔴" if t.status == "error" else "⚙️"
        title = f"{icon} 工具 #{t.index}: {t.name}"

        panel_elements: list[dict[str, Any]] = []

        # Command / input block
        if t.input_preview:
            panel_elements.append({
                "tag": "markdown",
                "content": f"```\n{t.input_preview}\n```",
            })

        # Output block (only when done)
        if t.output_preview and t.status != "running":
            output_text = t.output_preview[:600]
            if len(t.output_preview) > 600:
                output_text += "\n…(truncated)"
            panel_elements.append({
                "tag": "markdown",
                "content": output_text,
            })
        elif t.status == "running":
            panel_elements.append({
                "tag": "markdown",
                "content": "_running…_",
                "text_size": "notation",
            })

        return {
            "tag": "collapsible_panel",
            "expanded": t.status == "running",  # only expand the in-progress tool
            "background_color": "grey",
            "header": {
                "title": {"tag": "plain_text", "content": title},
            },
            "border": {"color": "grey"},
            "vertical_spacing": "8px",
            "padding": "4px 8px",
            "elements": panel_elements or [{"tag": "markdown", "content": "—"}],
        }

    def build_simple_card_json(self) -> dict[str, Any]:
        """Build a degraded Schema 1.0 card (no streaming, plain update)."""
        elements: list[dict[str, Any]] = []

        # Tool entries as markdown blocks
        for t in self._tools[-6:]:
            icon = "🟢" if t.status == "success" else "🔴" if t.status == "error" else "⚙️"
            parts = [f"**{icon} 工具 #{t.index}: {t.name}**"]
            if t.input_preview:
                parts.append(f"```\n{t.input_preview}\n```")
            if t.output_preview and t.status != "running":
                parts.append(t.output_preview[:300])
            elements.append({"tag": "markdown", "content": "\n".join(parts)})
            elements.append({"tag": "hr"})

        # Main response text
        if self.text:
            elements.append({"tag": "markdown", "content": self.text})

        if not elements:
            elements.append({"tag": "markdown", "content": "..."})

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": _STATUS_TITLES[self.status]},
                "template": _STATUS_COLORS[self.status],
            },
            "elements": elements,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, client: Any, tenant_access_token: str) -> bool:
        """Create the streaming card and send it as a message.

        Returns True on success, False if CardKit is unavailable.
        """
        card_json = self.build_card_json()
        card_json_str = json.dumps(card_json, ensure_ascii=False)

        if len(card_json_str.encode()) > MAX_CARD_JSON_BYTES:
            self._degraded = True
            return await self._create_fallback(client)

        # Try CardKit v1 creation
        try:
            card_id = await self._cardkit_create(tenant_access_token, card_json_str)
            if card_id:
                self.card_id = card_id
                self.message_id = await self._send_card_message(client, card_id)
                return True
        except Exception as exc:
            logger.warning("[FeishuStreamCard] CardKit create failed, degrading: %s", exc)
            self._cardkit_available = False

        # Fallback: standard interactive card
        self._degraded = True
        return await self._create_fallback(client)

    async def append_text(self, new_text: str, client: Any = None, tenant_access_token: str = "") -> None:
        """Append text and flush if throttle allows."""
        self.text += new_text
        await self._maybe_flush(client, tenant_access_token)

    def set_text(self, full_text: str) -> None:
        """Replace text (for cases where full text is provided, not deltas)."""
        self.text = full_text

    def add_tool(self, name: str, input_preview: str = "") -> None:
        """Add a new tool call entry (status: running)."""
        idx = len(self._tools) + 1
        self._tools.append(ToolEntry(
            name=name,
            input_preview=input_preview[:300],
            index=idx,
        ))

    def update_tool(self, name: str, status: str, summary: str = "", output_preview: str = "") -> None:
        """Update the most recent matching tool entry."""
        for t in reversed(self._tools):
            if t.name == name and t.status == "running":
                t.status = status
                t.summary = summary
                t.output_preview = output_preview[:800]
                break

    async def finish(self, status: CardStatus, client: Any = None, tenant_access_token: str = "") -> None:
        """Finalize the card: set status, flush remaining text, update header."""
        self.status = status
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        await self._flush(client, tenant_access_token, force=True)

    # ------------------------------------------------------------------
    # Internal streaming mechanics
    # ------------------------------------------------------------------

    async def _maybe_flush(self, client: Any, tenant_access_token: str) -> None:
        """Flush if enough time/chars have elapsed since last flush."""
        now = time.time()
        time_delta_ms = (now - self._last_flush_time) * 1000
        char_delta = len(self.text) - len(self._last_sent_text)

        if time_delta_ms >= STREAM_INTERVAL_MS or char_delta >= STREAM_MIN_DELTA_CHARS:
            await self._flush(client, tenant_access_token)
        else:
            # Schedule a delayed flush
            if self._flush_task is None or self._flush_task.done():
                delay = (STREAM_INTERVAL_MS - time_delta_ms) / 1000
                self._flush_task = asyncio.ensure_future(
                    self._delayed_flush(delay, client, tenant_access_token)
                )

    async def _delayed_flush(self, delay: float, client: Any, tenant_access_token: str) -> None:
        await asyncio.sleep(delay)
        await self._flush(client, tenant_access_token)

    async def _flush(self, client: Any, tenant_access_token: str, force: bool = False) -> None:
        """Send the accumulated text to the card."""
        if not force and self.text == self._last_sent_text:
            return

        self._last_flush_time = time.time()
        self._last_sent_text = self.text

        if self._degraded or not self._cardkit_available:
            await self._flush_fallback(client)
            return

        if self.card_id:
            await self._cardkit_stream_text(tenant_access_token)
            # Also update the full card if tools changed or status changed
            if force:
                await self._cardkit_update_card(tenant_access_token)

    async def _cardkit_stream_text(self, tenant_access_token: str) -> None:
        """PUT /cardkit/v1/cards/{card_id}/elements/{element_id}/content"""
        if not self.card_id or not tenant_access_token:
            return

        self.sequence += 1
        url = (
            f"https://open.feishu.cn/open-apis/cardkit/v1/cards/{self.card_id}"
            f"/elements/{MAIN_TEXT_ELEMENT_ID}/content"
        )
        body = json.dumps({
            "content": json.dumps({
                "tag": "markdown",
                "element_id": MAIN_TEXT_ELEMENT_ID,
                "content": self.text or "...",
            }),
            "sequence": self.sequence,
        }, ensure_ascii=False)

        try:
            await self._http_request("PUT", url, body, tenant_access_token)
        except Exception as exc:
            logger.debug("[FeishuStreamCard] Stream text update failed: %s", exc)

    async def _cardkit_update_card(self, tenant_access_token: str) -> None:
        """Update the full card JSON (for tool panel / header changes)."""
        if not self.card_id or not tenant_access_token:
            return

        card_json = self.build_card_json()
        card_json_str = json.dumps(card_json, ensure_ascii=False)

        # Size check — degrade if over limit
        if len(card_json_str.encode()) > MAX_CARD_JSON_BYTES:
            self._compact_tools()
            card_json = self.build_card_json()
            card_json_str = json.dumps(card_json, ensure_ascii=False)
            if len(card_json_str.encode()) > MAX_CARD_JSON_BYTES:
                self._degraded = True
                return

        url = f"https://open.feishu.cn/open-apis/cardkit/v1/cards/{self.card_id}"
        body = json.dumps({"type": "card_json", "data": card_json_str}, ensure_ascii=False)

        try:
            await self._http_request("PUT", url, body, tenant_access_token)
        except Exception as exc:
            logger.debug("[FeishuStreamCard] Card update failed: %s", exc)

    async def _cardkit_create(self, tenant_access_token: str, card_json_str: str) -> str | None:
        """POST /cardkit/v1/cards — returns card_id or None."""
        url = "https://open.feishu.cn/open-apis/cardkit/v1/cards"
        body = json.dumps({"type": "card_json", "data": card_json_str}, ensure_ascii=False)

        resp = await self._http_request("POST", url, body, tenant_access_token)
        if resp and isinstance(resp, dict):
            return resp.get("data", {}).get("card_id")
        return None

    async def _send_card_message(self, client: Any, card_id: str) -> str | None:
        """Send a message with the card_id reference."""
        # Use standard IM message create with card reference
        try:
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

            body = CreateMessageRequestBody()
            body.receive_id = self.chat_id
            body.msg_type = "interactive"
            body.content = json.dumps({"type": "card", "data": {"card_id": card_id}})

            request = CreateMessageRequest.builder().receive_id_type("chat_id").request_body(body).build()
            response = client.im.v1.message.create(request)
            if response and response.code == 0 and response.data:
                return response.data.message_id
        except Exception as exc:
            logger.warning("[FeishuStreamCard] Send card message failed: %s", exc)
        return None

    async def _create_fallback(self, client: Any) -> bool:
        """Fallback: send as standard interactive card (Schema 1.0)."""
        try:
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

            card_json = self.build_simple_card_json()
            payload = json.dumps(card_json, ensure_ascii=False)

            body = CreateMessageRequestBody()
            body.receive_id = self.chat_id
            body.msg_type = "interactive"
            body.content = payload

            request = CreateMessageRequest.builder().receive_id_type("chat_id").request_body(body).build()
            response = client.im.v1.message.create(request)
            if response and response.code == 0 and response.data:
                self.message_id = response.data.message_id
                return True
        except Exception as exc:
            logger.warning("[FeishuStreamCard] Fallback card create failed: %s", exc)
        return False

    async def _flush_fallback(self, client: Any) -> None:
        """Update via PATCH (standard card update) with throttling."""
        if not client or not self.message_id:
            return

        now = time.time()
        if (now - self._last_flush_time) * 1000 < FALLBACK_PATCH_INTERVAL_MS:
            return

        try:
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import PatchMessageRequest, PatchMessageRequestBody

            card_json = self.build_simple_card_json()
            payload = json.dumps(card_json, ensure_ascii=False)

            body = PatchMessageRequestBody()
            body.content = payload

            request = PatchMessageRequest.builder().message_id(self.message_id).request_body(body).build()
            client.im.v1.message.patch(request)
        except Exception as exc:
            logger.debug("[FeishuStreamCard] Fallback patch failed: %s", exc)

    def _compact_tools(self) -> None:
        """Reduce tool entries to stay under size limit."""
        if len(self._tools) > 6:
            self._tools = self._tools[-6:]
        for t in self._tools:
            if len(t.summary) > 40:
                t.summary = t.summary[:40] + "..."

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    async def _http_request(self, method: str, url: str, body: str, token: str) -> dict | None:
        """Make an HTTP request to Feishu API (async via thread pool)."""
        import urllib.request

        def _do():
            req = urllib.request.Request(
                url,
                data=body.encode("utf-8"),
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Bearer {token}",
                },
                method=method,
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do)
