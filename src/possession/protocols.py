"""Protocols (interfaces) for possession services."""

from typing import Any, AsyncIterator, Protocol


class UIEventBus(Protocol):
    """Where tools publish UI events."""

    def publish(self, event: dict[str, Any]) -> None:
        """Publish a UI event to the bus."""
        ...

    def drain(self) -> list[dict[str, Any]]:
        """Drain all pending events. Called by the session handler."""
        ...


class AgentRunner(Protocol):
    """Abstraction over an LLM agent."""

    async def run(self, message: str, session_id: str) -> AsyncIterator[Any]:
        """Run the agent with a message, streaming response chunks."""
        ...


class MessageHandler(Protocol):
    """Handles an incoming frontend message.

    Returns a string to send to the agent, or None to skip.
    """

    def handle(self, data: dict[str, Any]) -> str | None:
        ...


class WebSocketAdapter(Protocol):
    """Minimal WebSocket interface — makes sessions testable."""

    async def accept(self) -> None: ...
    async def send_json(self, data: dict[str, Any]) -> None: ...
    async def receive_json(self) -> dict[str, Any]: ...
