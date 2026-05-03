from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class KeyAction:
    kind: str
    value: str


class KeyEmitter(Protocol):
    def write_text(self, text: str, interval: float) -> None:
        ...

    def press_key(self, key: str) -> None:
        ...


class TypingCancelledError(RuntimeError):
    pass


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def build_key_actions(text: str) -> list[KeyAction]:
    actions: list[KeyAction] = []
    for char in normalize_text(text):
        if char == "\n":
            actions.append(KeyAction(kind="key", value="enter"))
        elif char == "\t":
            actions.append(KeyAction(kind="key", value="tab"))
        else:
            actions.append(KeyAction(kind="text", value=char))
    return actions


def count_effective_keys(text: str) -> int:
    return len(build_key_actions(text))


def type_actions(
    actions: list[KeyAction],
    emitter: KeyEmitter,
    *,
    interval: float,
    newline_pause: float,
    stop_requested: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    total = len(actions)
    for index, action in enumerate(actions, start=1):
        if stop_requested and stop_requested():
            raise TypingCancelledError("Typing stopped by user request.")

        if action.kind == "text":
            emitter.write_text(action.value, interval)
        elif action.kind == "key":
            emitter.press_key(action.value)
            if interval > 0:
                time.sleep(interval)
            if action.value == "enter" and newline_pause > 0:
                time.sleep(newline_pause)
        else:
            raise ValueError(f"Unsupported action kind: {action.kind}")

        if on_progress:
            on_progress(index, total)
