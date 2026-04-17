"""Possession — AI takes control of your UI."""

from possession.agent_builder import build_agent
from possession.auth import header_auth, jwt_auth
from possession.mount import mount_possession
from possession.protocols import (
    AgentRunner,
    MessageHandler,
    UIEventBus,
    WebSocketAdapter,
)
from possession.services import (
    AgnoAgentRunner,
    MessageRouter,
    QueueEventBus,
    WebSocketSession,
)
from possession.tool_meta import possession_tool, get_tool_label
from possession.ui_tool import UITool

__all__ = [
    # Protocols
    "UIEventBus",
    "AgentRunner",
    "MessageHandler",
    "WebSocketAdapter",
    # Services
    "QueueEventBus",
    "AgnoAgentRunner",
    "MessageRouter",
    "WebSocketSession",
    # Tool
    "UITool",
    # Integration
    "mount_possession",
    "build_agent",
    # Auth
    "jwt_auth",
    "header_auth",
    # Tool metadata
    "possession_tool",
    "get_tool_label",
]
