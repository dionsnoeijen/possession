"""Per-connection WebSocket session orchestrator."""

import uuid
from typing import Any

from possession.protocols import (
    AgentRunner,
    UIEventBus,
    WebSocketAdapter,
)
from possession.services.message_router import MessageRouter
from possession.tool_meta import get_tool_meta


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

            event_name = str(getattr(chunk, "event", "") or "")

            if event_name in ("ToolCallStarted", "ToolCallCompleted"):
                tool = getattr(chunk, "tool", None)
                name = getattr(tool, "tool_name", None) if tool else None
                if name:
                    meta = get_tool_meta(name)
                    if not meta.silent:
                        payload: dict[str, Any] = {
                            "type": "tool_call",
                            "status": "started" if event_name == "ToolCallStarted" else "completed",
                            "name": name,
                            "label": meta.label,
                        }
                        if meta.icon:
                            payload["icon"] = meta.icon
                        await websocket.send_json(payload)
                continue

            # Only forward actual text content. Skip RunCompleted (full content
            # duplicate at end), RunStarted, ModelRequestStarted, etc.
            if event_name != "RunContent":
                continue

            content = getattr(chunk, "content", None)
            if not content:
                continue

            chunks.append(content)
            await websocket.send_json({
                "type": "chat",
                "content": content,
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
