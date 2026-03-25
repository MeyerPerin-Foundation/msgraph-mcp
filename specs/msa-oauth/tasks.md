# Tasks: MSA OAuth Authentication

**Input**: Design documents from `/specs/msa-oauth/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/auth-routes.md, quickstart.md

**Tests**: Included — Constitution Principle IV requires tests for all new modules.

**Organization**: Single user story (auth infrastructure). Tasks grouped as Setup → Foundational → US1 → Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

## Path Conventions

- **Flat layout**: `msgraph_mcp/` at repository root, `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Add dependencies and configuration infrastructure

- [ ] T001 Add `msal` and `httpx` dependencies to `pyproject.toml` and run `uv sync`
- [ ] T002 [P] Add auth environment variables to `msgraph_mcp/config.py`: `MSGRAPH_CLIENT_ID`, `MSGRAPH_CLIENT_SECRET`, `MSGRAPH_REDIRECT_URI` with validation for missing values
- [ ] T003 [P] Update `infra/main.bicep` to add `MSGRAPH_CLIENT_ID`, `MSGRAPH_CLIENT_SECRET`, `MSGRAPH_REDIRECT_URI` app settings (secret values as empty defaults, set manually in Azure Portal)

**Checkpoint**: Dependencies installed, config module reads all OAuth env vars, Bicep declares new app settings.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core auth provider that MUST be complete before the server can use it

⚠️ **CRITICAL**: US1 integration cannot begin until this phase is complete

- [ ] T004 Create `msgraph_mcp/auth.py` with `MicrosoftOAuthProvider` class skeleton implementing all 9 methods of `OAuthAuthorizationServerProvider` protocol: `get_client`, `register_client`, `authorize`, `load_authorization_code`, `exchange_authorization_code`, `load_refresh_token`, `exchange_refresh_token`, `load_access_token`, `revoke_token`. Initialize in-memory state dicts: `registered_clients`, `pending_flows`, `auth_codes`, `access_tokens`, `refresh_tokens`. Initialize MSAL `ConfidentialClientApplication` using config values with `/consumers` authority
- [ ] T005 Implement `register_client()` and `get_client()` in `msgraph_mcp/auth.py`: store/retrieve `OAuthClientInformationFull` in `registered_clients` dict
- [ ] T006 Implement `authorize()` in `msgraph_mcp/auth.py`: store MCP flow context (`mcp_redirect_uri`, `mcp_code_challenge`, `mcp_state`, `client_id`) in `pending_flows` keyed by a generated `microsoft_state`, build Microsoft authorize URL with scopes `openid profile email offline_access User.Read Mail.Read Calendars.Read Tasks.ReadWrite Files.Read` and PKCE, return the Microsoft URL
- [ ] T007 Create Microsoft callback handler in `msgraph_mcp/auth.py`: async function `handle_microsoft_callback(request: Request)` that (1) looks up `state` in `pending_flows`, (2) calls MSAL `acquire_token_by_authorization_code()` with Microsoft's `code`, (3) extracts user email from ID token `preferred_username` or `email` claim, (4) validates email against `config.is_user_allowed()`, (5) stores Microsoft tokens in MSAL cache, (6) generates MCP auth code (secrets.token_urlsafe(32), >=160 bits), (7) stores `AuthorizationCode` object in `auth_codes` keyed by code string with `user_email` attached, (8) redirects to MCP client's `redirect_uri` with `code` and `state` params. Return 403 if user not allowed, 502 if token exchange fails
- [ ] T008 Implement `load_authorization_code()` and `exchange_authorization_code()` in `msgraph_mcp/auth.py`: look up code in `auth_codes`, verify not expired, return `AuthorizationCode`. Exchange: consume code, generate MCP access token (secrets.token_urlsafe(32)) and refresh token, store in `access_tokens`/`refresh_tokens` mapped to user email, return `OAuthToken`
- [ ] T009 Implement `load_access_token()` in `msgraph_mcp/auth.py`: look up token in `access_tokens`, return `AccessToken` if found and not expired, else None
- [ ] T010 [P] Implement `load_refresh_token()`, `exchange_refresh_token()`, and `revoke_token()` in `msgraph_mcp/auth.py`: refresh rotates both tokens preserving user email mapping; revoke removes from dicts
- [ ] T011 [P] Add `get_microsoft_token(user_email: str)` helper method to `MicrosoftOAuthProvider` in `msgraph_mcp/auth.py`: calls MSAL `acquire_token_silent()` for the user's account, returns Microsoft access token string. Raises if no cached token found

**Checkpoint**: Full `MicrosoftOAuthProvider` implementation ready. All 9 protocol methods + `get_microsoft_token()` helper implemented.

---

## Phase 3: User Story 1 — Server authenticates user and saves token (Priority: P1) 🎯 MVP

**Goal**: Copilot CLI connects to the MCP server, triggers interactive OAuth with Microsoft, server acquires and stores Graph API tokens for tool use.

**Independent Test**: Start server locally, configure Copilot CLI, invoke echo tool — should be prompted to authenticate via browser, then tool call succeeds.

### Tests for User Story 1 ⚠️

- [ ] T012 [P] [US1] Create `tests/conftest.py` with shared fixtures: mock MSAL `ConfidentialClientApplication`, mock `MicrosoftOAuthProvider` with pre-loaded test tokens, test `AuthConfig` with dummy values
- [ ] T013 [P] [US1] Create `tests/test_auth.py` with tests: (1) `register_client` stores and `get_client` retrieves, (2) `authorize` returns Microsoft URL and stores pending flow, (3) `handle_microsoft_callback` with valid code stores tokens and redirects, (4) `handle_microsoft_callback` with disallowed user returns 403, (5) `load_authorization_code` returns stored code, (6) `exchange_authorization_code` consumes code and returns OAuthToken, (7) `load_access_token` returns stored token, (8) `load_access_token` returns None for expired token, (9) `get_microsoft_token` calls MSAL acquire_token_silent

### Implementation for User Story 1

- [ ] T014 [US1] Update `msgraph_mcp/server.py`: import `MicrosoftOAuthProvider` and `AuthSettings`, instantiate provider, configure `FastMCP` with `auth=AuthSettings(issuer_url=server_url, resource_server_url=server_url, required_scopes=["mcp:tools"], client_registration_options=ClientRegistrationOptions(enabled=True))` and `auth_server_provider=provider`
- [ ] T015 [US1] Register `/auth/microsoft/callback` route in `msgraph_mcp/server.py` via `mcp._custom_starlette_routes.append(Route("/auth/microsoft/callback", provider.handle_microsoft_callback))` — must be added BEFORE `mcp.streamable_http_app()` is called
- [ ] T016 [US1] Update `msgraph_mcp/config.py` to expose `MSGRAPH_SERVER_URL` env var (defaults to `http://localhost:8000` for dev, `https://msgraph-mcp.azurewebsites.net` for prod) — used as `issuer_url` and `resource_server_url`
- [ ] T017 [US1] Run all tests with `uv run pytest tests/ -v` and verify all pass
- [ ] T018 [US1] Test locally: start server with `uv run python -m msgraph_mcp.server`, verify `GET /.well-known/oauth-protected-resource` returns metadata, verify `POST /mcp` without Bearer returns 401

**Checkpoint**: Server runs with MCP-native OAuth. Copilot CLI can discover auth, register, authenticate via Microsoft, and call tools with Bearer token. Microsoft Graph token stored server-side for tool use.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Deployment, documentation, and cleanup

- [ ] T019 [P] Update `infra/main.bicep`: set `MSGRAPH_REDIRECT_URI` default to `https://msgraph-mcp.azurewebsites.net/auth/microsoft/callback` and add `MSGRAPH_SERVER_URL` set to `https://msgraph-mcp.azurewebsites.net`
- [ ] T020 [P] Update `specs/msa-oauth/quickstart.md` with final setup instructions reflecting actual implementation
- [ ] T021 [P] Update `README.md` with authentication section: prerequisites (Azure app registration), environment variables, first-time auth flow
- [ ] T022 Deploy to Azure App Service: push to branch, create PR, merge. Set `MSGRAPH_CLIENT_ID` and `MSGRAPH_CLIENT_SECRET` manually in Azure Portal app settings
- [ ] T023 Verify end-to-end: restart Copilot CLI, invoke echo tool against production URL, confirm interactive auth works and tool call succeeds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (dependencies installed). T004-T011 are sequential within the provider, except T010 and T011 which can run in parallel
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion (all provider methods ready)
- **Polish (Phase 4)**: Depends on US1 completion

### Within User Story 1

- Tests (T012, T013) SHOULD be written before implementation but CAN run in parallel with each other
- T014 (server wiring) and T015 (callback route) must come before T017 (test run)
- T018 (manual test) depends on everything else in the phase

### Parallel Opportunities

```bash
# Phase 1 — all can run in parallel after T001:
T002: Config env vars in msgraph_mcp/config.py
T003: Bicep app settings in infra/main.bicep

# Phase 2 — T010 and T011 can run in parallel (different concerns):
T010: Refresh/revoke methods in msgraph_mcp/auth.py
T011: get_microsoft_token helper in msgraph_mcp/auth.py

# Phase 3 — Tests can run in parallel:
T012: conftest.py fixtures
T013: test_auth.py tests

# Phase 4 — Documentation updates can run in parallel:
T019: Bicep updates in infra/main.bicep
T020: Quickstart in specs/msa-oauth/quickstart.md
T021: README.md auth section
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T011) — provider fully implemented
3. Complete Phase 3: User Story 1 (T012-T018) — server wired, tested
4. **STOP and VALIDATE**: Test with Copilot CLI locally
5. Deploy (T022) and verify production (T023)

### Future Increment

After this feature merges, the next feature would add actual Graph API tools (e.g., `read_mail`, `list_events`, `list_tasks`) that use `provider.get_microsoft_token()` to call Graph endpoints. The auth infrastructure built here makes those tools straightforward.

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] = all tasks belong to the single user story
- Total tasks: 23
- Tests included per Constitution Principle IV
- All state is in-memory; server restart requires re-authentication
- `secrets.token_urlsafe(32)` produces 256 bits of entropy (exceeds 160-bit requirement)
