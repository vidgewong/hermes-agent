"""Mixin for FeishuAdapter to integrate streaming progress cards.

Provides methods that bridge the gateway's step/stream callbacks into the
FeishuStreamCard state machine. The adapter hooks these at turn boundaries.

Usage in FeishuAdapter:
    - Call `_stream_card_start(chat_id, session_key)` at turn start
    - Call `_stream_card_tool_start(name)` when a tool call begins
    - Call `_stream_card_tool_end(name, ok)` when a tool call completes
    - Call `_stream_card_text(delta)` on streamed text
    - Call `_stream_card_finish(ok)` at turn end
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FeishuStreamCardMixin:
    """Mixin providing streaming progress card management for FeishuAdapter."""

    _active_stream_cards: dict  # session_key → FeishuStreamCard

    def _init_stream_card_state(self) -> None:
        """Call from __init__ to initialize stream card tracking."""
        self._active_stream_cards: dict[str, Any] = {}

    async def _stream_card_start(self, chat_id: str, session_key: str) -> None:
        """Create a new streaming progress card for this turn."""
        from plugins.platforms.feishu.stream_card import CardStatus, FeishuStreamCard

        if not getattr(self, "_client", None):
            return

        card = FeishuStreamCard(
            chat_id=chat_id,
            session_key=session_key,
        )

        token = await self._get_tenant_access_token()
        if not token:
            logger.debug("[FeishuStreamCard] No tenant token, skipping stream card")
            return

        success = await card.create(self._client, token)
        if success:
            self._active_stream_cards[session_key] = card
            logger.debug("[FeishuStreamCard] Created stream card for %s", session_key)

    async def _stream_card_text(self, session_key: str, delta: str) -> None:
        """Append streamed text to the active card."""
        card = self._active_stream_cards.get(session_key)
        if not card:
            return

        token = await self._get_tenant_access_token()
        await card.append_text(delta, self._client, token or "")

    async def _stream_card_tool_start(
        self, session_key: str, tool_name: str, input_preview: str = ""
    ) -> None:
        """Record a new tool call in the progress card."""
        from plugins.platforms.feishu.stream_card import CardStatus

        card = self._active_stream_cards.get(session_key)
        if not card:
            return

        if card.status != CardStatus.WORKING:
            card.status = CardStatus.WORKING

        card.add_tool(tool_name, input_preview=input_preview)

    async def _stream_card_tool_end(
        self,
        session_key: str,
        tool_name: str,
        ok: bool = True,
        summary: str = "",
        output_preview: str = "",
    ) -> None:
        """Update tool status in the progress card."""
        card = self._active_stream_cards.get(session_key)
        if not card:
            return

        card.update_tool(tool_name, "success" if ok else "error", summary, output_preview)

    async def _stream_card_finish(self, session_key: str, ok: bool = True) -> None:
        """Finalize the streaming card (turn complete)."""
        from plugins.platforms.feishu.stream_card import CardStatus

        card = self._active_stream_cards.pop(session_key, None)
        if not card:
            return

        status = CardStatus.DONE if ok else CardStatus.ERROR
        token = await self._get_tenant_access_token()
        await card.finish(status, self._client, token or "")

    async def _get_tenant_access_token(self) -> Optional[str]:
        """Get the current tenant access token from the lark client.

        Subclasses (FeishuAdapter) should override if they have a different
        token acquisition path.
        """
        try:
            client = getattr(self, "_client", None)
            if client and hasattr(client, "_token_manager"):
                tm = client._token_manager
                if hasattr(tm, "get_tenant_access_token"):
                    return tm.get_tenant_access_token()
            # Fallback: try raw config
            config = getattr(self, "_lark_config", None) or getattr(client, "_config", None)
            if config and hasattr(config, "app_settings"):
                # The lark SDK manages tokens internally; we may need to
                # access the internal token cache.
                pass
        except Exception as exc:
            logger.debug("[FeishuStreamCard] Token acquisition failed: %s", exc)
        return None
