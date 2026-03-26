# Implementation Plan: Persistent Credential Cache

**Branch**: `001-persistent-credentials` | **Date**: 2026-03-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-persistent-credentials/spec.md`

## Summary

The MCP server currently stores all authentication state (registered clients, MCP tokens, MSAL token cache) in memory. Every server restart or Azure deployment wipes this state, forcing users to re-authenticate through the browser. This feature adds file-based persistence using JSON files on Azure App Service's durable `/home/` mount, so credentials survive restarts.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: mcp 1.26.0, msal 1.35.1, Pydantic v2, Starlette  
**Storage**: JSON files on local file system (Azure `/home/` durable mount)  
**Testing**: pytest with pytest-asyncio  
**Target Platform**: Azure App Service Linux (single instance)  
**Project Type**: web-service (FastMCP/Starlette)  
**Performance Goals**: N/A — write volume is negligible (< 10 writes per auth session)  
**Constraints**: Single-instance only; no external dependencies (no Redis, no database)  
**Scale/Scope**: 1–2 concurrent users, < 10 registered clients

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Thin MCP Wrapper | ✅ PASS | File-based persistence is minimal infrastructure; no new domain logic |
| II. Consumer-Account Only | ✅ PASS | No change to auth audience |
| III. Secure by Default | ✅ PASS | Credential files use 0o600 permissions; no tokens in logs |
| IV. Test Before Ship | ✅ PASS | Persistence load/save and round-trip will have dedicated tests |
| V. Automated Deployment | ✅ PASS | Bicep modified: `MSGRAPH_CACHE_DIR` added as app setting |

**Post-Phase-1 re-check**: All gates still pass. The design adds a single new module (`msgraph_mcp/store.py`) with no external dependencies and minimal surface area.

## Project Structure

### Documentation (this feature)

```text
specs/001-persistent-credentials/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: integration guide
├── contracts/           # Phase 1: module interface contracts
│   └── credential-store.md
├── checklists/          # Spec quality checklist
│   └── requirements.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
msgraph_mcp/
├── __init__.py
├── auth.py              # Modified: add persistence hooks
├── config.py            # Modified: add MSGRAPH_CACHE_DIR
├── server.py            # Modified: instantiate CredentialStore and pass to provider
└── store.py             # NEW: CredentialStore persistence module

tests/
├── conftest.py          # Modified: add cache_dir fixture
├── test_auth.py         # Modified: test persistence round-trips
├── test_config.py       # Existing (no changes)
├── test_server.py       # Existing (no changes)
└── test_store.py        # NEW: CredentialStore unit tests

infra/
└── main.bicep           # Modified: add MSGRAPH_CACHE_DIR app setting
```

**Structure Decision**: The persistence module is a single new file (`store.py`) in the existing flat package layout, consistent with the "Thin MCP Wrapper" principle. No new packages or directories are needed in the source tree.
