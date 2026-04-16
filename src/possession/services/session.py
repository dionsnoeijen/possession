"""Per-connection WebSocket session orchestrator."""

import uuid
from typing import Any

from possession.protocols import (
    AgentRunner,
    UIEventBus,
    WebSocketAdapter,
)
from possession.services.message_router import MessageRouter


def _disconnect_types() -> tuple[type[BaseException], ...]:
    """Return exception types that indicate a clean disconnect."""
    types: list[type[BaseException]] = [StopAsyncIteration]
    try:
        from starlette.websockets import WebSocketDisconnect
        types.append(WebSocketDisconnect)
    except ImportError:
        pass
    return tuple(types)


_DISCONNECT = _disconnect_types()


class WebSocketSession:
    """Orchestrates a single WebSocket connection.

    Pure orchestration — no business logic. All dependencies injected.
    """

    def __init__(
        self,
        agent_runner: AgentRunner,
        event_bus: UIEventBus,
        router: MessageRouter,
        session_id: str | None = None,
    ) -> None:
        self.agent = agent_runner
        self.bus = event_bus
        self.router = router
        self.session_id = session_id or str(uuid.uuid4())

    async def handle(self, websocket: WebSocketAdapter) -> None:
        await websocket.accept()
        await websocket.send_json({"type": "ping"})

        try:
            while True:
                try:
                    data = await websocket.receive_json()
                except _DISCONNECT:
                    return

                message = self.router.route(data)
                if message is None:
                    continue

                await self._stream_response(websocket, message)
        except Exception as e:
            await self._send_error(websocket, str(e))

    async def _stream_response(
        self,
        websocket: WebSocketAdapter,
        message: str,
    ) -> None:
        chunks: list[str] = []

        async for chunk in self.agent.run(message, self.session_id):
            # Drain UI events between stream chunks
            for event in self.bus.drain():
                await websocket.send_json(event)

            if getattr(chunk, "content", None):
                chunks.append(chunk.content)
                await websocket.send_json({
                    "type": "chat",
                    "content": chunk.content,
                    "streaming": True,
                })

        # Drain any remaining events
        for event in self.bus.drain():
            await websocket.send_json(event)

        # Signal stream end
        await websocket.send_json({
            "type": "chat_end",
            "content": "".join(chunks),
        })

    async def _send_error(self, websocket: WebSocketAdapter, message: str) -> None:
        try:
            await websocket.send_json({"type": "error", "content": message})
        except Exception:
            pass
