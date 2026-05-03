from typerelay.app import TypeRelayApp


def test_app_class_is_importable() -> None:
    assert TypeRelayApp.__name__ == "TypeRelayApp"
