"""Tests for WebSocketSession orchestration."""

import pytest

from possession.services.message_router import MessageRouter
from possession.services.session import WebSocketSession
from possession.testing import FakeAgentRunner, FakeEventBus, FakeWebSocket


@pytest.mark.asyncio
async def test_session_streams_chat_chunks():
    agent = FakeAgentRunner(["Hello", " world"])
    bus = FakeEventBus()
    router = MessageRouter()
    session = WebSocketSession(agent, bus, router, session_id="sid-1")

    ws = FakeWebSocket(inputs=[{"message": "hi"}])
    await session.handle(ws)

    # Ping + 2 chat chunks + chat_end
    assert ws.accepted
    types = [m.get("type") for m in ws.sent]
    assert "ping" in types
    assert types.count("chat") == 2
    assert types[-1] == "chat_end"


@pytest.mark.asyncio
async def test_session_drains_ui_events():
    agent = FakeAgentRunner(["Done"])
    bus = FakeEventBus([
        {"type": "ui_action", "action": "navigate", "view": "invoices"},
    ])
    router = MessageRouter()
    session = WebSocketSession(agent, bus, router, session_id="sid")

    ws = FakeWebSocket(inputs=[{"message": "show invoices"}])
    await session.handle(ws)

    sent_navigate = [m for m in ws.sent if m.get("action") == "navigate"]
    assert len(sent_navigate) == 1


@pytest.mark.asyncio
async def test_session_uses_router_for_typed_messages():
    agent = FakeAgentRunner(["OK"])
    bus = FakeEventBus()
    router = MessageRouter()
    router.register(
        "form_submit",
        lambda data: f"User submitted form: {data.get('form_data')}",
    )
    session = WebSocketSession(agent, bus, router, session_id="sid")

    ws = FakeWebSocket(inputs=[{"type": "form_submit", "form_data": {"x": "1"}}])
    await session.handle(ws)

    assert agent.calls[0][0] == "User submitted form: {'x': '1'}"


@pytest.mark.asyncio
async def test_session_skips_when_router_returns_none():
    agent = FakeAgentRunner(["should not run"])
    bus = FakeEventBus()
    router = MessageRouter()
    router.register("ping_back", lambda data: None)
    session = WebSocketSession(agent, bus, router, session_id="sid")

    ws = FakeWebSocket(inputs=[{"type": "ping_back"}])
    await session.handle(ws)

    assert agent.calls == []
