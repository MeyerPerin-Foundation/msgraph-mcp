# Data Model: To-Do Task CRUD

**Feature Branch**: `002-todo-crud`
**Date**: 2026-03-29

## Overview

This feature does not introduce local data models or database tables. All data lives in Microsoft Graph and is accessed via REST API calls. The entities below describe the Graph API resource shapes that the MCP tools consume and produce.

## Entities

### TaskList

Represents a Microsoft To Do task list belonging to the authenticated user.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Opaque identifier assigned by Graph API |
| `displayName` | `str` | User-visible name of the list (e.g., "Tasks", "Shopping") |

**Graph API resource**: `todoTaskList`
**Endpoint**: `GET /me/todo/lists`

**Notes**:
- Every personal Microsoft account has at least one default list (`wellknownListName == "defaultList"`).
- Lists cannot be created or deleted through this feature (out of scope).

---

### Task

Represents a single to-do item within a task list.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Opaque identifier assigned by Graph API |
| `title` | `str` | Title of the task |
| `body` | `str \| None` | Text content of the task body (from `body.content`) |
| `status` | `str` | `"notStarted"` or `"completed"` |
| `importance` | `str` | `"low"`, `"normal"`, or `"high"` |
| `dueDateTime` | `str \| None` | Due date as ISO date string (extracted from `dueDateTime.dateTime`) |
| `createdDateTime` | `str` | Creation timestamp as ISO datetime string |

**Graph API resource**: `todoTask`
**Endpoint**: `GET /me/todo/lists/{listId}/tasks`

**Notes**:
- `body` uses a nested `{ content, contentType }` structure in Graph API. We only read/write the `content` field and assume `contentType: "text"`.
- `dueDateTime` uses a nested `{ dateTime, timeZone }` structure in Graph API. When setting a due date, we send `{ dateTime: "<date>T00:00:00.0000000", timeZone: "UTC" }`.
- `status` only supports two values: `"notStarted"` and `"completed"`. There is no "in progress" state in the Graph To Do API.
- Attachments, linked resources, and checklist items are out of scope for this feature.

## Relationships

```
User (authenticated)
 └── TaskList (1:many)
      └── Task (1:many)
```

A user owns multiple task lists. Each task list contains multiple tasks. All access is scoped to the authenticated user via the `Tasks.ReadWrite` permission.

## No Local Storage

All state is managed by Microsoft Graph. The MCP server is stateless with respect to task data — it acts purely as a passthrough between the AI client and the Graph API.
