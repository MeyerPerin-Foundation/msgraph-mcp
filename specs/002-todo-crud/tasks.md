# Tasks: To-Do Task CRUD

**Input**: Design documents from `/specs/002-todo-crud/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md

**Tests**: Included — the constitution requires "Test Before Ship" (Principle IV).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Project scaffolding and shared infrastructure for Graph API tools

- [x] T001 Create `msgraph_mcp/graph.py` with `GraphClient` class: `__init__(token: str)` storing the bearer token, and define `GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"` constant
- [x] T002 Implement `GraphApiError` exception class in `msgraph_mcp/graph.py` with `status_code: int`, `message: str`, and `detail: str | None` fields
- [x] T003 Implement private `_request()` helper in `GraphClient` that makes an httpx async request with `Authorization: Bearer {token}`, raises `GraphApiError` on non-2xx responses mapping HTTP status codes to user-friendly messages per research R4, and handles network errors

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Complete the GraphClient with all CRUD methods before wiring MCP tools

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement `get_task_lists() -> list[dict]` in `msgraph_mcp/graph.py` that calls `GET /me/todo/lists` and returns the `value` array
- [x] T005 Implement `get_tasks(list_id: str) -> list[dict]` in `msgraph_mcp/graph.py` that calls `GET /me/todo/lists/{list_id}/tasks` and returns the `value` array
- [x] T006 Implement `get_default_list_id() -> str` in `msgraph_mcp/graph.py` that calls `get_task_lists()` and returns the ID of the list where `wellknownListName == "defaultList"`, falling back to the first list
- [x] T007 Implement `create_task(list_id: str, title: str, body: str | None, due_date: str | None) -> dict` in `msgraph_mcp/graph.py` that calls `POST /me/todo/lists/{list_id}/tasks` with the appropriate request body including nested `body` and `dueDateTime` structures per data-model.md
- [x] T008 Implement `update_task(list_id: str, task_id: str, **fields) -> dict` in `msgraph_mcp/graph.py` that calls `PATCH /me/todo/lists/{list_id}/tasks/{task_id}` with only the non-None fields, handling nested `body` and `dueDateTime` structures
- [x] T009 Implement `delete_task(list_id: str, task_id: str) -> None` in `msgraph_mcp/graph.py` that calls `DELETE /me/todo/lists/{list_id}/tasks/{task_id}`
- [x] T010 Create `tests/test_graph.py` with unit tests for `GraphClient`: mock httpx responses for all 6 methods (get_task_lists, get_tasks, get_default_list_id, create_task, update_task, delete_task); test error handling for 401, 404, and 5xx responses; test `GraphApiError` exception fields; test due date formatting and body content nesting; test empty `value` array (no task lists / no tasks) returns empty list

**Checkpoint**: `GraphClient` module ready — MCP tool wiring can now begin

---

## Phase 3: User Story 1 — View My Tasks (Priority: P1) 🎯 MVP

**Goal**: Users can list their task lists and see tasks within a list from Copilot CLI.

**Independent Test**: Ask the AI assistant to list task lists, then list tasks in a specific list.

### Implementation for User Story 1

- [x] T011 [US1] Implement helper function `_get_graph_client(ctx: Context) -> GraphClient` in `msgraph_mcp/server.py` that extracts the MCP bearer token from the request context, maps it to a user email via `auth_provider.get_user_email_for_token()`, gets the Microsoft token via `auth_provider.get_microsoft_token()`, and returns a `GraphClient` instance. Handle errors (no token, no user, token refresh failure) by raising a descriptive MCP error.
- [x] T012 [US1] Add `list_task_lists` MCP tool in `msgraph_mcp/server.py` that uses `_get_graph_client()` and `GraphClient.get_task_lists()` to return a formatted string listing all task lists with IDs and display names, catching `GraphApiError` and returning its message
- [x] T013 [US1] Add `list_tasks` MCP tool in `msgraph_mcp/server.py` with parameter `list_id: str` that uses `GraphClient.get_tasks()` to return a formatted string listing tasks with title, ID, status, importance, and due date, catching `GraphApiError`
- [x] T014 [P] [US1] Add tests in `tests/test_tools.py` for `list_task_lists` and `list_tasks`: mock `auth_provider` and `GraphClient` to verify tools return correctly formatted output and handle errors gracefully; test empty task list response; test token-refresh-failure path (mock `get_microsoft_token` raising `RuntimeError`)

**Checkpoint**: After this phase, users can view their tasks. This is the MVP.

---

## Phase 4: User Story 2 — Create Tasks (Priority: P2)

**Goal**: Users can create new to-do items from Copilot CLI.

**Independent Test**: Ask the assistant to create a task, verify it appears in the task list.

### Implementation for User Story 2

- [x] T015 [US2] Add `create_task` MCP tool in `msgraph_mcp/server.py` with parameters `title: str`, `list_id: str | None = None`, `due_date: str | None = None`, `body: str | None = None`. When `list_id` is None, use `GraphClient.get_default_list_id()`. Validate `due_date` format if provided. Return formatted confirmation with created task details. Catch `GraphApiError`.
- [x] T016 [P] [US2] Add tests in `tests/test_tools.py` for `create_task`: test with all parameters, test with only title, test default list resolution, test invalid due date format error

**Checkpoint**: After this phase, users can view AND create tasks.

---

## Phase 5: User Story 3 — Update Tasks (Priority: P3)

**Goal**: Users can update task properties (mark complete, change title, set due date) from Copilot CLI.

**Independent Test**: Create a task, mark it complete, verify status changed.

### Implementation for User Story 3

- [x] T017 [US3] Add `update_task` MCP tool in `msgraph_mcp/server.py` with parameters `list_id: str`, `task_id: str`, `title: str | None = None`, `status: str | None = None`, `due_date: str | None = None`, `body: str | None = None`, `importance: str | None = None`. Validate status is `"notStarted"` or `"completed"` if provided. Validate importance is `"low"`, `"normal"`, or `"high"` if provided. Return error if no fields provided. Return formatted confirmation. Catch `GraphApiError`.
- [x] T018 [P] [US3] Add tests in `tests/test_tools.py` for `update_task`: test marking complete, test changing title, test setting due date, test invalid due date format error, test no-fields-provided error, test invalid status/importance validation

**Checkpoint**: After this phase, users can view, create, AND update tasks.

---

## Phase 6: User Story 4 — Delete Tasks (Priority: P4)

**Goal**: Users can delete tasks they no longer need from Copilot CLI.

**Independent Test**: Create a task, delete it, verify it no longer appears.

### Implementation for User Story 4

- [x] T019 [US4] Add `delete_task` MCP tool in `msgraph_mcp/server.py` with parameters `list_id: str`, `task_id: str`. Call `GraphClient.delete_task()`. Return confirmation string. Catch `GraphApiError` and return "not found" message for 404.
- [x] T020 [P] [US4] Add tests in `tests/test_tools.py` for `delete_task`: test successful deletion, test task-not-found error

**Checkpoint**: All four user stories are complete and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and cleanup

- [x] T021 [P] Update `README.md` to document the 5 new MCP tools with brief descriptions and example usage
- [x] T022 Run all tests (`uv run pytest -q`) and lint (`uv run ruff check .`) to confirm no regressions
- [x] T023 Run `quickstart.md` validation: authenticate → list task lists → create a task → list tasks → update task → delete task (manual or scripted end-to-end test)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (GraphClient class and error types) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 (get_task_lists, get_tasks methods)
- **US2 (Phase 4)**: Depends on Phase 2 + T011 from US1 (needs `_get_graph_client` helper)
- **US3 (Phase 5)**: Depends on Phase 2 + T011 from US1
- **US4 (Phase 6)**: Depends on Phase 2 + T011 from US1
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. Creates the `_get_graph_client` helper that US2–US4 reuse.
- **US2 (P2)**: Depends on T011 from US1 (the helper). Can run after US1's T011 is complete.
- **US3 (P3)**: Depends on T011 from US1. Can run in parallel with US2.
- **US4 (P4)**: Depends on T011 from US1. Can run in parallel with US2/US3.

### Within Each User Story

- Tool implementation before tests
- Tests marked [P] can run in parallel with other stories' tests
- Story complete before moving to next priority

### Parallel Opportunities

- T014, T016, T018, T020 (all test tasks) are in the same file but test different tools — can be written in parallel
- US2, US3, US4 tool implementations are independent (different tool functions in server.py) — can run in parallel after T011

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T010)
3. Complete Phase 3: User Story 1 (T011–T014)
4. **STOP and VALIDATE**: Authenticate → list task lists → list tasks
5. Deploy and verify on Azure

### Incremental Delivery

1. Setup + Foundational → GraphClient ready
2. Add US1 → View tasks → Deploy (MVP!)
3. Add US2 → Create tasks → Deploy
4. Add US3 → Update tasks → Deploy
5. Add US4 → Delete tasks → Deploy
6. Polish → Docs, final validation

---

## Notes

- [P] tasks = different files or independent functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each phase or logical group
- The GraphClient has zero new dependencies — httpx is already in pyproject.toml
- All tools return plain-text strings, not JSON — designed for AI assistant consumption
