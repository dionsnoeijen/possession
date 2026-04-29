"""UI Control Tool — publishes UI events via an injected event bus."""

import json
import uuid
from typing import Any

from agno.tools import Toolkit

from possession.protocols import UIEventBus


class UITool(Toolkit):
    """Agent tool that publishes UI control events.

    Depends on a UIEventBus — not on a specific queue implementation.
    Makes the tool testable and decoupled from transport.
    """

    def __init__(self, event_bus: UIEventBus) -> None:
        super().__init__(name="ui")
        self.bus = event_bus
        self.register(self.render_component)
        self.register(self.update_component)
        self.register(self.remove_component)

    # -- Programmatic API for domain tools --

    def navigate(self, view: str, params: dict[str, str] | None = None) -> None:
        msg: dict[str, Any] = {
            "type": "ui_action",
            "action": "navigate",
            "view": view,
        }
        if params:
            msg["params"] = params
        self.bus.publish(msg)

    def send_view_data(self, view: str, data: Any) -> None:
        self.bus.publish({"type": "view_data", "view": view, "data": data})

    def send_form_fill(self, field: str, value: str) -> None:
        self.bus.publish({
            "type": "form_fill",
            "field": field,
            "value": value,
        })

    def open_form(self, form_type: str, params: dict[str, Any] | None = None) -> None:
        msg: dict[str, Any] = {
            "type": "ui_action",
            "action": "open_form",
            "form_type": form_type,
        }
        if params:
            msg["params"] = params
        self.bus.publish(msg)

    def submit_form(self) -> None:
        self.bus.publish({"type": "ui_action", "action": "submit_form"})

    def highlight_item(self, item_id: str) -> None:
        self.bus.publish({"type": "highlight_item", "item_id": item_id})

    def render_in_zone(
        self,
        zone: str,
        component_type: str,
        props: dict[str, Any],
        component_id: str | None = None,
    ) -> str:
        if not component_id:
            component_id = f"{component_type}_{uuid.uuid4().hex[:8]}"
        self.bus.publish({
            "type": "ui_action",
            "action": "render",
            "component_id": component_id,
            "component_type": component_type,
            "zone": zone,
            "props": props,
        })
        return component_id

    def update_in_zone(self, component_id: str, props: dict[str, Any]) -> None:
        self.bus.publish({
            "type": "ui_action",
            "action": "update",
            "component_id": component_id,
            "props": props,
        })

    def remove_from_zone(self, component_id: str) -> None:
        self.bus.publish({
            "type": "ui_action",
            "action": "remove",
            "component_id": component_id,
        })

    # -- Agent-callable tools (registered with Agno) --

    def render_component(
        self,
        zone: str,
        component_type: str,
        props: str,
        component_id: str = "",
    ) -> str:
        """Render a UI component in a named zone.

        Args:
            zone: Target zone name (defined by the app).
            component_type: Built-in (table, card, metric, list, chart, html) or custom.
            props: JSON string with component properties.
            component_id: Optional unique ID. Auto-generated if empty.

        Returns:
            Confirmation with the component ID.
        """
        try:
            parsed_props = json.loads(props)
        except json.JSONDecodeError:
            return f"Error: invalid JSON in props: {props}"

        cid = self.render_in_zone(zone, component_type, parsed_props, component_id or None)
        return f"Rendered {component_type} '{cid}' in zone '{zone}'."

    def update_component(self, component_id: str, props: str) -> str:
        """Update an existing UI component.

        Args:
            component_id: ID of the component to update.
            props: JSON string with properties to merge.
        """
        try:
            parsed_props = json.loads(props)
        except json.JSONDecodeError:
            return f"Error: invalid JSON in props: {props}"

        self.update_in_zone(component_id, parsed_props)
        return f"Updated component '{component_id}'."

    def remove_component(self, component_id: str) -> str:
        """Remove a UI component from the frontend.

        Args:
            component_id: ID of the component to remove.
        """
        self.remove_from_zone(component_id)
        return f"Removed component '{component_id}'."
