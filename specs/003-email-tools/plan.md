# Implementation Plan: Email Tools

**Branch**: `003-email-tools` | **Date**: 2026-03-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-email-tools/spec.md`

## Summary

Add five MCP tools for email operations (list folders, list messages, read message, search messages, send message) via the Microsoft Graph Mail API. Extends the existing `GraphClient` in `graph.py` with mail methods alongside the existing To-Do methods. Adds `Mail.Send` to `GRAPH_SCOPES` in `config.py`. HTML email bodies are converted to plain text using Python's stdlib `html.parser` — no new dependencies required.

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
| I | Thin MCP Wrapper | ✅ Pass | Each tool maps directly to one Graph API call with minimal transformation. HTML-to-text conversion is the only processing, using stdlib only. |
| II | Consumer-Account Only | ✅ Pass | Uses the consumer endpoint (`https://graph.microsoft.com/v1.0`) via existing MSA-only OAuth configuration. |
| III | Secure by Default | ✅ Pass | Reuses existing OAuth flow. Microsoft tokens are never exposed to the AI client or logged. Access controlled by `MSGRAPH_MCP_ALLOWED_USERS`. |
| IV | Test Before Ship | ✅ Pass | Tests planned for all `GraphClient` mail methods (`test_graph.py`) and all MCP email tools (`test_tools.py`). All runnable via `uv run pytest`. |
| V | Automated Deployment | ✅ Pass | No infrastructure changes needed. Deployment uses existing GitHub Actions pipeline. PR with squash merge + auto-merge. |

## Project Structure

### Documentation (this feature)

```text
specs/003-email-tools/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Research decisions (R1–R7)
├── data-model.md        # Graph API entity shapes (MailFolder, Message)
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
├── server.py            # MODIFIED: add 5 email MCP tools
├── graph.py             # MODIFIED: add mail methods (get_mail_folders, get_messages, get_message, search_messages, send_message)
├── config.py            # MODIFIED: add Mail.Send to GRAPH_SCOPES
├── auth.py              # No changes needed
└── store.py             # No changes needed

tests/
├── test_graph.py        # MODIFIED: add mail method tests
├── test_tools.py        # MODIFIED: add email tool tests
├── conftest.py          # No changes needed
├── test_auth.py         # No changes needed
├── test_config.py       # No changes needed
├── test_server.py       # No changes needed
└── test_store.py        # No changes needed
```

**Structure Decision**: Extend the existing `graph.py` and test files rather than creating new ones, since the `GraphClient` pattern is already established and adding a second client class would duplicate the `_request()` infrastructure and violate the thin wrapper principle. The module docstring in `graph.py` is updated from "To-Do operations" to "Microsoft Graph API operations" to reflect the broader scope.

## Complexity Tracking

> No constitution violations. All five principles pass without exceptions.
