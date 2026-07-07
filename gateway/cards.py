"""Platform-agnostic interactive card data model.

Provides a Card IR (intermediate representation) that can be rendered to
any platform's native card format. Inspired by cc-connect's core.Card.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class CardHeader:
    title: str
    color: str  # blue, green, red, orange, purple, grey, turquoise, etc.


@dataclass(frozen=True)
class CardMarkdown:
    content: str


@dataclass(frozen=True)
class CardDivider:
    pass


@dataclass(frozen=True)
class CardButton:
    text: str
    type: str = "default"  # "primary" | "default" | "danger"
    value: str = ""
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CardActions:
    buttons: list[CardButton]
    layout: str = "row"  # "row" | "equal_columns"


@dataclass(frozen=True)
class CardListItem:
    text: str
    btn_text: str
    btn_type: str = "default"
    btn_value: str = ""
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CardSelectOption:
    text: str
    value: str


@dataclass(frozen=True)
class CardSelect:
    placeholder: str
    options: list[CardSelectOption]
    init_value: str = ""
    action_value: str = ""


@dataclass(frozen=True)
class CardNote:
    text: str


CardElement = Union[
    CardMarkdown, CardDivider, CardActions, CardListItem, CardSelect, CardNote
]


@dataclass(frozen=True)
class InteractiveCard:
    header: CardHeader
    elements: tuple[CardElement, ...]

    @staticmethod
    def builder() -> CardBuilder:
        return CardBuilder()


class CardBuilder:
    """Fluent builder for constructing InteractiveCard instances."""

    def __init__(self) -> None:
        self._title: str = ""
        self._color: str = "blue"
        self._elements: list[CardElement] = []

    def title(self, text: str, color: str = "blue") -> CardBuilder:
        self._title = text
        self._color = color
        return self

    def markdown(self, content: str) -> CardBuilder:
        self._elements.append(CardMarkdown(content=content))
        return self

    def divider(self) -> CardBuilder:
        self._elements.append(CardDivider())
        return self

    def actions(self, buttons: list[CardButton]) -> CardBuilder:
        self._elements.append(CardActions(buttons=buttons, layout="row"))
        return self

    def actions_equal(self, buttons: list[CardButton]) -> CardBuilder:
        self._elements.append(CardActions(buttons=buttons, layout="equal_columns"))
        return self

    def list_item(
        self,
        text: str,
        btn_text: str,
        btn_type: str = "default",
        btn_value: str = "",
        extra: dict[str, str] | None = None,
    ) -> CardBuilder:
        self._elements.append(
            CardListItem(
                text=text,
                btn_text=btn_text,
                btn_type=btn_type,
                btn_value=btn_value,
                extra=extra or {},
            )
        )
        return self

    def select(
        self,
        placeholder: str,
        options: list[CardSelectOption],
        init_value: str = "",
        action_value: str = "",
    ) -> CardBuilder:
        self._elements.append(
            CardSelect(
                placeholder=placeholder,
                options=options,
                init_value=init_value,
                action_value=action_value,
            )
        )
        return self

    def note(self, text: str) -> CardBuilder:
        self._elements.append(CardNote(text=text))
        return self

    def build(self) -> InteractiveCard:
        return InteractiveCard(
            header=CardHeader(title=self._title, color=self._color),
            elements=tuple(self._elements),
        )
