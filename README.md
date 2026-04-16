# possession

AI takes control of your UI.

A Python library for building applications where an AI agent can drive your existing user interface. Talk to your software: the agent navigates views, fills forms, renders components, and sends notifications, while your app keeps working exactly as it did before.

## See it in action

https://github.com/dionsnoeijen/possession/raw/main/docs/demo-1.mp4

https://github.com/dionsnoeijen/possession/raw/main/docs/demo-2.mp4

> If the videos do not play inline, download them from [`docs/demo-1.mp4`](docs/demo-1.mp4) and [`docs/demo-2.mp4`](docs/demo-2.mp4).

## What it does

You have a regular web app. Pages, tables, forms, the usual. `possession` lets you bolt an AI agent onto it that can do everything a user can do, and more:

- Navigate to any view in your app
- Filter and update existing tables
- Fill form fields one by one, as if typed
- Render custom components in named zones (notifications, inspector panels, toasts, anything)
- Highlight items to draw attention
- Send notifications with confirmation flows

The library provides the glue: a WebSocket protocol, an Agno agent tool that publishes UI events, and the services to wire it together. You bring your domain tools, your views, your layout.

## Install

Not yet on PyPI. For now, install from GitHub:

```bash
pip install git+https://github.com/dionsnoeijen/possession.git
```

With optional extras:

```bash
pip install "possession[jwt] @ git+https://github.com/dionsnoeijen/possession.git"
pip install "possession[postgres] @ git+https://github.com/dionsnoeijen/possession.git"
```

Available extras:
- `jwt`: built-in JWT auth helper (adds PyJWT)
- `postgres`: PostgresDb session storage (adds sqlalchemy, psycopg2-binary)
- `anthropic`: Claude model support via Agno (adds anthropic)

For local development:
```bash
git clone git@github.com:dionsnoeijen/possession.git
cd possession
pip install -e ".[dev]"
```

Once published to PyPI:
```bash
pip install possession
pip install "possession[jwt,postgres]"
```

## Quick start

```python
from fastapi import FastAPI
from agno.models.anthropic import Claude
from agno.db.postgres import PostgresDb

from possession import (
    QueueEventBus,
    MessageRouter,
    WebSocketSession,
    build_agent,
    mount_possession,
    jwt_auth,
)

from my_app.tools import CRMTool
from my_app.store import store

app = FastAPI()

def make_session(user: dict) -> WebSocketSession:
    bus = QueueEventBus()

    agent_runner, ui_tool = build_agent(
        model=Claude(id="claude-sonnet-4-6"),
        event_bus=bus,
        tools=[CRMTool(ui=ui_tool, store=store, user_id=user["sub"])],
        instructions=[f"You are assisting {user['email']}."],
        db=PostgresDb(db_url="postgresql+psycopg2://..."),
    )

    router = MessageRouter()
    return WebSocketSession(
        agent_runner, bus, router,
        session_id=f"user:{user['sub']}",
    )

mount_possession(
    app, "/ws/chat", make_session,
    auth=jwt_auth(secret="your-jwt-secret"),
)
```

That's it for the backend. Pair it with [`possession-react`](https://github.com/dionsnoeijen/possession-react) on the frontend.

## Auth

Possession is auth-agnostic but ships with a JWT helper as a sensible default.

### Default: JWT

```python
from possession import mount_possession, jwt_auth

mount_possession(
    app, "/ws/chat", make_session,
    auth=jwt_auth(secret="your-jwt-secret"),
)
```

The resolver reads the token from `?token=...` on the WebSocket URL, verifies it with the given secret, and passes the decoded claims to `make_session(user)`. If the token is missing or invalid, the connection is rejected with close code `4401` before the agent is created.

`jwt_auth` accepts `algorithms`, `audience`, `issuer`, and `token_param` arguments. See the docstring.

Requires PyJWT:
```bash
pip install "possession[jwt]"
```

### Custom auth

If you use cookies, OAuth tokens, or anything else, write your own async resolver:

```python
async def my_auth(websocket):
    token = websocket.cookies.get("session")
    user = await verify_cookie(token)
    return user  # dict, dataclass, anything, or None to reject

mount_possession(app, "/ws/chat", make_session, auth=my_auth)
```

Whatever your resolver returns is what `make_session(user)` receives.

### No auth

For development or internal tools, just omit `auth=`. The session factory is then called with `user=None`.

## Writing domain tools

Your domain tools extend `agno.tools.Toolkit` and receive the `UITool` to publish UI events:

```python
from agno.tools import Toolkit
from possession import UITool

class CRMTool(Toolkit):
    def __init__(self, ui: UITool, store, user_id: str):
        super().__init__(name="crm")
        self.ui = ui
        self.store = store
        self.user_id = user_id
        self.register(self.search_contacts)
        self.register(self.create_reminder)

    def search_contacts(self, query: str = "") -> str:
        """Search contacts and show them in the contacts view."""
        contacts = self.store.search(query, owner=self.user_id)
        self.ui.navigate("contacts")
        self.ui.send_view_data("contacts", contacts)
        return f"Found {len(contacts)} contacts."

    def create_reminder(self, contact_id: str, message: str) -> str:
        """Render a reminder draft in the notifications zone."""
        notif_id = self.ui.render_in_zone(
            zone="notifications",
            component_type="reminder_draft",
            props={
                "contact_id": contact_id,
                "message": message,
                "status": "draft",
            },
        )
        return f"Draft reminder created: {notif_id}"
```

Each tool does two things: business logic, and UI intent. The agent decides when to call them. The WebSocket handler streams the events to the frontend.

## The UITool API

```python
ui.navigate(view, params=None)                      # go to a view
ui.send_view_data(view, data)                       # update an existing view
ui.send_form_fill(field, value)                     # fill one form field
ui.highlight_item(item_id)                          # highlight a list item
ui.render_in_zone(zone, type, props, id=None)       # render a component
ui.update_in_zone(component_id, props)              # update a rendered component
ui.remove_from_zone(component_id)                   # remove a rendered component
```

The agent has its own tool-level access too: `render_component`, `update_component`, `remove_component`. Use those when the agent needs to render something ad-hoc. Use the programmatic API when your own tool code wants to publish events.

## Incoming messages

The frontend sends messages with a `type`. Default behavior: the `message` field is forwarded to the agent. For typed messages (navigation context, form submits), register a handler:

```python
router = MessageRouter()

router.register(
    "navigate",
    lambda data: f"[User opened view: {data.get('view')}]",
)

router.register(
    "form_submit",
    lambda data: f"User submitted form {data.get('component_id')}: {data.get('form_data')}",
)
```

The handler returns a string to forward to the agent, or `None` to skip.

## Architecture

Everything is behind a protocol. Nothing is hardwired.

```
protocols.py             Interfaces
  UIEventBus             Where tools publish events
  AgentRunner            Wraps the LLM agent
  MessageHandler         Routes incoming messages
  WebSocketAdapter       Abstracts the transport

services/
  event_bus.py           QueueEventBus (thread-safe)
  agent_runner.py        AgnoAgentRunner
  message_router.py      MessageRouter
  session.py             WebSocketSession (orchestrator)

ui_tool.py               UITool (domain-facing API)
agent_builder.py         build_agent (convenience factory)
auth.py                  jwt_auth, header_auth
mount.py                 mount_possession (FastAPI glue)
```

Every service is injected. Every service is testable. Every service is replaceable.

## Testing

Fakes are provided for every protocol:

```python
from possession.testing import FakeEventBus, FakeAgentRunner, FakeWebSocket
from possession import UITool

def test_my_tool_publishes_navigate_event():
    bus = FakeEventBus()
    tool = UITool(event_bus=bus)

    tool.navigate("invoices")

    assert bus.has({"type": "ui_action", "action": "navigate", "view": "invoices"})
```

Run the library's own tests with `pytest` after `pip install -e ".[dev]"`.

## Model agnostic

You pick the model. Anything Agno supports works:

```python
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.models.ollama import Ollama

build_agent(model=Claude(id="claude-sonnet-4-6"), ...)
build_agent(model=OpenAIChat(id="gpt-4o"), ...)
build_agent(model=Gemini(id="gemini-2.0-flash"), ...)
build_agent(model=Ollama(id="llama3.3"), ...)
```

## License

MIT
