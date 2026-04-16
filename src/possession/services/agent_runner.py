"""Agno-based agent runner."""

from typing import Any, AsyncIterator

from agno.agent import Agent


class AgnoAgentRunner:
    """AgentRunner implementation wrapping an Agno Agent."""

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    async def run(self, message: str, session_id: str) -> AsyncIterator[Any]:
        stream = await self.agent.arun(
            message=message,
            session_id=session_id,
            stream=True,
        )
        async for chunk in stream:
            yield chunk
