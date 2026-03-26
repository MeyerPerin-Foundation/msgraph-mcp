# Tasks: Persistent Credential Cache

**Input**: Design documents from `/specs/001-persistent-credentials/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/credential-store.md

**Tests**: Included — the constitution requires "Test Before Ship" (Principle IV).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Add configuration and project scaffolding for credential persistence

- [x] T001 Add `MSGRAPH_CACHE_DIR` environment variable to `msgraph_mcp/config.py` with sensible defaults (Azure: `/home/msgraph-mcp-cache`, local: `.local/cache`)
- [x] T002 [P] Add `MSGRAPH_CACHE_DIR` app setting to `infra/main.bicep` with value `/home/msgraph-mcp-cache`
- [x] T003 [P] Add `.local/cache/` to `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the `CredentialStore` persistence module that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create `msgraph_mcp/store.py` with `CredentialStore` class: `__init__(cache_dir: Path)` that creates the cache directory with `0o700` permissions, and defines file paths for `credentials.json` and `msal_cache.json`
- [x] T005 Implement atomic write helper `_atomic_write(path: Path, data: str)` in `msgraph_mcp/store.py` using temp file + `os.replace()` with `0o600` file permissions
- [x] T006 Implement `_load_json(path: Path) -> dict` in `msgraph_mcp/store.py` that reads JSON from file, returns empty dict on any error (missing, corrupt, permission), and logs a warning on failure
- [x] T007 Implement `save_credentials()` in `msgraph_mcp/store.py` that serializes registered clients, access tokens (with user email), and refresh tokens into a single `credentials.json` using Pydantic `model_dump(mode="json")` and the `_atomic_write` helper
- [x] T008 Implement `load_credentials()` in `msgraph_mcp/store.py` that deserializes `credentials.json` back into `registered_clients`, `access_tokens`, and `refresh_tokens` dicts using Pydantic `model_validate()`, filtering out expired tokens
- [x] T009 Implement `save_msal_cache(cache: SerializableTokenCache)` in `msgraph_mcp/store.py` that calls `cache.serialize()` and writes to `msal_cache.json` via `_atomic_write`, only if `cache.has_state_changed`
- [x] T010 Implement `load_msal_cache() -> SerializableTokenCache` in `msgraph_mcp/store.py` that reads `msal_cache.json` and calls `cache.deserialize()`, returning a fresh empty cache on any error
- [x] T011 Implement `save_all(provider)` convenience method in `msgraph_mcp/store.py` that saves clients, access tokens, refresh tokens, and MSAL cache in one call
- [x] T012 Create `tests/test_store.py` with unit tests for `CredentialStore`: test save/load round-trip for clients, access tokens, refresh tokens, and MSAL cache; test expired token filtering on load; test graceful handling of corrupt files; test graceful handling of read-only/full storage (write failure); test atomic write does not corrupt on simulated failure; test directory and file permissions; test that `pending_flows` and `auth_codes` are NOT present in `credentials.json` after `save_all()` (FR-005 negative test)

**Checkpoint**: `CredentialStore` module ready — user story integration can now begin

---

## Phase 3: User Story 1 — Survive Server Restarts (Priority: P1) 🎯 MVP

**Goal**: MCP access tokens, refresh tokens, and MSAL Graph tokens survive server restarts so users do not need to re-authenticate.

**Independent Test**: Authenticate, restart the server process, verify that a previously issued MCP token still works for tool calls.

### Implementation for User Story 1

- [x] T013 [US1] Modify `MicrosoftOAuthProvider.__init__()` in `msgraph_mcp/auth.py` to accept an optional `CredentialStore`, and if provided, call `load_credentials()` to hydrate `access_tokens` and `refresh_tokens`, and `load_msal_cache()` to hydrate `_msal_cache` + rebuild `_msal_app` with the loaded cache
- [x] T014 [US1] Add persistence hook in `exchange_authorization_code()` in `msgraph_mcp/auth.py`: after issuing tokens, call `self._store.save_all(self)` if store is set
- [x] T015 [US1] Add persistence hook in `exchange_refresh_token()` in `msgraph_mcp/auth.py`: after rotating tokens, call `self._store.save_all(self)`
- [x] T016 [US1] Add persistence hook in `revoke_token()` in `msgraph_mcp/auth.py`: after removing tokens, call `self._store.save_all(self)`
- [x] T017 [US1] Add persistence hook in `handle_microsoft_callback()` in `msgraph_mcp/auth.py`: after MSAL token acquisition succeeds, call `self._store.save_all(self)` to persist the updated MSAL cache
- [x] T018 [US1] Update `msgraph_mcp/server.py` to instantiate `CredentialStore(cache_dir)` using the configured `MSGRAPH_CACHE_DIR` and pass it to `MicrosoftOAuthProvider(store=...)`
- [x] T019 [US1] Update `tests/conftest.py` to add a `tmp_cache_dir` fixture using `tmp_path` and patch `MSGRAPH_CACHE_DIR`
- [x] T020 [US1] Add tests in `tests/test_auth.py` for token persistence round-trip: issue tokens → save → create new provider with same store → verify tokens are loaded and valid

**Checkpoint**: After this phase, tokens survive restarts. This is the MVP — test independently.

---

## Phase 4: User Story 2 — Reconnect Without Browser Login (Priority: P2)

**Goal**: Dynamically registered MCP clients survive server restarts so Copilot CLI does not get "Client ID not found" errors.

**Independent Test**: Register a client, restart the server, verify the server still recognizes the client ID.

### Implementation for User Story 2

- [x] T021 [US2] Add persistence hook in `register_client()` in `msgraph_mcp/auth.py`: after storing client, call `self._store.save_all(self)`
- [x] T022 [US2] Verify that `load_credentials()` in `msgraph_mcp/store.py` correctly deserializes `OAuthClientInformationFull` with all fields (redirect_uris, scope, grant_types, etc.) — add targeted round-trip test in `tests/test_store.py`
- [x] T023 [US2] Add test in `tests/test_auth.py` for client registration persistence: register client → save → create new provider with same store → verify `get_client()` returns the registered client

**Checkpoint**: After this phase, both tokens AND client registrations survive restarts.

---

## Phase 5: User Story 3 — Graceful Cache Expiry (Priority: P3)

**Goal**: Expired and revoked credentials are automatically cleaned up when loaded from persistent storage.

**Independent Test**: Create credentials with short TTLs, wait for them to expire, reload, and verify they are discarded.

### Implementation for User Story 3

- [x] T024 [US3] Verify that `load_credentials()` in `msgraph_mcp/store.py` filters out access tokens where `expires_at < time.time()` — add explicit test in `tests/test_store.py` with a mix of expired and valid tokens
- [x] T025 [US3] Verify that `load_credentials()` in `msgraph_mcp/store.py` filters out refresh tokens where `expires_at < time.time()` — add explicit test in `tests/test_store.py`
- [x] T026 [US3] Add test in `tests/test_store.py` confirming that a revoked token (removed from in-memory state) is not present in the persisted file after `save_all()`

**Checkpoint**: All three user stories are complete and independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, deployment, and final validation

- [x] T027 [P] Update `README.md` to document `MSGRAPH_CACHE_DIR` configuration and persistence behavior
- [x] T028 [P] Add `MSGRAPH_CACHE_DIR` to the `Production` GitHub environment variables via `gh variable set` or document that it should be set
- [x] T029 Run all tests (`uv run pytest -q`) and lint (`uv run ruff check .`) to confirm no regressions
- [x] T030 Run `quickstart.md` validation: authenticate → restart → verify tool call works without re-auth (manual or scripted)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (config) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 2 completion; can run in parallel with US1
- **US3 (Phase 5)**: Depends on Phase 2 completion; can run in parallel with US1/US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — No dependencies on other stories
- **US2 (P2)**: Can start after Phase 2 — Independent of US1
- **US3 (P3)**: Can start after Phase 2 — Independent of US1/US2

### Within Each User Story

- Provider integration (auth.py) before server wiring (server.py)
- Implementation before tests (tests validate the integration)
- Story complete before moving to next priority

### Parallel Opportunities

- T002 and T003 can run in parallel with T001 (different files)
- US1 and US2 provider hooks touch the same file (auth.py) — run sequentially
- US3 tasks (T024–T026) are all in test_store.py and can run after Phase 2

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T012)
3. Complete Phase 3: User Story 1 (T013–T020)
4. **STOP and VALIDATE**: Test that tokens survive a restart
5. Deploy and verify on Azure

### Incremental Delivery

1. Setup + Foundational → CredentialStore ready
2. Add US1 → Tokens survive restarts → Deploy (MVP!)
3. Add US2 → Client registrations survive → Deploy
4. Add US3 → Expired tokens auto-cleaned → Deploy
5. Polish → Docs, deployment config, final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The store module has zero external dependencies — only stdlib + Pydantic + msal (already in the project)
