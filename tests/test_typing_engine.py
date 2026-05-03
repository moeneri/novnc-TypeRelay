from dataclasses import dataclass

import pytest

from typerelay.typing_engine import (
    KeyAction,
    TypingCancelledError,
    build_key_actions,
    count_effective_keys,
    normalize_text,
    type_actions,
)


@dataclass
class FakeEmitter:
    events: list[tuple[str, str]]

    def write_text(self, text: str, interval: float) -> None:
        self.events.append(("text", text))

    def press_key(self, key: str) -> None:
        self.events.append(("key", key))


def test_normalize_text_collapses_windows_newlines() -> None:
    assert normalize_text("a\r\nb\rc") == "a\nb\nc"


def test_build_key_actions_maps_newline_and_tab() -> None:
    assert build_key_actions("ab\n\tc") == [
        KeyAction(kind="text", value="a"),
        KeyAction(kind="text", value="b"),
        KeyAction(kind="key", value="enter"),
        KeyAction(kind="key", value="tab"),
        KeyAction(kind="text", value="c"),
    ]


def test_count_effective_keys_counts_text_and_special_actions() -> None:
    assert count_effective_keys("a\nb\tc") == 5


def test_type_actions_raises_cancelled_when_stop_requested() -> None:
    emitter = FakeEmitter(events=[])

    with pytest.raises(TypingCancelledError):
        type_actions(
            build_key_actions("abc"),
            emitter,
            interval=0.0,
            newline_pause=0.0,
            stop_requested=lambda: True,
        )


def test_type_actions_sends_expected_sequence() -> None:
    emitter = FakeEmitter(events=[])

    type_actions(
        build_key_actions("a\n\tb"),
        emitter,
        interval=0.0,
        newline_pause=0.0,
    )

    assert emitter.events == [
        ("text", "a"),
        ("key", "enter"),
        ("key", "tab"),
        ("text", "b"),
    ]
