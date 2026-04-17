"""Tool metadata — labels, icons, and flags that travel with each tool call.

Decorate your tools with @possession_tool(...) so the frontend can render
meaningful badges without maintaining a duplicate map.
"""

from dataclasses import dataclass
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


@dataclass(frozen=True)
class ToolMeta:
    label: str
    icon: str | None = None
    silent: bool = False


_META: dict[str, ToolMeta] = {}


def possession_tool(
    *,
    label: str,
    icon: str | None = None,
    silent: bool = False,
) -> Callable[[F], F]:
    """Attach metadata to a tool method.

    Args:
        label: Human-readable label shown as a badge in the frontend.
        icon: Optional icon identifier (string). The frontend maps it to its
            own icon library via the Chat `iconMap` prop.
        silent: If True, the frontend hides the badge for this tool. Useful
            for plumbing tools that should not clutter the chat.

    Example:
        class CRMTool(Toolkit):
            @possession_tool(label="Reminder drafted", icon="mail")
            def create_reminder(self, ...): ...

            @possession_tool(label="Page set", silent=True)
            def set_form_page(self, ...): ...
    """

    def decorator(func: F) -> F:
        _META[func.__name__] = ToolMeta(label=label, icon=icon, silent=silent)
        setattr(func, "_possession_meta", _META[func.__name__])
        return func

    return decorator


def get_tool_meta(name: str) -> ToolMeta:
    """Return metadata for a tool, falling back to a prettified label."""
    if name in _META:
        return _META[name]
    fallback = name.replace("_", " ").capitalize() if name else "Tool"
    return ToolMeta(label=fallback)


def get_tool_label(name: str) -> str:
    """Return the label for a tool. Kept for backwards compatibility."""
    return get_tool_meta(name).label
