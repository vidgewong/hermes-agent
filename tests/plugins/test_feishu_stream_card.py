"""Tests for Feishu streaming progress card state machine."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.platforms.feishu.stream_card import (
    CardStatus,
    FeishuStreamCard,
    MAX_CARD_JSON_BYTES,
    MAIN_TEXT_ELEMENT_ID,
    ToolEntry,
)


class TestFeishuStreamCardBuildJson:
    def test_initial_card_has_thinking_status(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        result = card.build_card_json()

        assert result["schema"] == "2.0"
        assert result["config"]["streaming_mode"] is True
        assert result["header"]["template"] == "grey"
        assert "Thinking" in result["header"]["title"]["content"]

    def test_main_text_has_element_id(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card.text = "Hello world"
        result = card.build_card_json()

        body_elements = result["body"]["elements"]
        text_el = next(
            el for el in body_elements
            if el.get("tag") == "markdown" and el.get("element_id") == MAIN_TEXT_ELEMENT_ID
        )
        assert text_el["content"] == "Hello world"

    def test_tool_panel_shows_entries(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card._tools = [
            ToolEntry(name="web_search", status="success", summary="Found 3 results"),
            ToolEntry(name="read_file", status="running"),
        ]
        result = card.build_card_json()

        body_elements = result["body"]["elements"]
        panel = body_elements[0]
        assert panel["tag"] == "collapsible_panel"
        assert "Tools (2)" in panel["header"]["title"]["content"]
        assert len(panel["elements"]) == 2

    def test_status_colors(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")

        card.status = CardStatus.WORKING
        assert card.build_card_json()["header"]["template"] == "blue"

        card.status = CardStatus.DONE
        assert card.build_card_json()["header"]["template"] == "green"

        card.status = CardStatus.ERROR
        assert card.build_card_json()["header"]["template"] == "red"

    def test_tool_panel_limits_to_10(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card._tools = [ToolEntry(name=f"tool_{i}", status="success") for i in range(15)]
        result = card.build_card_json()

        panel = result["body"]["elements"][0]
        assert len(panel["elements"]) == 10  # Limited to last 10

    def test_simple_card_json_degraded_mode(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card.text = "Some output"
        card._tools = [ToolEntry(name="bash", status="success")]
        card.status = CardStatus.DONE

        result = card.build_simple_card_json()
        assert result["header"]["template"] == "green"
        assert "Some output" in result["elements"][0]["content"]


class TestFeishuStreamCardLifecycle:
    def test_add_and_update_tool(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card.add_tool("web_search")
        card.add_tool("read_file")

        assert len(card._tools) == 2
        assert card._tools[0].status == "running"

        card.update_tool("web_search", "success", "3 results")
        assert card._tools[0].status == "success"
        assert card._tools[0].summary == "3 results"

    def test_set_text_replaces(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card.text = "old"
        card.set_text("new full text")
        assert card.text == "new full text"

    def test_compact_tools(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card._tools = [
            ToolEntry(name=f"tool_{i}", status="success", summary="x" * 100)
            for i in range(10)
        ]
        card._compact_tools()
        assert len(card._tools) == 6
        for t in card._tools:
            assert len(t.summary) <= 43  # 40 + "..."


class TestFeishuStreamCardSizeLimit:
    def test_card_under_limit(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card.text = "Short text"
        card_json = json.dumps(card.build_card_json(), ensure_ascii=False)
        assert len(card_json.encode()) < MAX_CARD_JSON_BYTES

    def test_large_text_triggers_compaction_path(self):
        card = FeishuStreamCard(chat_id="oc_abc", session_key="s1")
        card.text = "x" * 30000
        card_json = json.dumps(card.build_card_json(), ensure_ascii=False)
        # This would exceed 28KB and trigger degradation in the create path
        assert len(card_json.encode()) > MAX_CARD_JSON_BYTES
