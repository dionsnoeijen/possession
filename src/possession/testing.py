"""Testing utilities — fakes for protocols."""

from dataclasses import dataclass, field
from typing import Any, AsyncIterator


class FakeEventBus:
    """In-memory event bus with assertion helpers."""

    def __init__(self, preload: list[dict] | None = None) -> None:
        self.events: list[dict] = list(preload or [])
        self._draining = list(self.events)

    def publish(self, event: dict) -> None:
        self.events.append(event)
        self._draining.append(event)

    def drain(self) -> list[dict]:
        drained = self._draining
        self._draining = []
        return drained

    def has(self, partial: dict) -> bool:
        """Check if any event matches the given partial dict."""
        return any(
            all(e.get(k) == v for k, v in partial.items())
            for e in self.events
        )


@dataclass
class FakeChunk:
    content: str


class FakeAgentRunner:
    """Agent runner that yields predetermined chunks."""

    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.calls: list[tuple[str, str]] = []

    async def run(self, message: str, session_id: str) -> AsyncIterator[FakeChunk]:
        self.calls.append((message, session_id))
        for chunk in self.chunks:
            yield FakeChunk(content=chunk)


@dataclass
class FakeWebSocket:
    """Test double for WebSocketAdapter."""

    inputs: list[dict] = field(default_factory=list)
    sent: list[dict] = field(default_factory=list)
    accepted: bool = False
    _cursor: int = 0

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)

    async def receive_json(self) -> dict:
        if self._cursor >= len(self.inputs):
            raise StopAsyncIteration
        data = self.inputs[self._cursor]
        self._cursor += 1
        return data
