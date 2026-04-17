"""Agno-based agent runner."""

from typing import Any, AsyncIterator

from agno.agent import Agent


class AgnoAgentRunner:
    """AgentRunner implementation wrapping an Agno Agent."""

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    async def run(self, message: str, session_id: str) -> AsyncIterator[Any]:
        result = self.agent.arun(
            input=message,
            session_id=session_id,
            stream=True,
            stream_events=True,
        )
        if hasattr(result, "__aiter__"):
            async for chunk in result:
                yield chunk
        else:
            stream = await result
            async for chunk in stream:
                yield chunk
