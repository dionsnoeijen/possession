"""Protocol message types for possession."""

from typing import Any, TypedDict


class UIActionMessage(TypedDict, total=False):
    type: str  # "ui_action"
    action: str  # "render" | "update" | "remove" | "navigate"
    component_id: str
    component_type: str
    position: str  # "main" | "sidebar" | "notifications"
    props: dict[str, Any]
    view: str
    params: dict[str, str]


class ViewDataMessage(TypedDict):
    type: str  # "view_data"
    view: str
    data: Any


class FormFillMessage(TypedDict):
    type: str  # "form_fill"
    field: str
    value: str


class HighlightMessage(TypedDict):
    type: str  # "highlight_item"
    item_id: str


class ChatStreamMessage(TypedDict):
    type: str  # "chat"
    content: str
    streaming: bool


class ChatEndMessage(TypedDict):
    type: str  # "chat_end"
    content: str


class ErrorMessage(TypedDict):
    type: str  # "error"
    content: str
