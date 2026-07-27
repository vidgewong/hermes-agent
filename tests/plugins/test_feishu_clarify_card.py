"""Integration tests for Feishu clarify interactive card flow."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateway.cards import InteractiveCard


class TestSendClarify:
    """Test send_clarify override in FeishuAdapter."""

    @pytest.fixture
    def adapter(self):
        """Minimal FeishuAdapter-like object with the send_clarify method."""
        from plugins.platforms.feishu.adapter import FeishuAdapter

        # Create a minimal adapter without full init
        adapter = object.__new__(FeishuAdapter)
        adapter._client = MagicMock()
        adapter._clarify_state = {}
        adapter._feishu_send_with_retry = AsyncMock(
            return_value=MagicMock(code=0, data=MagicMock(message_id="msg_001"))
        )
        adapter._finalize_send_result = MagicMock(
            return_value=MagicMock(success=True, message_id="msg_001")
        )
        return adapter

    @pytest.mark.asyncio
    async def test_single_select_sends_interactive_card(self, adapter):
        with patch("tools.clarify_gateway.mark_awaiting_text") as mock_mark:
            result = await adapter.send_clarify(
                chat_id="oc_abc",
                question="Which framework?",
                choices=["React", "Vue", "Svelte"],
                clarify_id="clr_001",
                session_key="feishu:oc_abc:ou_123",
            )

        assert result.success
        mock_mark.assert_called_once_with("clr_001")

        # Verify card was sent as interactive
        call_args = adapter._feishu_send_with_retry.call_args
        assert call_args.kwargs["msg_type"] == "interactive"

        # Verify state stored
        assert "clr_001" in adapter._clarify_state
        state = adapter._clarify_state["clr_001"]
        assert state["session_key"] == "feishu:oc_abc:ou_123"
        assert state["choices"] == ["React", "Vue", "Svelte"]

        # Verify JSON contains buttons with clarify: prefix
        import json
        payload = json.loads(call_args.kwargs["payload"])
        assert payload["header"]["template"] == "blue"
        # Should have markdown + 3 list items + note = 5 elements
        assert len(payload["elements"]) == 5

    @pytest.mark.asyncio
    async def test_open_ended_sends_card_without_buttons(self, adapter):
        with patch("tools.clarify_gateway.mark_awaiting_text") as mock_mark:
            result = await adapter.send_clarify(
                chat_id="oc_abc",
                question="What would you like to name it?",
                choices=None,
                clarify_id="clr_002",
                session_key="feishu:oc_abc:ou_123",
            )

        assert result.success
        mock_mark.assert_called_once_with("clr_002")

        import json
        call_args = adapter._feishu_send_with_retry.call_args
        payload = json.loads(call_args.kwargs["payload"])
        # Should have markdown + note = 2 elements (no list items)
        assert len(payload["elements"]) == 2
        assert payload["elements"][1]["tag"] == "note"


class TestClarifyCardAction:
    """Test _handle_clarify_card_action callback handling."""

    def test_resolves_clarify_on_valid_click(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter

        adapter = object.__new__(FeishuAdapter)
        adapter._clarify_state = {
            "clr_001": {
                "session_key": "feishu:oc_abc:ou_123",
                "chat_id": "oc_abc",
                "question": "Which?",
                "choices": ["React", "Vue"],
            }
        }
        adapter._admins = []
        adapter._allowed_group_users = []
        adapter._submit_on_loop = MagicMock(return_value=True)

        event = SimpleNamespace(
            operator=SimpleNamespace(open_id="ou_123", user_id="uid_1"),
        )
        action_value = {
            "action": "clarify:clr_001:1",
            "session_key": "feishu:oc_abc:ou_123",
        }

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse", MagicMock):
            with patch("plugins.platforms.feishu.adapter.CallBackCard", MagicMock):
                response = adapter._handle_clarify_card_action(
                    event=event, action_value=action_value, loop=MagicMock()
                )

        # State should be consumed
        assert "clr_001" not in adapter._clarify_state
        # Submit should have been called (to resolve async)
        assert adapter._submit_on_loop.called

    def test_rejects_unauthorized_operator(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter

        adapter = object.__new__(FeishuAdapter)
        adapter._clarify_state = {
            "clr_001": {
                "session_key": "feishu:oc_abc:ou_123",
                "chat_id": "oc_abc",
                "question": "Which?",
                "choices": ["A", "B"],
            }
        }
        # Restrict to specific admin
        adapter._admins = ["ou_admin"]
        adapter._allowed_group_users = []

        event = SimpleNamespace(
            operator=SimpleNamespace(open_id="ou_intruder", user_id="uid_bad"),
        )
        action_value = {"action": "clarify:clr_001:1", "session_key": "s"}

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse") as MockResp:
            mock_resp_instance = MagicMock()
            MockResp.return_value = mock_resp_instance
            response = adapter._handle_clarify_card_action(
                event=event, action_value=action_value, loop=MagicMock()
            )

        # State should NOT be consumed
        assert "clr_001" in adapter._clarify_state

    def test_build_resolved_clarify_card_format(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter

        card = FeishuAdapter._build_resolved_clarify_card(
            question="Which framework?",
            answer="React",
        )
        assert card["header"]["template"] == "green"
        assert "已选择" in card["header"]["title"]["content"]
        assert "React" in card["elements"][0]["content"]
        assert "Which framework?" in card["elements"][0]["content"]
