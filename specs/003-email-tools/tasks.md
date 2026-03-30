# Tasks: Email Tools

**Input**: Design documents from `/specs/003-email-tools/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md

**Tests**: Included — the constitution requires "Test Before Ship" (Principle IV).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Configuration and shared infrastructure for email tools

- [x] T001 Add `Mail.Send` to `GRAPH_SCOPES` in `msgraph_mcp/config.py` (after `Mail.Read`)
- [x] T002 Update module docstring in `msgraph_mcp/graph.py` from "To-Do operations" to "Microsoft Graph API operations"
- [x] T003 Implement `strip_html(html: str) -> str` helper in `msgraph_mcp/graph.py` using stdlib `html.parser.HTMLParser` subclass that extracts text content from HTML and normalizes whitespace (sequential with T002 — same file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add all mail methods to `GraphClient` before wiring MCP tools

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement `get_mail_folders() -> list[dict]` in `msgraph_mcp/graph.py` that calls `GET /me/mailFolders` and returns the `value` array
- [x] T005 Implement `get_messages(folder_id: str | None = None, count: int = 10) -> list[dict]` in `msgraph_mcp/graph.py` that calls `GET /me/messages?$top={count}&$orderby=receivedDateTime desc` (or `/me/mailFolders/{folder_id}/messages?...` if folder_id provided) and returns the `value` array
- [x] T006 Implement `get_message(message_id: str) -> dict` in `msgraph_mcp/graph.py` that calls `GET /me/messages/{message_id}` and returns the message dict
- [x] T007 Implement `search_messages(query: str, count: int = 10) -> list[dict]` in `msgraph_mcp/graph.py` that calls `GET /me/messages?$search="{query}"&$top={count}` and returns the `value` array (note: `$search` cannot be combined with `$orderby`)
- [x] T008 Implement `send_message(to: list[str], subject: str, body: str, cc: list[str] | None = None) -> None` in `msgraph_mcp/graph.py` that calls `POST /me/sendMail` with the appropriate `message` object containing `toRecipients`, `ccRecipients`, `subject`, and `body` per data-model.md. Expects `202 Accepted` with no response body. Note: `_request()` returns the raw response — the caller must not call `.json()` on 202/204 empty-body responses.
- [x] T009 Implement `_extract_body_text(message: dict, max_length: int | None = None) -> str` helper in `msgraph_mcp/graph.py` that extracts plain text from a message's body field: uses `body.content` directly if `contentType == "text"`, applies `strip_html()` if `contentType == "html"`, and truncates to `max_length` chars with `"..."` if specified
- [x] T010 Add mail method tests to `tests/test_graph.py`: mock httpx responses for all 6 new methods (get_mail_folders, get_messages, get_message, search_messages, send_message, _extract_body_text); test folder-specific vs inbox-wide list_messages; test `strip_html` with simple HTML, nested tags, and empty input; test `_extract_body_text` with `max_length=500` on a body exceeding 500 chars verifying `"..."` is appended; test error handling for 401, 403, 404 on mail endpoints; test send_message returns None on 202; test empty results return empty list

**Checkpoint**: All `GraphClient` mail methods ready — MCP tool wiring can now begin

---

## Phase 3: User Story 1 — Read My Inbox (Priority: P1) 🎯 MVP

**Goal**: Users can list their recent emails and read individual messages from Copilot CLI.

**Independent Test**: Ask the AI assistant to list recent emails, then read one by ID.

### Implementation for User Story 1

- [x] T011 [US1] Add `list_messages` MCP tool in `msgraph_mcp/server.py` with parameters `folder_id: str | None = None`, `count: int = 10`. Uses `_get_graph_client()` and `GraphClient.get_messages()`. Formats each message with sender name/address, subject, date, read status, and body preview (truncated to 500 chars via `_extract_body_text`). Catches `GraphApiError`.
- [x] T012 [US1] Add `read_message` MCP tool in `msgraph_mcp/server.py` with parameter `message_id: str`. Uses `GraphClient.get_message()`. Formats full message with sender, all To/CC recipients, subject, date, importance, read status, and complete body text (no truncation). Catches `GraphApiError`.
- [x] T013 [P] [US1] Add tests in `tests/test_tools.py` for `list_messages` and `read_message`: mock `GraphClient` to verify formatted output includes sender, subject, date, body preview; test folder-specific listing; test empty inbox returns clear message; test auth failure path

**Checkpoint**: After this phase, users can read their inbox. This is the MVP.

---

## Phase 4: User Story 2 — Search Emails (Priority: P2)

**Goal**: Users can search emails by keyword from Copilot CLI.

**Independent Test**: Search for a known keyword and verify matching results are returned.

### Implementation for User Story 2

- [x] T014 [US2] Add `search_messages` MCP tool in `msgraph_mcp/server.py` with parameters `query: str`, `count: int = 10`. Uses `GraphClient.search_messages()`. Formats results similarly to `list_messages` with body preview. Returns `"No messages found matching \"{query}\"."` when empty. Catches `GraphApiError`.
- [x] T015 [P] [US2] Add tests in `tests/test_tools.py` for `search_messages`: test with matching results, test empty results message, test error handling

**Checkpoint**: After this phase, users can read AND search their email.

---

## Phase 5: User Story 3 — Send Email (Priority: P3)

**Goal**: Users can send emails from Copilot CLI.

**Independent Test**: Send a test email to the user's own address and verify it arrives.

### Implementation for User Story 3

- [x] T016 [US3] Add `send_message` MCP tool in `msgraph_mcp/server.py` with parameters `to: str`, `subject: str`, `body: str`, `cc: str | None = None`. Validates that `to`, `subject`, and `body` are non-empty. Parses comma-separated email addresses into lists. Validates each address contains `@` and returns a clear error for invalid addresses. Calls `GraphClient.send_message()`. Returns confirmation string with recipients and subject. Catches `GraphApiError`.
- [x] T017 [P] [US3] Add tests in `tests/test_tools.py` for `send_message`: test successful send with confirmation, test with CC recipients, test missing/empty `to` validation, test missing `subject` validation, test missing `body` validation, test invalid email format (no `@`) validation, test 403 permission denied error

**Checkpoint**: After this phase, users can read, search, AND send email.

---

## Phase 6: User Story 4 — List Mail Folders (Priority: P4)

**Goal**: Users can see their mail folders from Copilot CLI.

**Independent Test**: Ask the assistant to list mail folders and verify standard folders appear.

### Implementation for User Story 4

- [x] T018 [US4] Add `list_mail_folders` MCP tool in `msgraph_mcp/server.py`. Uses `_get_graph_client()` and `GraphClient.get_mail_folders()`. Formats each folder with display name, ID, total message count, and unread count. Catches `GraphApiError`.
- [x] T019 [P] [US4] Add tests in `tests/test_tools.py` for `list_mail_folders`: test formatted output with folder names and counts, test empty folders list, test error handling

**Checkpoint**: All four user stories are complete and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and cleanup

- [x] T020 [P] Update `README.md` to document the 5 new email MCP tools with brief descriptions and example usage
- [x] T021 Run all tests (`uv run pytest -q`) and lint (`uv run ruff check .`) to confirm no regressions
- [x] T022 Run `quickstart.md` validation: authenticate → list mail folders → list messages → read message → search messages → send message (manual or scripted end-to-end test)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (config change + strip_html helper) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 (get_messages, get_message methods)
- **US2 (Phase 4)**: Depends on Phase 2 (search_messages method). Independent of US1 — uses `_get_graph_client` already in server.py
- **US3 (Phase 5)**: Depends on Phase 2 (send_message method). Independent of US1/US2.
- **US4 (Phase 6)**: Depends on Phase 2 (get_mail_folders method). Independent of US1/US2/US3.
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. No dependencies on other email stories.
- **US2 (P2)**: Can start after Phase 2. Independent of US1.
- **US3 (P3)**: Can start after Phase 2. Independent of US1/US2.
- **US4 (P4)**: Can start after Phase 2. Independent of US1/US2/US3.

### Within Each User Story

- Tool implementation before tests
- Tests marked [P] can run in parallel with other stories' tests
- Story complete before moving to next priority

### Parallel Opportunities

- T001, T002, T003 are independent (different files/locations) — can run in parallel
- T004–T009 are sequential within graph.py (same file, cumulative methods)
- US1–US4 tool implementations all modify server.py — run sequentially
- T013, T015, T017, T019 (test tasks) are all in test_tools.py — write sequentially but test different tools

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T010)
3. Complete Phase 3: User Story 1 (T011–T013)
4. **STOP and VALIDATE**: Authenticate → list recent emails → read a message
5. Deploy and verify on Azure

### Incremental Delivery

1. Setup + Foundational → GraphClient mail methods ready
2. Add US1 → Read inbox → Deploy (MVP!)
3. Add US2 → Search emails → Deploy
4. Add US3 → Send emails → Deploy
5. Add US4 → List folders → Deploy
6. Polish → Docs, final validation

---

## Notes

- [P] tasks = different files or independent functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each phase or logical group
- No new dependencies — httpx already in pyproject.toml, html.parser is stdlib
- All tools return plain-text strings, not JSON — designed for AI assistant consumption
- `_get_graph_client()` helper already exists in server.py from the To-Do feature — reused directly
- Mail.Send scope already added to Azure app registration — config.py change enables MSAL to request it during consent
