"""Convenience builder for an Agno agent with possession wired in."""

from typing import Any

from agno.agent import Agent
from agno.tools import Toolkit

from possession.protocols import UIEventBus
from possession.services.agent_runner import AgnoAgentRunner
from possession.ui_tool import UITool

BASE_INSTRUCTIONS = [
    "You can control the visual interface using your tools.",
    "Domain-specific tools update the UI automatically — do NOT use render_component "
    "for data that domain tools already handle.",
    "render_component is only for custom visualizations not covered by domain tools.",
    "Be concise in chat. Let the UI do the heavy lifting for visual information.",
]


def build_agent(
    *,
    model: Any,
    event_bus: UIEventBus,
    tools: list[Toolkit] | None = None,
    instructions: list[str] | None = None,
    db: Any = None,
    name: str = "PossessionAgent",
    history_runs: int = 10,
    **agent_kwargs: Any,
) -> tuple[AgnoAgentRunner, UITool]:
    """Build an Agno agent wired for possession.

    Args:
        model: Any Agno model instance (Claude, OpenAIChat, Gemini, etc.).
            This is your choice — possession is model-agnostic.
        event_bus: The UIEventBus that UITool publishes to.
        tools: Your domain tools. UITool is added automatically.
        instructions: Domain-specific instructions. Base UI instructions are prepended.
        db: Optional Agno db for session persistence (e.g. PostgresDb).
        name: Agent name.
        history_runs: How many past runs to include in context.
        **agent_kwargs: Any additional Agno Agent kwargs.

    Returns:
        Tuple of (agent_runner, ui_tool). Wire into WebSocketSession.
    """
    ui_tool = UITool(event_bus=event_bus)
    all_tools: list[Toolkit] = [ui_tool] + list(tools or [])
    all_instructions = BASE_INSTRUCTIONS + list(instructions or [])

    kwargs: dict[str, Any] = {
        "name": name,
        "model": model,
        "tools": all_tools,
        "instructions": all_instructions,
        "markdown": True,
        "add_history_to_context": True,
        "num_history_runs": history_runs,
    }
    if db is not None:
        kwargs["db"] = db
    kwargs.update(agent_kwargs)

    agent = Agent(**kwargs)
    return AgnoAgentRunner(agent), ui_tool
