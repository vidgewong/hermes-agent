"""Unit tests for Feishu card renderer (plugins.platforms.feishu.card_renderer)."""

from gateway.cards import (
    CardButton,
    CardSelectOption,
    InteractiveCard,
)
from plugins.platforms.feishu.card_renderer import render_card_to_feishu


SESSION_KEY = "feishu:oc_abc:ou_123"


class TestRenderCardToFeishu:
    def test_basic_structure(self):
        card = InteractiveCard.builder().title("Hello", "orange").markdown("Body").build()
        result = render_card_to_feishu(card, SESSION_KEY)

        assert result["config"] == {"wide_screen_mode": True}
        assert result["header"]["title"]["content"] == "Hello"
        assert result["header"]["template"] == "orange"
        assert len(result["elements"]) == 1

    def test_markdown_element(self):
        card = InteractiveCard.builder().title("T", "blue").markdown("**bold**").build()
        result = render_card_to_feishu(card, SESSION_KEY)
        assert result["elements"][0] == {"tag": "markdown", "content": "**bold**"}

    def test_divider_element(self):
        card = InteractiveCard.builder().title("T", "blue").divider().build()
        result = render_card_to_feishu(card, SESSION_KEY)
        assert result["elements"][0] == {"tag": "hr"}

    def test_actions_row_layout(self):
        card = (
            InteractiveCard.builder()
            .title("T", "blue")
            .actions([CardButton(text="Go", type="primary", value="cmd:go")])
            .build()
        )
        result = render_card_to_feishu(card, SESSION_KEY)
        action = result["elements"][0]
        assert action["tag"] == "action"
        assert len(action["actions"]) == 1
        btn = action["actions"][0]
        assert btn["tag"] == "button"
        assert btn["text"]["content"] == "Go"
        assert btn["type"] == "primary"
        assert btn["value"]["action"] == "cmd:go"
        assert btn["value"]["session_key"] == SESSION_KEY

    def test_actions_equal_columns(self):
        card = (
            InteractiveCard.builder()
            .title("T", "blue")
            .actions_equal([
                CardButton(text="A", type="primary", value="a"),
                CardButton(text="B", type="danger", value="b"),
            ])
            .build()
        )
        result = render_card_to_feishu(card, SESSION_KEY)
        col_set = result["elements"][0]
        assert col_set["tag"] == "column_set"
        assert col_set["flex_mode"] == "bisect"
        assert len(col_set["columns"]) == 2
        assert col_set["columns"][0]["weight"] == 1
        assert col_set["columns"][1]["weight"] == 1

    def test_list_item_two_column_layout(self):
        card = (
            InteractiveCard.builder()
            .title("T", "blue")
            .list_item("Description text", "Click Me", btn_type="primary", btn_value="opt:1")
            .build()
        )
        result = render_card_to_feishu(card, SESSION_KEY)
        col_set = result["elements"][0]
        assert col_set["tag"] == "column_set"
        assert col_set["flex_mode"] == "none"
        text_col = col_set["columns"][0]
        btn_col = col_set["columns"][1]
        assert text_col["weight"] == 5
        assert text_col["elements"][0]["content"] == "Description text"
        assert btn_col["width"] == "auto"
        btn = btn_col["elements"][0]["actions"][0]
        assert btn["text"]["content"] == "Click Me"
        assert btn["value"]["action"] == "opt:1"

    def test_note_element(self):
        card = InteractiveCard.builder().title("T", "blue").note("Footer").build()
        result = render_card_to_feishu(card, SESSION_KEY)
        note = result["elements"][0]
        assert note["tag"] == "note"
        assert note["elements"][0]["content"] == "Footer"

    def test_select_element(self):
        card = (
            InteractiveCard.builder()
            .title("T", "blue")
            .select(
                "Pick one",
                [CardSelectOption("Opt A", "a"), CardSelectOption("Opt B", "b")],
                init_value="a",
                action_value="sel:model",
            )
            .build()
        )
        result = render_card_to_feishu(card, SESSION_KEY)
        action = result["elements"][0]
        assert action["tag"] == "action"
        sel = action["actions"][0]
        assert sel["tag"] == "select_static"
        assert sel["placeholder"]["content"] == "Pick one"
        assert len(sel["options"]) == 2
        assert sel["value"]["action"] == "sel:model"
        assert sel["value"]["session_key"] == SESSION_KEY

    def test_session_key_in_all_buttons(self):
        card = (
            InteractiveCard.builder()
            .title("T", "blue")
            .actions([CardButton(text="A", value="x")])
            .actions_equal([CardButton(text="B", value="y"), CardButton(text="C", value="z")])
            .list_item("D", "E", btn_value="w")
            .build()
        )
        result = render_card_to_feishu(card, SESSION_KEY)
        # Row button
        assert result["elements"][0]["actions"][0]["value"]["session_key"] == SESSION_KEY
        # Equal column buttons
        cols = result["elements"][1]["columns"]
        assert cols[0]["elements"][0]["actions"][0]["value"]["session_key"] == SESSION_KEY
        assert cols[1]["elements"][0]["actions"][0]["value"]["session_key"] == SESSION_KEY
        # List item button
        li_btn = result["elements"][2]["columns"][1]["elements"][0]["actions"][0]
        assert li_btn["value"]["session_key"] == SESSION_KEY

    def test_button_extra_preserved(self):
        card = (
            InteractiveCard.builder()
            .title("T", "blue")
            .actions([CardButton(text="A", value="x", extra={"label": "Done", "color": "green"})])
            .build()
        )
        result = render_card_to_feishu(card, SESSION_KEY)
        btn = result["elements"][0]["actions"][0]
        assert btn["value"]["extra"] == {"label": "Done", "color": "green"}
