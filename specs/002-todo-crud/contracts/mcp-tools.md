# MCP Tool Contracts: To-Do Task CRUD

**Feature Branch**: `002-todo-crud`
**Date**: 2026-03-29

## Overview

Five MCP tools are added to `server.py` for CRUD operations on Microsoft To Do tasks. All tools require the user to be authenticated via the existing OAuth flow. All tools return plain-text string responses suitable for AI assistant consumption.

---

## `list_task_lists`

**Purpose**: Retrieve all of the user's Microsoft To Do task lists.

**Parameters**: None

**Returns**: Formatted string listing all task lists with their IDs and display names.

**Example response**:
```
Found 3 task lists:

1. Tasks (id: AAMkADI...)
2. Shopping (id: AAMkADJ...)
3. Work Projects (id: AAMkADK...)
```

**Graph API call**: `GET /me/todo/lists`

**Error cases**:
- Authentication failure → `"Authentication failed. Please re-authenticate."`
- Graph service error → `"Microsoft Graph service error. Please try again later."`

---

## `list_tasks`

**Purpose**: Retrieve all tasks in a specific task list.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `list_id` | `str` | Yes | The ID of the task list to retrieve tasks from |

**Returns**: Formatted string listing all tasks with their key fields.

**Example response**:
```
Found 2 tasks in list:

1. Buy groceries
   ID: AAkALgAA...
   Status: notStarted
   Importance: normal
   Due: 2024-01-20

2. Call dentist
   ID: AAkALgBB...
   Status: completed
   Importance: high
   Due: none
```

**Graph API call**: `GET /me/todo/lists/{list_id}/tasks`

**Error cases**:
- List not found → `"Not found: the specified task list does not exist."`
- Authentication failure → `"Authentication failed. Please re-authenticate."`

---

## `create_task`

**Purpose**: Create a new task in a specified (or default) task list.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | `str` | Yes | — | Title of the new task |
| `list_id` | `str \| None` | No | `None` | Task list ID. If omitted, uses the default task list. |
| `due_date` | `str \| None` | No | `None` | Due date in `YYYY-MM-DD` format |
| `body` | `str \| None` | No | `None` | Body/description text for the task |

**Returns**: Formatted string confirming the created task with its assigned ID.

**Example response**:
```
Task created successfully:

Title: Buy groceries
ID: AAkALgCC...
List: Tasks
Due: 2024-01-20
```

**Graph API call**: `POST /me/todo/lists/{list_id}/tasks`

**Request body** (example):
```json
{
  "title": "Buy groceries",
  "body": { "content": "Milk, eggs, bread", "contentType": "text" },
  "dueDateTime": { "dateTime": "2024-01-20T00:00:00.0000000", "timeZone": "UTC" }
}
```

**Default list resolution**: When `list_id` is `None`, call `GET /me/todo/lists` and select the list where `wellknownListName == "defaultList"`. If no such list is found, use the first list returned.

**Error cases**:
- Missing title → MCP framework validation error (title is required)
- Invalid due date format → `"Invalid due date format. Please use YYYY-MM-DD."`
- List not found → `"Not found: the specified task list does not exist."`

---

## `update_task`

**Purpose**: Update an existing task's properties.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `list_id` | `str` | Yes | — | The task list ID containing the task |
| `task_id` | `str` | Yes | — | The ID of the task to update |
| `title` | `str \| None` | No | `None` | New title for the task |
| `status` | `str \| None` | No | `None` | New status: `"notStarted"` or `"completed"` |
| `due_date` | `str \| None` | No | `None` | New due date in `YYYY-MM-DD` format |
| `body` | `str \| None` | No | `None` | New body/description text |
| `importance` | `str \| None` | No | `None` | New importance: `"low"`, `"normal"`, or `"high"` |

**Returns**: Formatted string confirming the updated task.

**Example response**:
```
Task updated successfully:

Title: Buy groceries (updated)
ID: AAkALgCC...
Status: completed
Importance: high
```

**Graph API call**: `PATCH /me/todo/lists/{list_id}/tasks/{task_id}`

**Request body**: Only includes fields that are not `None`. Example:
```json
{
  "title": "Buy groceries (updated)",
  "status": "completed"
}
```

**Validation**:
- At least one optional field must be provided (otherwise nothing to update).
- `status` must be `"notStarted"` or `"completed"` if provided.
- `importance` must be `"low"`, `"normal"`, or `"high"` if provided.

**Error cases**:
- No update fields provided → `"No updates specified. Provide at least one field to update."`
- Task not found → `"Not found: the specified task does not exist."`
- Invalid status value → `"Invalid status. Must be 'notStarted' or 'completed'."`
- Invalid importance value → `"Invalid importance. Must be 'low', 'normal', or 'high'."`

---

## `delete_task`

**Purpose**: Permanently delete a task from a task list.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `list_id` | `str` | Yes | The task list ID containing the task |
| `task_id` | `str` | Yes | The ID of the task to delete |

**Returns**: Confirmation string.

**Example response**:
```
Task deleted successfully.
```

**Graph API call**: `DELETE /me/todo/lists/{list_id}/tasks/{task_id}`

**Error cases**:
- Task not found → `"Not found: the specified task does not exist."`
- Authentication failure → `"Authentication failed. Please re-authenticate."`

---

## Common Patterns

### Authentication Flow (all tools)

```python
# 1. Get MCP bearer token from request context
mcp_token = ...  # extracted from Context or request

# 2. Map to user email
user_email = auth_provider.get_user_email_for_token(mcp_token)

# 3. Get Microsoft Graph token
ms_token = auth_provider.get_microsoft_token(user_email)

# 4. Call Graph API with httpx
response = await client.get(url, headers={"Authorization": f"Bearer {ms_token}"})
```

### Response Formatting

All tools return human-readable plain text, not JSON. The AI assistant can parse and present the information naturally. IDs are included so the user (or AI) can reference them in follow-up operations.
