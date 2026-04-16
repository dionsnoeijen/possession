"""FastAPI integration helpers."""

from typing import Any, Awaitable, Callable

from fastapi import FastAPI, WebSocket

from possession.services.session import WebSocketSession

AuthResolver = Callable[[WebSocket], Awaitable[Any]]
SessionFactory = Callable[[Any], WebSocketSession]


def mount_possession(
    app: FastAPI,
    path: str,
    session_factory: SessionFactory,
    auth: AuthResolver | None = None,
) -> None:
    """Mount a possession WebSocket endpoint.

    Args:
        app: The FastAPI application.
        path: WebSocket path (e.g., "/ws/chat").
        session_factory: Callable that returns a new WebSocketSession per connection.
            Receives the resolved user context (or None if no auth configured).
        auth: Optional async callable that receives the WebSocket and returns
            a user context. If it returns None, the connection is rejected with
            code 4401 (Unauthorized) before accept().

    Example:
        async def verify_jwt(ws):
            token = ws.query_params.get("token")
            if not token:
                return None
            try:
                claims = jwt.decode(token, SECRET, algorithms=["HS256"])
                return User(id=claims["sub"], email=claims["email"])
            except JWTError:
                return None

        def make_session(user):
            bus = QueueEventBus()
            ...
            return WebSocketSession(agent_runner, bus, router,
                                     session_id=f"user:{user.id}")

        mount_possession(app, "/ws/chat", make_session, auth=verify_jwt)
    """

    @app.websocket(path)
    async def _endpoint(websocket: WebSocket):
        user: Any = None
        if auth is not None:
            user = await auth(websocket)
            if user is None:
                # Reject with 4401 before accepting — browser sees close code
                await websocket.close(code=4401)
                return

        session = session_factory(user)
        await session.handle(websocket)
