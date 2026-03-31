# Tasks: Calendar Read-Write Wrapper

**Input**: Design documents from `/specs/004-calendar-wrapper/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: Required by constitution principle IV ("Test Before Ship"). All new tools and GraphClient methods must have corresponding tests.
**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Configuration change required for calendar write operations

- [x] T001 Update `GRAPH_SCOPES` in `msgraph_mcp/config.py`: change `"Calendars.Read"` to `"Calendars.ReadWrite"`. This is a single string replacement in the `GRAPH_SCOPES` list.
- [x] T002 [P] Update scope-related assertions in `tests/test_server.py` if any test validates the exact `GRAPH_SCOPES` list. Verify existing tests still pass after the scope change by running `uv run pytest tests/test_server.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No additional foundational work needed. The existing `GraphClient`, `_get_graph_client()`, `GraphApiError`, error handling patterns, and auth infrastructure are already in place. The scope change in Phase 1 is the only prerequisite.

**Checkpoint**: Scope updated — calendar implementation can begin.

---

## Phase 3: User Story 1 + User Story 2 — List & Read Events (Priority: P1) 🎯 MVP

**Goal**: Users can list upcoming calendar events (with optional date-range filtering) and view full details of a specific event.

**Independent Test**: Call `list_events` with and without date range, call `get_event` with a valid ID, verify formatted output contains subject, times, location, and attendees.

### GraphClient Methods

- [x] T003 [P] [US1] Add `get_events(count: int = 10) -> list[dict]` method to `GraphClient` in `msgraph_mcp/graph.py`. Calls `GET /me/events?$top={count}&$orderby=start/dateTime`. Returns `response["value"]`. Follow existing pattern from `get_messages`.
- [x] T004 [P] [US1] Add `get_calendar_view(start: str, end: str, timezone: str = "UTC", count: int = 10) -> list[dict]` method to `GraphClient` in `msgraph_mcp/graph.py`. Calls `GET /me/calendarView?startDateTime={start}&endDateTime={end}&$top={count}&$orderby=start/dateTime` with `Prefer: outlook.timezone="{timezone}"` header. Returns `response["value"]`.
- [x] T005 [P] [US2] Add `get_event(event_id: str) -> dict` method to `GraphClient` in `msgraph_mcp/graph.py`. Calls `GET /me/events/{event_id}`. Returns full event object (not wrapped in `["value"]`). Follow existing pattern from `get_message`.

### MCP Tools

- [x] T006 [US1] Add `list_events(start_date, end_date, count, timezone)` MCP tool in `msgraph_mcp/server.py`. If both `start_date` and `end_date` provided, use `client.get_calendar_view()`; if neither provided, use `client.get_events()`; if only one provided, return validation error. Format output as numbered list with subject, start/end times, location, attendees, and ID. Follow `list_messages` formatting pattern. See `contracts/mcp-tools.md` for output format.
- [x] T007 [US2] Add `get_event(event_id: str)` MCP tool in `msgraph_mcp/server.py`. Format output with subject, start/end times, location, organizer, all-day flag, online meeting link, attendees with response statuses, body text (use `_extract_body_text`), recurrence info, and ID. Follow `read_message` formatting pattern. See `contracts/mcp-tools.md` for output format.

### Tests

- [x] T008 [P] [US1] Add tests for `get_events` and `get_calendar_view` in `tests/test_graph.py`. Test: correct URL/path construction, query parameters, `Prefer` header for calendar view, error mapping (404, 401, network), and response parsing. Follow existing `test_get_messages` pattern with `_mock_response`.
- [x] T009 [P] [US2] Add tests for `get_event` in `tests/test_graph.py`. Test: correct URL with event_id, error on invalid ID (404), auth failure (401). Follow existing `test_get_message` pattern.
- [x] T010 [P] [US1] Add tests for `list_events` tool in `tests/test_tools.py`. Test: success with no filters, success with date range (uses calendar view), validation error when only one of start/end provided, empty result message, auth failure, GraphApiError propagation. Follow existing `test_list_messages` pattern.
- [x] T011 [P] [US2] Add tests for `get_event` tool in `tests/test_tools.py`. Test: success with full event details formatting, invalid event ID error, auth failure. Follow existing `test_read_message` pattern.

**Checkpoint**: MVP complete — users can list and read calendar events. Run `uv run pytest` to verify.

---

## Phase 4: User Story 3 — Create Event (Priority: P2)

**Goal**: Users can create new calendar events with subject, times, location, attendees, and optional online meeting.

**Independent Test**: Call `create_event` with required fields and verify a confirmation message with event ID is returned.

### GraphClient Method

- [x] T012 [US3] Add `create_event(subject, start, end, timezone, location, body, attendees, is_all_day, is_online_meeting) -> dict` method to `GraphClient` in `msgraph_mcp/graph.py`. Build event payload: subject as string, start/end as `{"dateTime": ..., "timeZone": ...}`, body as `{"contentType": "text", "content": ...}`, location as `{"displayName": ...}`, attendees as `[{"emailAddress": {"address": ...}, "type": "required"}]`, isAllDay, isOnlineMeeting. POST to `/me/events`. Return created event object. See `contracts/graph-client.md` for full signature.

### MCP Tool

- [x] T013 [US3] Add `create_event(subject, start_time, end_time, timezone, location, body, attendees, is_all_day, is_online_meeting)` MCP tool in `msgraph_mcp/server.py`. Validate: subject non-empty, start_time and end_time required, start before end. Parse attendees from comma-separated string to list. Format success output with subject, start/end, location, and ID. See `contracts/mcp-tools.md` for output format. Follow `send_message` validation pattern.

### Tests

- [x] T014 [P] [US3] Add tests for `create_event` in `tests/test_graph.py`. Test: correct POST payload construction with all fields, minimal fields (subject + times only), attendee list building, body content type, isAllDay/isOnlineMeeting flags. Follow `test_send_message` pattern.
- [x] T015 [P] [US3] Add tests for `create_event` tool in `tests/test_tools.py`. Test: success with all fields, success with required fields only, missing subject error, missing start/end error, start after end error, invalid attendee email format, auth failure, GraphApiError. Follow `test_send_message` tool test pattern.

**Checkpoint**: Users can list, read, and create events. Run `uv run pytest` to verify.

---

## Phase 5: User Story 4 + User Story 5 — Update & Delete Events (Priority: P3)

**Goal**: Users can update event details and delete events from their calendar.

**Independent Test**: Call `update_event` to change a subject or time, verify confirmation. Call `delete_event`, verify success message.

### GraphClient Methods

- [x] T016 [P] [US4] Add `update_event(event_id, *, subject, start, end, timezone, location, body, attendees, is_online_meeting) -> dict` method to `GraphClient` in `msgraph_mcp/graph.py`. Build PATCH payload with only non-None fields. PATCH to `/me/events/{event_id}`. Return updated event object. Follow `update_task` pattern. See `contracts/graph-client.md`.
- [x] T017 [P] [US5] Add `delete_event(event_id: str) -> None` method to `GraphClient` in `msgraph_mcp/graph.py`. DELETE `/me/events/{event_id}`. Return None. Follow `delete_task` pattern.

### MCP Tools

- [x] T018 [US4] Add `update_event(event_id, subject, start_time, end_time, timezone, location, body, attendees, is_online_meeting)` MCP tool in `msgraph_mcp/server.py`. Validate: at least one field provided, start before end if both given. Parse attendees from comma-separated string. Format success output with subject and ID. See `contracts/mcp-tools.md`. Follow `update_task` tool pattern.
- [x] T019 [US5] Add `delete_event(event_id: str)` MCP tool in `msgraph_mcp/server.py`. Return `"Event deleted successfully."` on success. Follow `delete_task` tool pattern.

### Tests

- [x] T020 [P] [US4] Add tests for `update_event` in `tests/test_graph.py`. Test: PATCH payload includes only non-None fields, correct URL with event_id, error mapping. Follow `test_update_task` pattern.
- [x] T021 [P] [US5] Add tests for `delete_event` in `tests/test_graph.py`. Test: correct DELETE URL, 404 error, auth failure. Follow `test_delete_task` pattern.
- [x] T022 [P] [US4] Add tests for `update_event` tool in `tests/test_tools.py`. Test: success updating subject, success updating time, no fields provided error, start after end error, invalid event ID, auth failure. Follow `test_update_task` tool test pattern.
- [x] T023 [P] [US5] Add tests for `delete_event` tool in `tests/test_tools.py`. Test: success message, invalid event ID error, auth failure. Follow `test_delete_task` tool test pattern.

**Checkpoint**: Full CRUD complete. Run `uv run pytest` to verify.

---

## Phase 6: User Story 6 — List Calendars (Priority: P3)

**Goal**: Users can see all their available calendars with names and IDs.

**Independent Test**: Call `list_calendars`, verify formatted list includes calendar names, IDs, and default indicator.

### GraphClient Method

- [x] T024 [US6] Add `get_calendars() -> list[dict]` method to `GraphClient` in `msgraph_mcp/graph.py`. Calls `GET /me/calendars`. Returns `response["value"]`. Follow `get_task_lists` pattern.

### MCP Tool

- [x] T025 [US6] Add `list_calendars()` MCP tool in `msgraph_mcp/server.py`. Format output as list with name, `(default)` indicator for `isDefaultCalendar=True`, and ID. See `contracts/mcp-tools.md`. Follow `list_task_lists` formatting pattern.

### Tests

- [x] T026 [P] [US6] Add tests for `get_calendars` in `tests/test_graph.py`. Test: correct URL, response parsing, error mapping. Follow `test_get_task_lists` pattern.
- [x] T027 [P] [US6] Add tests for `list_calendars` tool in `tests/test_tools.py`. Test: success with multiple calendars, default calendar indicator, single calendar, auth failure, GraphApiError. Follow `test_list_task_lists` tool test pattern.

**Checkpoint**: All CRUD + list calendars complete. Run `uv run pytest` to verify.

---

## Phase 7: User Story 7 — Check Free/Busy Availability (Priority: P3)

**Goal**: Users can query their own free/busy availability for a date range, or check a specific time window.

**Independent Test**: Call `get_availability` with a date range, verify time slots with statuses. Call with `check_only=True`, verify simple free/busy answer.

### GraphClient Method

- [x] T028 [US7] Add `get_schedule(user_email: str, start: str, end: str, timezone: str = "UTC", interval: int = 30) -> dict` method to `GraphClient` in `msgraph_mcp/graph.py`. POST to `/me/calendar/getSchedule` with body: `{"schedules": [user_email], "startTime": {"dateTime": start, "timeZone": timezone}, "endTime": {"dateTime": end, "timeZone": timezone}, "availabilityViewInterval": interval}`. Return first element of `response["value"]`. See `contracts/graph-client.md`.

### MCP Tool

- [x] T029 [US7] Add `get_availability(start_time, end_time, timezone, check_only)` MCP tool in `msgraph_mcp/server.py`. Validate start_time and end_time required, start before end. Get user email via `auth_provider.get_user_email_for_token()`. Call `client.get_schedule(user_email, ...)`. If `check_only=False`: format `scheduleItems` as time slot list with statuses. If `check_only=True`: check if any scheduleItems exist and return simple "You are free/busy" message. See `contracts/mcp-tools.md` for output formats.

### Tests

- [x] T030 [P] [US7] Add tests for `get_schedule` in `tests/test_graph.py`. Test: correct POST payload with user email in schedules array, timezone in startTime/endTime objects, interval parameter, response parsing (first element of value array), error mapping. No direct pattern to follow — this is a new POST-based read.
- [x] T031 [P] [US7] Add tests for `get_availability` tool in `tests/test_tools.py`. Test: success with schedule items (check_only=False), success with no events (all free), success with check_only=True (free window), success with check_only=True (busy window), missing start/end error, start after end error, auth failure, GraphApiError.

**Checkpoint**: All 7 calendar tools complete. Run `uv run pytest` to verify.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [x] T032 Update `README.md` with calendar tools documentation: add `list_calendars`, `list_events`, `get_event`, `create_event`, `update_event`, `delete_event`, `get_availability` to the list of available tools. Update the `Calendars.Read` scope reference to `Calendars.ReadWrite`.
- [x] T033 Run full test suite with `uv run pytest` and verify all tests pass (existing + new).
- [x] T034 Run linter with `uv run ruff check msgraph_mcp/ tests/` and fix any issues.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: N/A — no additional foundational work
- **US1+US2 (Phase 3)**: Depends on Phase 1 — MVP target
- **US3 (Phase 4)**: Depends on Phase 1 — can run in parallel with Phase 3
- **US4+US5 (Phase 5)**: Depends on Phase 1 — can run in parallel with Phase 3/4
- **US6 (Phase 6)**: Depends on Phase 1 — can run in parallel with Phase 3/4/5
- **US7 (Phase 7)**: Depends on Phase 1 — can run in parallel with Phase 3-6
- **Polish (Phase 8)**: Depends on all user story phases

### User Story Dependencies

- **US1 + US2 (P1)**: Independent — no dependencies on other stories
- **US3 (P2)**: Independent — no dependencies on other stories
- **US4 (P3)**: Functionally benefits from US1/US2 (need to find event ID), but implementation is independent
- **US5 (P3)**: Same as US4 — functionally benefits from US1/US2 but implementation is independent
- **US6 (P3)**: Fully independent
- **US7 (P3)**: Fully independent

### Within Each User Story

- GraphClient methods before MCP tools (tools depend on client methods)
- Tests can be written in parallel with implementation (same phase, different files)
- Tests marked [P] can all run in parallel

### Parallel Opportunities

Within Phase 3 (US1+US2):
- T003, T004, T005 can all run in parallel (different methods in same file but non-overlapping)
- T008, T009, T010, T011 can all run in parallel (test files)

Across Phases 3-7:
- All user story phases can run in parallel if team capacity allows
- Each phase touches the same files (graph.py, server.py, test files) so sequential execution is recommended for a single developer

---

## Parallel Example: Phase 3 (US1 + US2)

```text
# Step 1: GraphClient methods (can parallelize across methods)
T003: Add get_events method in msgraph_mcp/graph.py
T004: Add get_calendar_view method in msgraph_mcp/graph.py
T005: Add get_event method in msgraph_mcp/graph.py

# Step 2: MCP tools (depend on step 1)
T006: Add list_events tool in msgraph_mcp/server.py
T007: Add get_event tool in msgraph_mcp/server.py

# Step 3: Tests (can parallelize, depend on step 1-2 for correct assertions)
T008, T009: GraphClient tests in tests/test_graph.py
T010, T011: Tool tests in tests/test_tools.py
```

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 3)

1. Complete Phase 1: Scope upgrade
2. Complete Phase 3: US1 + US2 (list & read events)
3. **STOP and VALIDATE**: Run `uv run pytest`, test list_events and get_event
4. This delivers a functional read-only calendar tool

### Incremental Delivery

1. Phase 1 → Scope ready
2. Phase 3 → MVP: List & read events (P1)
3. Phase 4 → Add create events (P2)
4. Phase 5 → Add update & delete (P3)
5. Phase 6 → Add list calendars (P3)
6. Phase 7 → Add free/busy availability (P3)
7. Phase 8 → Polish, docs, final validation
8. Each phase adds value without breaking previous phases

---

## Notes

- All tasks modify existing files — no new source files created
- Constitution requires tests for all new tools (Principle IV)
- Single developer: execute phases sequentially (P1 → P2 → P3)
- Manual post-deploy step: update Azure app registration for `Calendars.ReadWrite`
