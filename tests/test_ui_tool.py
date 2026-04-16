"""Tests for UITool."""

from possession.testing import FakeEventBus
from possession.ui_tool import UITool


def test_navigate_publishes_event():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    tool.navigate("invoices")

    assert bus.has({"type": "ui_action", "action": "navigate", "view": "invoices"})


def test_navigate_with_params():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    tool.navigate("contact-detail", {"contact_id": "c1"})

    assert bus.events[0]["params"] == {"contact_id": "c1"}


def test_send_form_fill():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    tool.send_form_fill("company_name", "DataFlow")

    assert bus.has({
        "type": "form_fill",
        "field": "company_name",
        "value": "DataFlow",
    })


def test_render_in_zone():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    cid = tool.render_in_zone(
        zone="notifications",
        component_type="reminder_card",
        props={"recipient": "Mohammed"},
    )

    assert cid.startswith("reminder_card_")
    assert bus.has({
        "type": "ui_action",
        "action": "render",
        "zone": "notifications",
        "component_type": "reminder_card",
    })


def test_render_in_zone_with_id():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    cid = tool.render_in_zone(
        zone="notifications",
        component_type="card",
        props={},
        component_id="my-card",
    )

    assert cid == "my-card"


def test_render_component_parses_json_props():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    result = tool.render_component(
        zone="main",
        component_type="table",
        props='{"headers": ["a"]}',
    )

    assert "Rendered table" in result
    assert bus.events[0]["props"] == {"headers": ["a"]}


def test_render_component_invalid_json():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    result = tool.render_component(
        zone="main",
        component_type="table",
        props="not json",
    )

    assert "Error" in result
    assert len(bus.events) == 0
