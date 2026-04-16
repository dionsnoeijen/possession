"""Routes incoming frontend messages to registered handlers."""

from typing import Any, Callable

from possession.protocols import MessageHandler


class MessageRouter:
    """Dispatches incoming messages by type.

    Handlers return either a string (forward to agent) or None (skip).
    If no handler is registered for a type, the message's 'message' field is used.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, MessageHandler | Callable[[dict], str | None]] = {}

    def register(
        self,
        msg_type: str,
        handler: MessageHandler | Callable[[dict], str | None],
    ) -> None:
        self._handlers[msg_type] = handler

    def route(self, data: dict[str, Any]) -> str | None:
        msg_type = data.get("type", "chat")
        handler = self._handlers.get(msg_type)

        if handler is None:
            return data.get("message", "") or None

        if hasattr(handler, "handle"):
            return handler.handle(data)
        return handler(data)
