# msgraph-mcp

A hosted [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that wraps the Microsoft Graph API, giving AI assistants secure access to Microsoft 365 consumer services (Outlook.com, OneDrive, Microsoft To Do, etc.).

## Why

MCP lets AI models call external tools through a standard protocol. This project exposes Microsoft Graph endpoints as MCP tools so that any MCP-compatible client can read and manage a user's mail, calendar, files, tasks, and more — without needing to know the Graph API directly.

## Key Design Goals

- **Consumer-focused** — targets Microsoft personal accounts (MSA), not Entra ID / work accounts.
- **Hostable** — runs as a standalone service (FastMCP + Gunicorn/Uvicorn) deployed to Azure App Service.
- **Secure by default** — uses OAuth 2.0 authorization code flow with PKCE; tokens are never exposed to the AI client.
- **Thin wrapper** — maps MCP tool calls to Graph REST calls with minimal transformation, keeping the server easy to maintain as the Graph API evolves.

## Quickstart

```bash
# Install dependencies
uv sync

# Run the server locally
uv run python -m msgraph_mcp.server

# Run tests
uv run pytest
```

## MCP Tools

### Echo

- **`echo(message)`** — Echo back a message (health-check / smoke-test).

### Microsoft To-Do

All To-Do tools require the user to be authenticated via OAuth.

- **`list_task_lists()`** — List all Microsoft To-Do task lists with IDs and display names.
- **`list_tasks(list_id)`** — List all tasks in a task list, showing title, status, importance, due date, and body.
- **`create_task(title, list_id?, due_date?, body?)`** — Create a new task. Uses the default list when `list_id` is omitted. `due_date` must be in `YYYY-MM-DD` format.
- **`update_task(list_id, task_id, title?, status?, due_date?, body?, importance?)`** — Update one or more fields on a task. Valid statuses: `notStarted`, `completed`. Valid importances: `low`, `normal`, `high`.
- **`delete_task(list_id, task_id)`** — Delete a task from a task list.

### Email

All email tools require the user to be authenticated via OAuth.

- **`list_messages(folder_id?, count?)`** — List recent email messages with sender, subject, date, read status, and body preview. Optionally filter by folder ID. Default count is 10.
- **`read_message(message_id)`** — Read a specific email with full details: sender, recipients, CC, date, importance, read status, and complete body.
- **`search_messages(query, count?)`** — Search emails by keyword using Microsoft Graph `$search`. Returns matching messages with previews. Default count is 10.
- **`send_message(to, subject, body, cc?)`** — Send an email. `to` and `cc` accept comma-separated addresses. Validates email format before sending.
- **`list_mail_folders()`** — List all mail folders with display name, message count, and unread count.

### Calendar

All calendar tools require the user to be authenticated via OAuth.

- **`list_calendars()`** — List all calendars with name, color, default indicator, and ID.
- **`list_events(start_date?, end_date?, count?, timezone?)`** — List calendar events. When both `start_date` and `end_date` are provided, filters by date range and expands recurring events. Default count is 10, default timezone is UTC.
- **`get_event(event_id)`** — Get full details of a calendar event: subject, times, location, organizer, attendees with response statuses, body, recurrence, and online meeting link.
- **`create_event(subject, start_time, end_time, timezone?, location?, body?, attendees?, is_all_day?, is_online_meeting?)`** — Create a new calendar event. `attendees` accepts comma-separated email addresses. Validates time ordering.
- **`update_event(event_id, subject?, start_time?, end_time?, timezone?, location?, body?, attendees?, is_online_meeting?)`** — Update one or more fields on a calendar event. At least one field must be provided.
- **`delete_event(event_id)`** — Delete a calendar event.
- **`get_availability(start_time, end_time, timezone?, check_only?)`** — Check free/busy availability. Returns time slot breakdown by default, or a simple free/busy answer when `check_only=True`.

### Example Usage

```
> List my task lists
→ calls list_task_lists()

> Show tasks in list AAMkAD...
→ calls list_tasks(list_id="AAMkAD...")

> Create a task "Buy groceries" due 2025-01-20
→ calls create_task(title="Buy groceries", due_date="2025-01-20")

> Mark task AAkBT... in list AAMkAD... as completed
→ calls update_task(list_id="AAMkAD...", task_id="AAkBT...", status="completed")

> Delete task AAkBT... from list AAMkAD...
→ calls delete_task(list_id="AAMkAD...", task_id="AAkBT...")

> List my recent emails
→ calls list_messages()

> Show emails in folder AAMkAD...
→ calls list_messages(folder_id="AAMkAD...")

> Read email AAMkAG...
→ calls read_message(message_id="AAMkAG...")

> Search emails for "budget report"
→ calls search_messages(query="budget report")

> Send an email to john@example.com about the meeting
→ calls send_message(to="john@example.com", subject="Meeting", body="...")

> List my mail folders
→ calls list_mail_folders()
```

## Project Structure

```
msgraph_mcp/
  __init__.py   # Package metadata
  server.py     # MCP server (FastMCP + streamable HTTP + OAuth + To-Do + Email + Calendar tools)
  config.py     # Allowed users and OAuth configuration
  auth.py       # MicrosoftOAuthProvider (MCP OAuth ↔ Microsoft OAuth bridge)
  graph.py      # GraphClient — async Microsoft Graph API wrapper for To-Do, Email, and Calendar
  store.py      # Persistent credential cache (tokens, clients, MSAL cache)
tests/
  conftest.py     # Shared test fixtures
  test_config.py  # Config tests
  test_auth.py    # OAuth provider tests
  test_store.py   # Credential store tests
  test_graph.py   # GraphClient unit tests
  test_tools.py   # To-Do, Email, and Calendar MCP tool tests
infra/
  main.bicep    # Azure App Service infrastructure
.github/
  workflows/deploy.yml  # CI/CD pipeline
```

## Authentication

The server uses MCP-native OAuth to authenticate users with Microsoft personal accounts.

### Prerequisites

1. Register an app at [Azure Portal](https://portal.azure.com):
   - Account type: "Personal Microsoft accounts only"
   - Platform: Web
   - Redirect URI: `http://localhost:8000/auth/microsoft/callback`
   - Add Graph delegated permissions: `User.Read`, `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, `Tasks.ReadWrite`, `Files.Read`

2. Set environment variables:
   ```bash
   export MSGRAPH_CLIENT_ID="your-client-id"
   export MSGRAPH_CLIENT_SECRET="your-client-secret"
   ```

3. Copilot CLI auto-discovers auth via `/.well-known/oauth-protected-resource` — no special config needed.

## Credential Persistence

The server persists MCP tokens, client registrations, and the MSAL token cache to disk so that users do not need to re-authenticate after a server restart.

| Variable | Default | Description |
|---|---|---|
| `MSGRAPH_CACHE_DIR` | `.local/cache` | Directory where credential files are stored. On Azure App Service this is set to `/home/msgraph-mcp-cache` (persistent across restarts). |

Stored files:

- `credentials.json` — MCP registered clients, access tokens, and refresh tokens.
- `msal_cache.json` — Microsoft identity platform token cache.

Both files are written atomically and with restrictive permissions (`0o600`). Expired tokens are automatically filtered out when loaded.

## Deployment

The server is deployed to Azure App Service via GitHub Actions on push to `main`.

- **Infrastructure**: Bicep template in `infra/main.bicep`
- **Live endpoint**: `https://msgraph-mcp.azurewebsites.net/mcp`

## License

TBD
