"""Queue-based event bus implementation."""

import queue
from typing import Any


class QueueEventBus:
    """UIEventBus backed by a thread-safe queue.

    Tools can publish from any thread (Agno runs tools in a separate thread).
    The session handler drains the queue from the async loop.
    """

    def __init__(self) -> None:
        self._q: queue.Queue[dict[str, Any]] = queue.Queue()

    def publish(self, event: dict[str, Any]) -> None:
        self._q.put(event)

    def drain(self) -> list[dict[str, Any]]:
        events = []
        while not self._q.empty():
            try:
                events.append(self._q.get_nowait())
            except queue.Empty:
                break
        return events
