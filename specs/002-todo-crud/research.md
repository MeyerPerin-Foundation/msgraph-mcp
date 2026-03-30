# Research: To-Do Task CRUD

**Feature Branch**: `002-todo-crud`
**Date**: 2026-03-29

## R1: How to Call Graph API from MCP Tools

**Decision**: Use `httpx.AsyncClient` with the Microsoft bearer token obtained from `get_microsoft_token()`.

**Details**:

The existing `MicrosoftOAuthProvider` in `auth.py` provides two key methods:

1. `get_user_email_for_token(mcp_token)` — maps an MCP access token to a user email address.
2. `get_microsoft_token(user_email)` — returns a valid Microsoft Graph API bearer token for that user (handles MSAL silent refresh automatically).

The flow inside each MCP tool is:

```
MCP request → extract MCP bearer token from request headers
            → auth_provider.get_user_email_for_token(mcp_token)
            → auth_provider.get_microsoft_token(user_email)
            → httpx GET/POST/PATCH/DELETE with Authorization: Bearer <ms_token>
```

`httpx` is already a project dependency (`httpx>=0.28.1`). We will create a thin `GraphClient` class in `graph.py` that wraps these httpx calls.

**Why not `msgraph-sdk`?** The SDK adds significant dependency weight and abstractions. A thin httpx wrapper keeps the project aligned with Constitution Principle I (Thin MCP Wrapper).

---

## R2: Graph To Do API Endpoints

**Base URL**: `https://graph.microsoft.com/v1.0`

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List task lists | GET | `/me/todo/lists` |
| Get task list | GET | `/me/todo/lists/{listId}` |
| List tasks | GET | `/me/todo/lists/{listId}/tasks` |
| Get task | GET | `/me/todo/lists/{listId}/tasks/{taskId}` |
| Create task | POST | `/me/todo/lists/{listId}/tasks` |
| Update task | PATCH | `/me/todo/lists/{listId}/tasks/{taskId}` |
| Delete task | DELETE | `/me/todo/lists/{listId}/tasks/{taskId}` |

**Default task list**: When no `list_id` is provided for task creation, the server should first call `GET /me/todo/lists` and use the list where `isOwner == true` and `wellknownListName == "defaultList"` — or simply use the first list returned.

**Pagination**: Graph API returns `@odata.nextLink` for paginated results. For the initial implementation, we will fetch the first page only (default page size is typically sufficient for personal accounts with <100 tasks per list). Pagination support can be added later if needed.

---

## R3: Accessing Authenticated User Context from MCP Tools

**Challenge**: How does an MCP tool function get the current user's identity?

**Investigation**: FastMCP tool functions can accept a `Context` parameter (from `mcp.server.fastmcp`). However, in the current `server.py`, `Context` is not used. The `Context` object provides access to the MCP request context, but it does not directly expose the bearer token from the HTTP request headers.

**Solution**: Since this is a Starlette-based server using streamable HTTP transport, the MCP bearer token is in the HTTP `Authorization` header. The approach is:

1. The `auth_server_provider` on `FastMCP` handles token validation. After validation, the authenticated token information is available in the request context.
2. We need to access the Starlette request to extract the bearer token and map it to a user via `get_user_email_for_token()`.
3. FastMCP's `Context` object has a `request_context` attribute that provides access to transport-level metadata. For streamable HTTP, this includes the lifespan context which can be used to pass the auth provider.
4. Alternatively, since `auth_provider` is a module-level variable in `server.py`, the tool functions can access it directly.

**Chosen approach**: Access the `auth_provider` at module scope and use FastMCP's `Context` to extract the authenticated user's token. The `Context` object's request context carries metadata set during authentication. If direct token extraction from `Context` is not straightforward, we will store a thread-local or context-variable mapping from the MCP session to the authenticated user email during the auth flow.

**Fallback**: If `Context` does not provide direct access to the bearer token, we can use Starlette middleware or a dependency injection pattern to make the current user available to tool functions.

---

## R4: Error Handling Strategy

**Decision**: Map Graph API HTTP errors to descriptive string responses from MCP tools.

MCP tools return strings (not exceptions) to the AI client. The strategy:

| Graph HTTP Status | MCP Tool Response |
|-------------------|-------------------|
| 200-204 | Return formatted result |
| 400 | `"Bad request: {Graph error message}"` |
| 401 | `"Authentication failed. Please re-authenticate."` |
| 403 | `"Access denied. The required permissions may not be granted."` |
| 404 | `"Not found: the specified {resource} does not exist."` |
| 429 | `"Rate limited by Microsoft Graph. Please try again shortly."` |
| 5xx | `"Microsoft Graph service error. Please try again later."` |

The `GraphClient` class will raise a custom `GraphApiError` exception with the status code and message. Each MCP tool will catch this and return a user-friendly string.

For network errors (connection timeout, DNS failure), the tool will return: `"Could not reach Microsoft Graph. Please check your connection."`.

---

## R5: Graph API Response Structure

### Task List Response

```json
{
  "value": [
    {
      "id": "AAMkADI...",
      "displayName": "Tasks",
      "isOwner": true,
      "isShared": false,
      "wellknownListName": "defaultList"
    }
  ]
}
```

**Fields to extract**: `id`, `displayName`

### Task Response

```json
{
  "value": [
    {
      "id": "AAkALgAA...",
      "title": "Buy groceries",
      "body": {
        "content": "Milk, eggs, bread",
        "contentType": "text"
      },
      "status": "notStarted",
      "importance": "normal",
      "isReminderOn": false,
      "createdDateTime": "2024-01-15T10:30:00Z",
      "lastModifiedDateTime": "2024-01-15T10:30:00Z",
      "dueDateTime": {
        "dateTime": "2024-01-20T00:00:00.0000000",
        "timeZone": "UTC"
      },
      "completedDateTime": null
    }
  ]
}
```

**Fields to extract and return**:

| Field | Source Path | Notes |
|-------|-----------|-------|
| `id` | `.id` | Opaque identifier |
| `title` | `.title` | Task title |
| `body` | `.body.content` | Text content of the body |
| `status` | `.status` | `notStarted` or `completed` |
| `importance` | `.importance` | `low`, `normal`, or `high` |
| `due_date` | `.dueDateTime.dateTime` | ISO datetime string (date portion) |
| `created` | `.createdDateTime` | ISO datetime string |

**Note on `dueDateTime`**: The Graph API uses a nested object `{ dateTime: "...", timeZone: "..." }`. When setting a due date, we must send this structure. When reading, we extract just the date portion from `dateTime`.
