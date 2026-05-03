from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class HotkeyRegistrationResult:
    ok: bool
    message: str


def resolve_hotkey_action(*, is_running: bool) -> str:
    return "stop" if is_running else "noop"


def register_stop_hotkey(on_stop: Callable[[], None]) -> tuple[HotkeyRegistrationResult, object | None]:
    try:
        import keyboard

        handle = keyboard.add_hotkey("f2", on_stop, suppress=False)
        return HotkeyRegistrationResult(ok=True, message="Global F2 ready"), handle
    except Exception as exc:  # pragma: no cover - depends on host permissions
        return HotkeyRegistrationResult(ok=False, message=str(exc)), None


def unregister_stop_hotkey(handle: object | None) -> None:
    if handle is None:
        return
    try:
        import keyboard

        keyboard.remove_hotkey(handle)
    except Exception:  # pragma: no cover - best effort cleanup
        return
