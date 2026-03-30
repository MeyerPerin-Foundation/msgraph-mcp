# Implementation Plan: To-Do Task CRUD

**Branch**: `002-todo-crud` | **Date**: 2026-03-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-todo-crud/spec.md`

## Summary

Add five MCP tools for CRUD operations on Microsoft To Do tasks via the Graph API. A new `graph.py` module provides a thin `GraphClient` class wrapping httpx calls to the Graph To Do endpoints (`/me/todo/lists` and `/me/todo/lists/{listId}/tasks`). MCP tool functions in `server.py` delegate to this client, keeping tool definitions focused and Graph API details isolated. Authentication uses the existing `MicrosoftOAuthProvider` — no new OAuth scopes or infrastructure changes are required.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: mcp 1.26.0, httpx, Pydantic v2, Starlette
**Storage**: N/A (all data lives in Microsoft Graph)
**Testing**: pytest with pytest-asyncio
**Target Platform**: Azure App Service Linux
**Project Type**: web-service (FastMCP/Starlette)
**Performance Goals**: N/A
**Constraints**: Thin MCP wrapper, consumer-account only
**Scale/Scope**: 1–2 concurrent users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Thin MCP Wrapper | ✅ Pass | Each tool maps directly to one Graph API call with minimal transformation. No domain logic beyond what Graph provides. |
| II | Consumer-Account Only | ✅ Pass | Uses the consumer endpoint (`https://graph.microsoft.com/v1.0`) via existing MSA-only OAuth configuration. |
| III | Secure by Default | ✅ Pass | Reuses existing OAuth flow. Microsoft tokens are never exposed to the AI client or logged. Access controlled by `MSGRAPH_MCP_ALLOWED_USERS`. |
| IV | Test Before Ship | ✅ Pass | Tests planned for the `GraphClient` class (`test_graph.py`) and MCP tool integration (`test_tools.py`). All runnable via `uv run pytest`. |
| V | Automated Deployment | ✅ Pass | No infrastructure changes needed. Deployment uses existing GitHub Actions pipeline. PR with squash merge + auto-merge. |

## Project Structure

### Documentation (this feature)

```text
specs/002-todo-crud/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Research decisions (R1–R5)
├── data-model.md        # Graph API entity shapes
├── quickstart.md        # Usage guide for Copilot CLI
├── contracts/
│   └── mcp-tools.md     # MCP tool contracts
├── checklists/
│   └── requirements.md  # Requirements checklist
└── tasks.md             # Task breakdown (created separately by /speckit.tasks)
```

### Source Code (repository root)

```text
msgraph_mcp/
├── server.py            # MODIFIED: add 5 new MCP tools
├── graph.py             # NEW: Graph API client helper module
├── auth.py              # No changes needed
├── config.py            # No changes needed
└── store.py             # No changes needed

tests/
├── test_graph.py        # NEW: Graph API client unit tests (mocking inline with pytest fixtures)
├── test_tools.py        # NEW: MCP tool integration tests (mocking inline with pytest fixtures)
├── conftest.py          # No changes needed (Graph mocking is self-contained in test files)
├── test_auth.py         # No changes needed
├── test_config.py       # No changes needed
├── test_server.py       # No changes needed
└── test_store.py        # No changes needed
```

**Structure Decision**: Add a single `graph.py` module containing a thin `GraphClient` class that encapsulates all httpx calls to the Microsoft Graph To Do API. MCP tools in `server.py` delegate to this client. This keeps `server.py` focused on MCP tool definitions (parameter declarations, docstrings, response formatting) and keeps Graph API details (URL construction, request/response serialization, error mapping) isolated in one place. No new directories or packages are needed — the flat `msgraph_mcp/` layout is sufficient.

## Complexity Tracking

> No constitution violations. All five principles pass without exceptions.
