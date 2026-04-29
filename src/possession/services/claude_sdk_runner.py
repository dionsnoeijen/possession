"""Claude Agent SDK runner.

Parallel to AgnoAgentRunner. Wraps `claude-agent-sdk` and translates its
typed Message/Block stream into the duck-typed chunk shape that
WebSocketSession expects (`.event`, `.content`, `.tool.tool_name`).

Session continuity: first pass uses the one-shot `query()` function, which
does not carry conversation history across turns. Upgrade to
`ClaudeSDKClient` for per-session history once this is stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass
class _ToolRef:
    tool_name: str


@dataclass
class _Chunk:
    """Duck-typed shape WebSocketSession expects."""
    event: str
    content: str | None = None
    tool: _ToolRef | None = None
    args: dict | None = None


class ClaudeSDKAgentRunner:
    """AgentRunner implementation wrapping claude-agent-sdk.

    Uses `ClaudeSDKClient` so conversation history is preserved across turns
    within a WebSocket session. Call `close()` (awaitable) on session end to
    release the subprocess the SDK manages.
    """

    def __init__(self, options: Any) -> None:
        """
        Args:
            options: a `ClaudeAgentOptions` instance. Typed as Any here to
                keep this module import-safe when claude-agent-sdk isn't
                installed (the import happens lazily in `run`).
        """
        self.options = options
        self._client: Any | None = None

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None

    async def run(self, message: str, session_id: str) -> AsyncIterator[Any]:
        # Lazy import so possession can be installed without claude-agent-sdk.
        from claude_agent_sdk import ClaudeSDKClient  # type: ignore

        if self._client is None:
            self._client = ClaudeSDKClient(options=self.options)
            await self._client.connect()

        await self._client.query(message)
        async for msg in self._client.receive_response():
            msg_type = type(msg).__name__
            # Token-level streaming: StreamEvent carries partial deltas.
            if msg_type == "StreamEvent":
                event_field = getattr(msg, "event", None)
                event_obj = event_field if event_field is not None else msg
                evt_type = getattr(event_obj, "type", None) or (
                    event_obj.get("type") if isinstance(event_obj, dict) else None
                )
                if evt_type == "content_block_delta":
                    delta = (
                        getattr(event_obj, "delta", None)
                        if not isinstance(event_obj, dict)
                        else event_obj.get("delta")
                    )
                    delta_type = getattr(delta, "type", None) or (
                        delta.get("type") if isinstance(delta, dict) else None
                    )
                    text = getattr(delta, "text", None) or (
                        delta.get("text") if isinstance(delta, dict) else None
                    )
                    thinking = getattr(delta, "thinking", None) or (
                        delta.get("thinking") if isinstance(delta, dict) else None
                    )
                    if delta_type == "text_delta" and text:
                        yield _Chunk(event="RunContent", content=text)
                    elif delta_type == "thinking_delta" and thinking:
                        yield _Chunk(event="ReasoningContent", content=thinking)
                continue

            content = getattr(msg, "content", None)
            if not isinstance(content, list):
                continue

            # Full AssistantMessage pass: skip TextBlocks here since token-level
            # deltas already streamed the text above. Only emit tool events.
            for block in content:
                block_type = type(block).__name__

                if block_type == "TextBlock":
                    # Skip — already streamed via StreamEvent deltas.
                    continue

                elif block_type == "ThinkingBlock":
                    # Skip — already streamed via StreamEvent thinking_deltas.
                    continue

                elif block_type == "ToolUseBlock":
                    raw_input = getattr(block, "input", None)
                    args = raw_input if isinstance(raw_input, dict) else None
                    yield _Chunk(
                        event="ToolCallStarted",
                        tool=_ToolRef(tool_name=getattr(block, "name", "") or ""),
                        args=args,
                    )

                elif block_type == "ToolResultBlock":
                    # ToolResultBlock references the original tool_use_id;
                    # the concrete tool name is on the corresponding
                    # ToolUseBlock earlier in the stream. Best-effort here.
                    name = getattr(block, "tool_name", "") or getattr(block, "name", "") or ""
                    yield _Chunk(event="ToolCallCompleted", tool=_ToolRef(tool_name=name))
