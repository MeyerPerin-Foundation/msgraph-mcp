"""MCP server with Microsoft OAuth authentication."""

import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from msgraph_mcp.auth import MicrosoftOAuthProvider
from msgraph_mcp.config import MCP_REQUIRED_SCOPES, MSGRAPH_CACHE_DIR, MSGRAPH_CLIENT_ID, MSGRAPH_SERVER_URL
from msgraph_mcp.graph import GraphApiError, GraphClient
from msgraph_mcp.store import CredentialStore

# Initialize the credential store and OAuth provider
credential_store = CredentialStore(MSGRAPH_CACHE_DIR)
auth_provider = MicrosoftOAuthProvider(store=credential_store)

# Configure FastMCP with MCP-native OAuth (only if client ID is set)
mcp_kwargs: dict = {"name": "msgraph-mcp", "host": "0.0.0.0", "port": 8000}

if MSGRAPH_CLIENT_ID:
    mcp_kwargs["auth"] = AuthSettings(
        issuer_url=AnyHttpUrl(MSGRAPH_SERVER_URL),
        resource_server_url=AnyHttpUrl(MSGRAPH_SERVER_URL),
        required_scopes=list(MCP_REQUIRED_SCOPES),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=list(MCP_REQUIRED_SCOPES),
            default_scopes=list(MCP_REQUIRED_SCOPES),
        ),
    )
    mcp_kwargs["auth_server_provider"] = auth_provider

mcp = FastMCP(**mcp_kwargs)


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the message sent by the user."""
    return f"[MSGRAPH-MCP]: {message}"


# ── Graph client helper ──────────────────────────────────────────────


async def _get_graph_client() -> GraphClient:
    """Get a GraphClient authenticated as the current MCP user.

    Uses the auth context set by the bearer auth middleware to identify
    the current user and obtain a Microsoft Graph token.
    """
    access_token = get_access_token()
    if not access_token:
        raise ValueError("Authentication required")

    mcp_token = access_token.token

    # Look up the user email for this MCP token.
    # First try the direct dict lookup.
    user_email = auth_provider.get_user_email_for_token(mcp_token)

    # Fallback: scan all access tokens for a matching token field.
    # This handles cases where the dict key and token field diverge
    # after serialization round-trips.
    if not user_email:
        for _key, (at, email) in auth_provider.access_tokens.items():
            if at.token == mcp_token:
                user_email = email
                break

    if not user_email:
        raise ValueError("No user found for token. Please re-authenticate.")

    ms_token = await auth_provider.get_microsoft_token(user_email)
    return GraphClient(ms_token)


def _validate_date(due_date: str) -> bool:
    """Validate that a date string is in YYYY-MM-DD format."""
    try:
        datetime.date.fromisoformat(due_date)
        return True
    except ValueError:
        return False


# ── To-Do tools ───────────────────────────────────────────────────────


@mcp.tool()
async def list_task_lists() -> str:
    """List all Microsoft To-Do task lists for the authenticated user."""
    try:
        client = await _get_graph_client()
    except (ValueError, RuntimeError) as exc:
        return str(exc)

    try:
        lists = await client.get_task_lists()
    except GraphApiError as exc:
        return exc.message

    if not lists:
        return "No task lists found."

    lines = ["Task Lists:", ""]
    for tl in lists:
        name = tl.get("displayName", "Untitled")
        list_id = tl.get("id", "?")
        wellknown = tl.get("wellknownListName", "")
        suffix = " (default)" if wellknown == "defaultList" else ""
        lines.append(f"- {name}{suffix}  [id: {list_id}]")
    return "\n".join(lines)


@mcp.tool()
async def list_tasks(list_id: str) -> str:
    """List all tasks in a Microsoft To-Do task list.

    Args:
        list_id: The ID of the task list to retrieve tasks from.
    """
    try:
        client = await _get_graph_client()
    except (ValueError, RuntimeError) as exc:
        return str(exc)

    try:
        tasks = await client.get_tasks(list_id)
    except GraphApiError as exc:
        return exc.message

    if not tasks:
        return "No tasks found in this list."

    lines = ["Tasks:", ""]
    for t in tasks:
        title = t.get("title", "Untitled")
        task_id = t.get("id", "?")
        status = t.get("status", "unknown")
        importance = t.get("importance", "normal")
        due = t.get("dueDateTime")
        due_str = due["dateTime"][:10] if due else "none"
        body = t.get("body", {})
        body_text = body.get("content", "").strip() if body else ""
        body_str = f'  Body: "{body_text}"' if body_text else ""

        lines.append(
            f"- [{status}] {title}  (importance: {importance}, due: {due_str})  [id: {task_id}]{body_str}"
        )
    return "\n".join(lines)


@mcp.tool()
async def create_task(
    title: str,
    list_id: str | None = None,
    due_date: str | None = None,
    body: str | None = None,
) -> str:
    """Create a new task in Microsoft To-Do.

    Args:
        title: The title of the task.
        list_id: The task list ID. Uses the default list if not provided.
        due_date: Optional due date in YYYY-MM-DD format.
        body: Optional task description / notes.
    """
    if due_date and not _validate_date(due_date):
        return f"Invalid due_date format: '{due_date}'. Expected YYYY-MM-DD."

    try:
        client = await _get_graph_client()
    except (ValueError, RuntimeError) as exc:
        return str(exc)

    try:
        if not list_id:
            list_id = await client.get_default_list_id()
        task = await client.create_task(list_id, title, body=body, due_date=due_date)
    except GraphApiError as exc:
        return exc.message

    task_id = task.get("id", "?")
    due = task.get("dueDateTime")
    due_str = f", due: {due['dateTime'][:10]}" if due else ""
    return f"Task created: \"{task.get('title', title)}\" [id: {task_id}]{due_str}"


@mcp.tool()
async def update_task(
    list_id: str,
    task_id: str,
    title: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    body: str | None = None,
    importance: str | None = None,
) -> str:
    """Update a task in Microsoft To-Do.

    Args:
        list_id: The task list ID containing the task.
        task_id: The ID of the task to update.
        title: New title for the task.
        status: New status — "notStarted" or "completed".
        due_date: New due date in YYYY-MM-DD format.
        body: New task description / notes.
        importance: New importance — "low", "normal", or "high".
    """
    # Validate that at least one field is provided
    if all(v is None for v in (title, status, due_date, body, importance)):
        return "No fields provided to update. Specify at least one of: title, status, due_date, body, importance."

    if due_date and not _validate_date(due_date):
        return f"Invalid due_date format: '{due_date}'. Expected YYYY-MM-DD."

    valid_statuses = {"notStarted", "completed"}
    if status and status not in valid_statuses:
        return f"Invalid status: '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}."

    valid_importances = {"low", "normal", "high"}
    if importance and importance not in valid_importances:
        return f"Invalid importance: '{importance}'. Must be one of: {', '.join(sorted(valid_importances))}."

    try:
        client = await _get_graph_client()
    except (ValueError, RuntimeError) as exc:
        return str(exc)

    try:
        task = await client.update_task(
            list_id,
            task_id,
            title=title,
            status=status,
            body=body,
            due_date=due_date,
            importance=importance,
        )
    except GraphApiError as exc:
        return exc.message

    return f"Task updated: \"{task.get('title', '?')}\" [id: {task.get('id', task_id)}]"


@mcp.tool()
async def delete_task(list_id: str, task_id: str) -> str:
    """Delete a task from Microsoft To-Do.

    Args:
        list_id: The task list ID containing the task.
        task_id: The ID of the task to delete.
    """
    try:
        client = await _get_graph_client()
    except (ValueError, RuntimeError) as exc:
        return str(exc)

    try:
        await client.delete_task(list_id, task_id)
    except GraphApiError as exc:
        return exc.message

    return f"Task deleted successfully. [id: {task_id}]"


async def health(request: Request) -> JSONResponse:
    """Health check endpoint for Azure warmup probe."""
    return JSONResponse({"status": "ok"})


# Register custom routes before building the ASGI app
mcp._custom_starlette_routes.append(Route("/", health))
if MSGRAPH_CLIENT_ID:
    mcp._custom_starlette_routes.append(
        Route("/auth/microsoft/callback", auth_provider.handle_microsoft_callback)
    )

# ASGI app for deployment (streamable HTTP transport)
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
