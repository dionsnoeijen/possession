"""Tests for MessageRouter."""

from possession.services.message_router import MessageRouter


def test_default_passes_message_field():
    router = MessageRouter()
    assert router.route({"message": "hi"}) == "hi"


def test_default_returns_none_when_no_message():
    router = MessageRouter()
    assert router.route({"type": "unknown"}) is None


def test_registered_handler_is_called():
    router = MessageRouter()
    router.register("navigate", lambda data: f"went to {data['view']}")

    result = router.route({"type": "navigate", "view": "contacts"})

    assert result == "went to contacts"


def test_handler_can_return_none():
    router = MessageRouter()
    router.register("ignore_me", lambda data: None)

    assert router.route({"type": "ignore_me"}) is None


def test_handler_class_with_handle_method():
    class MyHandler:
        def handle(self, data):
            return "handled"

    router = MessageRouter()
    router.register("custom", MyHandler())

    assert router.route({"type": "custom"}) == "handled"
