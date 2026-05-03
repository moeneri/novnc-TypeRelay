from typerelay.hotkeys import HotkeyRegistrationResult, resolve_hotkey_action


def test_resolve_hotkey_action_only_stops_when_running() -> None:
    assert resolve_hotkey_action(is_running=False) == "noop"
    assert resolve_hotkey_action(is_running=True) == "stop"


def test_registration_result_defaults_to_success() -> None:
    result = HotkeyRegistrationResult(ok=True, message="Global F2 ready")
    assert result.ok is True
    assert result.message == "Global F2 ready"
