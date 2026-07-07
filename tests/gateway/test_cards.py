"""Unit tests for gateway.cards — InteractiveCard data model and builder."""

from gateway.cards import (
    CardActions,
    CardButton,
    CardDivider,
    CardHeader,
    CardListItem,
    CardMarkdown,
    CardNote,
    CardSelect,
    CardSelectOption,
    InteractiveCard,
)


class TestCardBuilder:
    def test_basic_card_with_header_and_markdown(self):
        card = (
            InteractiveCard.builder()
            .title("Test Card", "blue")
            .markdown("Hello **world**")
            .build()
        )
        assert card.header == CardHeader(title="Test Card", color="blue")
        assert len(card.elements) == 1
        assert isinstance(card.elements[0], CardMarkdown)
        assert card.elements[0].content == "Hello **world**"

    def test_all_element_types(self):
        card = (
            InteractiveCard.builder()
            .title("Full Card", "orange")
            .markdown("Some text")
            .divider()
            .actions([CardButton(text="Click", type="primary", value="act:1")])
            .list_item("Description", "Select", btn_value="opt:1")
            .select("Choose...", [CardSelectOption("A", "a")])
            .note("Footer note")
            .build()
        )
        assert len(card.elements) == 6
        assert isinstance(card.elements[0], CardMarkdown)
        assert isinstance(card.elements[1], CardDivider)
        assert isinstance(card.elements[2], CardActions)
        assert isinstance(card.elements[3], CardListItem)
        assert isinstance(card.elements[4], CardSelect)
        assert isinstance(card.elements[5], CardNote)

    def test_actions_equal_layout(self):
        card = (
            InteractiveCard.builder()
            .title("Approval", "orange")
            .actions_equal([
                CardButton(text="Allow", type="primary", value="perm:allow"),
                CardButton(text="Deny", type="danger", value="perm:deny"),
            ])
            .build()
        )
        actions = card.elements[0]
        assert isinstance(actions, CardActions)
        assert actions.layout == "equal_columns"
        assert len(actions.buttons) == 2

    def test_actions_row_layout(self):
        card = (
            InteractiveCard.builder()
            .title("T", "blue")
            .actions([CardButton(text="Go", value="cmd:go")])
            .build()
        )
        actions = card.elements[0]
        assert actions.layout == "row"

    def test_list_item_with_extra(self):
        card = (
            InteractiveCard.builder()
            .title("Q", "blue")
            .list_item(
                "Option A description",
                "Option A",
                btn_type="primary",
                btn_value="askq:0:1",
                extra={"label": "Option A"},
            )
            .build()
        )
        item = card.elements[0]
        assert isinstance(item, CardListItem)
        assert item.text == "Option A description"
        assert item.btn_text == "Option A"
        assert item.btn_value == "askq:0:1"
        assert item.extra == {"label": "Option A"}

    def test_button_value_prefix_convention(self):
        btn = CardButton(text="Allow", type="primary", value="clarify:req_42:3")
        parts = btn.value.split(":")
        assert parts[0] == "clarify"
        assert parts[1] == "req_42"
        assert parts[2] == "3"

    def test_button_extra_metadata(self):
        btn = CardButton(
            text="Allow",
            type="primary",
            value="perm:allow",
            extra={"label": "✅ Allowed", "color": "green"},
        )
        assert btn.extra["label"] == "✅ Allowed"
        assert btn.extra["color"] == "green"

    def test_builder_produces_independent_card(self):
        builder = InteractiveCard.builder().title("T", "blue").markdown("A")
        card1 = builder.build()
        builder.markdown("B")
        card2 = builder.build()
        assert len(card1.elements) == 1
        assert len(card2.elements) == 2

    def test_card_is_frozen(self):
        card = InteractiveCard.builder().title("T", "blue").build()
        try:
            card.header = CardHeader(title="X", color="red")  # type: ignore
            assert False, "Should raise"
        except Exception:
            pass

    def test_select_element(self):
        card = (
            InteractiveCard.builder()
            .title("Pick", "blue")
            .select(
                "Choose model",
                [
                    CardSelectOption("GPT-4", "gpt4"),
                    CardSelectOption("Claude", "claude"),
                ],
                init_value="claude",
                action_value="model:select",
            )
            .build()
        )
        sel = card.elements[0]
        assert isinstance(sel, CardSelect)
        assert sel.placeholder == "Choose model"
        assert len(sel.options) == 2
        assert sel.init_value == "claude"
        assert sel.action_value == "model:select"
