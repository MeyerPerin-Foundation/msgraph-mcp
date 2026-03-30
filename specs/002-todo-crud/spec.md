# Feature Specification: To-Do Task CRUD

**Feature Branch**: `002-todo-crud`  
**Created**: 2026-03-29  
**Status**: Draft  
**Input**: User description: "Create functions that allow me to CRUD to-do items"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View My Tasks (Priority: P1)

As an authenticated user interacting through Copilot CLI, I want to see my to-do tasks so that I can quickly review what I need to work on without opening the Microsoft To Do app.

**Why this priority**: Reading tasks is the most common operation and the foundation for all other stories. Without list/read, update and delete have no context.

**Independent Test**: Can be fully tested by authenticating and asking the AI assistant to list tasks. Delivers immediate value by surfacing the user's task list in the terminal.

**Acceptance Scenarios**:

1. **Given** the user is authenticated, **When** they ask to list their to-do lists, **Then** the system returns the names and identifiers of all their task lists.
2. **Given** the user is authenticated and has tasks in a list, **When** they ask to list tasks in a specific list, **Then** the system returns the task titles, statuses, due dates, importance, and body content for each task.

---

### User Story 2 - Create Tasks (Priority: P2)

As an authenticated user, I want to create new to-do items through the AI assistant so that I can quickly capture tasks without switching to another application.

**Why this priority**: Creating tasks is the second most valuable operation — it lets users act on information from their terminal workflow.

**Independent Test**: Can be tested by asking the assistant to create a task with a title, then verifying the task appears in the user's task list.

**Acceptance Scenarios**:

1. **Given** the user is authenticated and specifies a task title, **When** they ask to create a task, **Then** the system creates the task in the specified (or default) list and returns the created task details.
2. **Given** the user specifies a title and a due date, **When** they create a task, **Then** the task is created with the correct due date set.
3. **Given** the user does not specify a list, **When** they create a task, **Then** the task is created in the user's default task list.

---

### User Story 3 - Update Tasks (Priority: P3)

As an authenticated user, I want to update existing to-do items (mark complete, change title, set due date) so that I can manage my tasks from the terminal.

**Why this priority**: Updating tasks — especially marking them complete — is the natural follow-up after viewing. It completes the core workflow loop.

**Independent Test**: Can be tested by creating a task, updating its title or marking it complete, and verifying the change is reflected.

**Acceptance Scenarios**:

1. **Given** the user specifies a task, **When** they ask to mark it complete, **Then** the task's status is updated to completed.
2. **Given** the user specifies a task and a new title, **When** they ask to update it, **Then** the task's title is changed.
3. **Given** the user specifies a task and a due date, **When** they ask to update it, **Then** the task's due date is changed.

---

### User Story 4 - Delete Tasks (Priority: P4)

As an authenticated user, I want to delete to-do items I no longer need so that my task lists stay clean.

**Why this priority**: Deletion is less frequent than viewing, creating, or updating, but still necessary for list hygiene.

**Independent Test**: Can be tested by creating a task, deleting it, and verifying it no longer appears in the list.

**Acceptance Scenarios**:

1. **Given** the user specifies a task by its identifier, **When** they ask to delete it, **Then** the task is permanently removed from the list.
2. **Given** the user specifies a task that does not exist, **When** they ask to delete it, **Then** the system returns a clear error indicating the task was not found.

---

### Edge Cases

- What happens when the user's Microsoft Graph token has expired and cannot be silently refreshed? The system should return a clear error indicating re-authentication is required.
- What happens when the user tries to access a task list that does not exist? The system should return a "not found" error.
- What happens when the user has no task lists? The system should return an empty list rather than an error.
- What happens when the user has an empty task list (no tasks)? The system should return an empty list rather than an error.
- What happens when the user provides an invalid due date format? The system should return a validation error with the expected format (applies to both create and update).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a tool to list the user's to-do task lists (names and identifiers).
- **FR-002**: System MUST provide a tool to list tasks within a specified task list, including title, status, and due date.
- **FR-003**: System MUST provide a tool to create a new task with at least a title, in a specified or default task list.
- **FR-004**: System MUST provide a tool to update an existing task's title, due date, body, importance, or completion status.
- **FR-005**: System MUST provide a tool to delete a task by its identifier within a specified list.
- **FR-006**: System MUST map each tool directly to Microsoft Graph To Do API calls with minimal transformation (per Constitution Principle I).
- **FR-007**: System MUST use the authenticated user's Microsoft Graph token to make API calls on their behalf.
- **FR-008**: System MUST return clear error messages when Graph API calls fail (not found, unauthorized, rate limited).
- **FR-009**: Each tool MUST require only the `Tasks.ReadWrite` scope (already configured).

### Key Entities

- **Task List**: A named collection of tasks belonging to the user. Has a display name and an identifier.
- **Task**: An individual to-do item within a list. Has a title, body content, due date, importance level, and completion status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can list their task lists and see task details within 5 seconds of asking.
- **SC-002**: Users can create a new task with a title and have it appear in Microsoft To Do immediately.
- **SC-003**: Users can mark a task as complete from the terminal and have the change reflected in Microsoft To Do.
- **SC-004**: Users can delete a task and have it permanently removed from Microsoft To Do.
- **SC-005**: All CRUD operations return meaningful results or error messages — no silent failures.

## Assumptions

- The user has already authenticated with the MCP server via the existing OAuth flow.
- The `Tasks.ReadWrite` scope is already consented (it is part of the existing scope configuration).
- The user has at least one task list in Microsoft To Do (a default list is always present for personal accounts).
- Task identifiers (list IDs, task IDs) are opaque strings provided by the Graph API — the system does not generate its own IDs.
- Batch operations (create/update/delete multiple tasks at once) are out of scope for this feature.
- Task attachments, linked resources, and checklist items (sub-steps) are out of scope for this feature.
