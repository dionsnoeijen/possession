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

The library provides the glue: a WebSocket protocol, agent runners for both Agno and Claude Agent SDK (the engine behind Claude Code), and the services to wire it together. You bring your domain tools, your views, your layout.

## Philosophy: explicit control

Possession is built around a deliberate choice: the agent can only do what you give it tools to do.

No raw database access. No arbitrary code execution. No open-ended generation of SQL, shell commands, or business logic. Every action the agent can take is a named tool you write, with parameters you define and authorization you enforce.

This has trade-offs. You write more tools. Adding a new capability means adding a new tool. But in return:

- Every action is auditable (tool calls are logged by name)
- Every action is authorized (you decide what the agent can do per user, per role, per context)
- Every action is validated (your tool validates input before hitting the store)
- Business logic stays in code, not in an LLM's head
- You can test your tools without running the agent

If you want a pure "raw access" experiment, possession is the wrong library. If you want to ship AI-driven features into a real SaaS app without losing control, this is the approach.

## Managing tool bloat

The controlled approach scales only as far as your tool count stays manageable. A few patterns to keep it clean:

**Grouped tools.** Instead of 15 flat tools, group related actions into one tool with an `action` parameter:

```python
class DealsTool(Toolkit):
    def manage_deal(self, deal_id: str, action: str, data: str = "") -> str:
        """Manage a deal.

        Args:
            deal_id: The deal ID.
            action: One of: update_stage, add_note, close_won, close_lost, reopen.
            data: JSON payload for the action (stage name, note content, etc.).
        """
        ...
```

One tool, many actions. Less prompt bloat.

**Scoped tool loading.** Register different toolkits based on the user's role or the current view. A read-only user gets read-only tools. An admin gets the full set.

```python
def make_session(user):
    tools = [read_tools]
    if user["role"] == "admin":
        tools.append(admin_tools)
    ...
```

**Resource-style reads.** A single `query_resource(type, filters)` tool can cover many read cases. Writes stay explicit.

```python
def query_resource(self, resource_type: str, filters: str = "{}") -> str:
    """Query a resource with filters. Read-only.

    Args:
        resource_type: One of: contacts, deals, invoices, notes.
        filters: JSON object with filter criteria.
        """
```

Possession does not prescribe any of these. Your tools, your call. But the library stays out of the way, so you can go as flat or as hierarchical as your app needs.

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
- `claude-sdk`: Claude Agent SDK runner — full Claude Code engine with built-in filesystem / bash / grep tools (adds claude-agent-sdk)

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

## Quick start (Claude Agent SDK)

If you want Claude Code's agent engine instead of Agno — same built-in filesystem tools (Read, Grep, Glob, Bash, Edit), same reasoning loop, same streaming — use `ClaudeSDKAgentRunner`. Your domain tools get defined with the SDK's `@tool` decorator and bundled via `create_sdk_mcp_server`.

```python
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool
from possession import (
    QueueEventBus, UITool, ClaudeSDKAgentRunner,
    MessageRouter, WebSocketSession, possession_tool, mount_possession,
)

def build_tools(ui: UITool, user):
    @tool("search_contacts", "Search contacts by name/email/company.", {"query": str})
    @possession_tool(label="Contacts searched")
    async def search_contacts(args):
        contacts = store.search(args["query"], owner=user["sub"])
        ui.navigate("contacts")
        ui.send_view_data("contacts", contacts)
        return {"content": [{"type": "text", "text": f"Found {len(contacts)}"}]}

    return [search_contacts]

def make_session(user):
    bus = QueueEventBus()
    ui = UITool(event_bus=bus)
    tools = build_tools(ui, user)

    server = create_sdk_mcp_server(name="crm", version="0.1.0", tools=tools)

    options = ClaudeAgentOptions(
        system_prompt="You are the CRM assistant.",
        mcp_servers={"crm": server},
        allowed_tools=[f"mcp__crm__{t.name}" for t in tools] + ["Read", "Grep", "Glob"],
        cwd="/path/to/project",
        include_partial_messages=True,                        # enables token-level streaming
        extra_args={"thinking": "enabled"},                   # enables reasoning events
    )

    runner = ClaudeSDKAgentRunner(options)
    router = MessageRouter()
    return WebSocketSession(runner, bus, router, session_id=f"user:{user['sub']}")

mount_possession(app, "/ws/chat", make_session)
```

The `@possession_tool` decorator works the same as with Agno — labels are looked up by the bare function name, and the `mcp__<server>__<tool>` prefix is stripped automatically.

**Install:**
```bash
pip install "possession[claude-sdk] @ git+https://github.com/dionsnoeijen/possession.git"
```

## Tool event stream

Whichever runner you use, `WebSocketSession` forwards a consistent set of messages to the frontend:

- `tool_call` (status `started` / `completed`) with `name`, `label`, optional `args` and `icon`
- `reasoning` (Claude SDK only, when thinking is enabled) — live thinking-block deltas
- `chat` — token-level text deltas
- `chat_end` — stream complete
- `ui_action` — render/update/remove for `PossessionZone` components
- `view_data`, `form_fill`, `highlight_item` — zone-less convenience channels

The possession-react frontend consumes these out of the box.

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
from possession import UITool, possession_tool

class CRMTool(Toolkit):
    def __init__(self, ui: UITool, store, user_id: str):
        super().__init__(name="crm")
        self.ui = ui
        self.store = store
        self.user_id = user_id
        self.register(self.search_contacts)
        self.register(self.create_reminder)

    @possession_tool(label="Contacts searched")
    def search_contacts(self, query: str = "") -> str:
        """Search contacts by name, company, or email.

        Use this when the user wants to find contacts or filter the list.

        Args:
            query: Search text to match against name, email, or company.
        """
        contacts = self.store.search(query, owner=self.user_id)
        self.ui.navigate("contacts")
        self.ui.send_view_data("contacts", contacts)
        return f"Found {len(contacts)} contacts."

    @possession_tool(label="Reminder drafted")
    def create_reminder(self, contact_id: str, message: str) -> str:
        """Create a reminder draft for a contact.

        Args:
            contact_id: The ID of the contact.
            message: The body of the reminder.
        """
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

Each tool does two things: business logic, and UI intent. The agent decides when to call them.

### Two things the LLM reads from your tools

1. **The docstring.** Agno extracts the docstring of each registered method and sends it to the LLM as the tool's description. This is what the model reads to decide WHEN to call the tool and WHAT arguments to pass. Be specific: mention when to use it, what each argument means, and what exact values are accepted for enum-like parameters. If you add select values to the docstring, the model will use them verbatim.
2. **The type hints.** Argument types are turned into a JSON schema that constrains the LLM's calls. String, number, boolean, and JSON-serialised dicts work well.

### Tool metadata via `@possession_tool`

Wrap your tools with `@possession_tool(...)` to attach metadata that travels with every tool-call event to the frontend. The UI renders this as a compact badge above the assistant's response.

```python
@possession_tool(label="Deals loaded")
def list_deals(self, stage: str = "") -> str:
    ...

@possession_tool(label="Reminder drafted", icon="mail")
def create_reminder(self, ...):
    ...

@possession_tool(label="Page set", silent=True)
def set_form_page(self, page: int) -> str:
    ...
```

Supported arguments:

| Argument | Type | Purpose |
|----------|------|---------|
| `label` | `str` (required) | Human-readable badge text in the chat. |
| `icon` | `str` (optional) | Icon identifier. The frontend maps it to its own icon library via the Chat `iconMap` prop. |
| `silent` | `bool` (optional) | Skip rendering a badge for this tool. Useful for plumbing tools the user should not care about. |

If you skip the decorator, the frontend falls back to a prettified version of the function name (`list_deals` → `List deals`). Metadata is defined ONCE on the backend — the frontend does not need a duplicate map.

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
  claude_sdk_runner.py   ClaudeSDKAgentRunner (Claude Code engine)
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

## Runner & model agnostic

You pick both the **runner** and the **model**. Two runners are built-in; both implement the same `AgentRunner` protocol so `WebSocketSession` doesn't care which one you use.

**`AgnoAgentRunner`** — wraps an Agno Agent. Any model Agno supports works:

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

**`ClaudeSDKAgentRunner`** — wraps the Claude Agent SDK (the engine behind Claude Code). Claude-only, but you get the full Claude Code toolkit: built-in `Read`, `Grep`, `Glob`, `Bash`, `Edit`, `Write`, plus MCP tools you define yourself. Supports token-level streaming (`include_partial_messages=True`) and reasoning-block streaming (`extra_args={"thinking": "enabled"}`).

You'll want this when your agent should genuinely reason over source files, project structure, or a curated knowledge base — not just call tools.

Or bring your own runner by implementing the `AgentRunner` protocol.

## License

MIT
