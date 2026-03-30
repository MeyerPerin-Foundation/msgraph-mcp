# Quickstart: To-Do Task CRUD

**Feature Branch**: `002-todo-crud`

## Prerequisites

1. The `msgraph-mcp` server is deployed to Azure App Service (or running locally).
2. You have authenticated with your Microsoft personal account through the MCP OAuth flow.
3. The `Tasks.ReadWrite` scope has been consented.

## Usage from Copilot CLI

Once the server is deployed and you are authenticated, you can interact with your Microsoft To Do tasks through natural language. The AI assistant will call the appropriate MCP tools behind the scenes.

### View Your Task Lists

> "Show me my to-do lists"

The assistant calls `list_task_lists` and returns the names and IDs of all your task lists.

### View Tasks in a List

> "What tasks do I have in my Tasks list?"

The assistant calls `list_tasks` with the appropriate list ID and shows your tasks with their titles, statuses, and due dates.

### Create a Task

> "Add a task called 'Buy groceries' to my default list, due January 20th"

The assistant calls `create_task` with:
- `title`: "Buy groceries"
- `due_date`: "2025-01-20"
- `list_id`: None (uses default list)

> "Create a task 'Review PR #42' in my Work Projects list"

The assistant calls `create_task` with the title and the Work Projects list ID.

### Update a Task

> "Mark 'Buy groceries' as completed"

The assistant calls `update_task` with `status: "completed"`.

> "Change the due date of 'Review PR #42' to next Friday"

The assistant calls `update_task` with the new `due_date`.

> "Set 'Buy groceries' to high importance"

The assistant calls `update_task` with `importance: "high"`.

### Delete a Task

> "Delete the 'Buy groceries' task"

The assistant calls `delete_task` with the task's list and task IDs.

## Tips

- **List first**: If you don't know your list IDs, ask to see your task lists first. The assistant will use the returned IDs for follow-up operations.
- **Default list**: When creating tasks, you can omit the list and the task will be added to your default To Do list.
- **Status values**: Tasks are either `notStarted` or `completed` — there is no "in progress" state in Microsoft To Do.
- **Due dates**: Use natural language dates (the assistant converts them) or explicit `YYYY-MM-DD` format.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Authentication failed" | MCP token expired or invalid | Re-authenticate with the MCP server |
| "Not found" on a task | Task ID is stale (task was deleted elsewhere) | List tasks again to get current IDs |
| "Access denied" | `Tasks.ReadWrite` scope not consented | Re-authenticate and consent to the required scope |
| "Rate limited" | Too many requests to Graph API | Wait a moment and retry |
