"""Tests for unified card action routing in FeishuAdapter._on_card_action_trigger."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _make_card_action_data(value_dict):
    """Build a minimal card action data object matching Feishu SDK structure."""
    return SimpleNamespace(
        event=SimpleNamespace(
            action=SimpleNamespace(value=value_dict),
            operator=SimpleNamespace(open_id="ou_test", user_id="uid_test"),
            context=SimpleNamespace(open_chat_id="oc_test"),
        ),
    )


@pytest.fixture
def adapter():
    """Minimal FeishuAdapter for routing tests."""
    from plugins.platforms.feishu.adapter import FeishuAdapter

    a = object.__new__(FeishuAdapter)
    a._loop = MagicMock()
    a._loop.is_closed = MagicMock(return_value=False)
    a._approval_state = {1: {"session_key": "s", "chat_id": "oc_test", "message_id": "m"}}
    a._update_prompt_state = {}
    a._clarify_state = {"clr_1": {"session_key": "s", "chat_id": "oc_test", "question": "Q", "choices": ["A", "B"]}}
    a._admins = []
    a._allowed_group_users = []
    a._submit_on_loop = MagicMock(return_value=True)
    a._sender_name_cache = {}
    return a


class TestLegacyRouting:
    """Backward compat: hermes_action key still routes to approval handler."""

    def test_hermes_action_routes_to_approval(self, adapter):
        data = _make_card_action_data({"hermes_action": "approve_once", "approval_id": 1})

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse", MagicMock):
            with patch("plugins.platforms.feishu.adapter.CallBackCard", MagicMock):
                with patch.object(adapter, "_handle_approval_card_action", return_value=MagicMock()) as mock:
                    adapter._on_card_action_trigger(data)

        mock.assert_called_once()

    def test_update_prompt_action_routes_correctly(self, adapter):
        adapter._update_prompt_state = {1: {"session_key": "s", "chat_id": "oc_test"}}
        data = _make_card_action_data({"hermes_update_prompt_action": "y", "update_prompt_id": 1})

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse", MagicMock):
            with patch("plugins.platforms.feishu.adapter.CallBackCard", MagicMock):
                with patch.object(adapter, "_handle_update_prompt_card_action", return_value=MagicMock()) as mock:
                    adapter._on_card_action_trigger(data)

        mock.assert_called_once()


class TestPrefixRouting:
    """New prefix-based routing via action value string."""

    def test_clarify_prefix_routes_to_clarify_handler(self, adapter):
        data = _make_card_action_data({"action": "clarify:clr_1:1", "session_key": "s"})

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse", MagicMock):
            with patch("plugins.platforms.feishu.adapter.CallBackCard", MagicMock):
                with patch.object(adapter, "_handle_clarify_card_action", return_value=MagicMock()) as mock:
                    adapter._on_card_action_trigger(data)

        mock.assert_called_once()

    def test_perm_prefix_routes_to_approval_handler(self, adapter):
        data = _make_card_action_data({"action": "perm:approve_once", "approval_id": 1})

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse", MagicMock):
            with patch("plugins.platforms.feishu.adapter.CallBackCard", MagicMock):
                with patch.object(adapter, "_handle_approval_card_action", return_value=MagicMock()) as mock:
                    adapter._on_card_action_trigger(data)

        mock.assert_called_once()
        # Verify legacy key was injected
        call_kwargs = mock.call_args[1]
        assert call_kwargs["action_value"]["hermes_action"] == "approve_once"

    def test_stream_prefix_returns_empty_response(self, adapter):
        data = _make_card_action_data({"action": "stream:stop", "session_key": "s"})

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse") as MockResp:
            mock_resp = MagicMock()
            MockResp.return_value = mock_resp
            result = adapter._on_card_action_trigger(data)

        assert result == mock_resp

    def test_unknown_action_falls_through_to_generic(self, adapter):
        data = _make_card_action_data({"action": "unknown:something", "session_key": "s"})

        with patch("plugins.platforms.feishu.adapter.P2CardActionTriggerResponse", MagicMock):
            with patch.object(adapter, "_submit_on_loop", return_value=True) as mock_submit:
                adapter._on_card_action_trigger(data)

        # Should fall through to _handle_card_action_event via _submit_on_loop
        assert mock_submit.called
