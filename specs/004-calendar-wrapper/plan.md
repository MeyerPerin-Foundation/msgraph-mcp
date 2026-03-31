# Implementation Plan: Calendar Read-Write Wrapper

**Branch**: `004-calendar-wrapper` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-calendar-wrapper/spec.md`

## Summary

Add seven calendar MCP tools (list calendars, list events, get event, create event, update event, delete event, check availability) wrapping Microsoft Graph Calendar API endpoints. Follows the existing thin-wrapper pattern: new `GraphClient` methods call Graph REST endpoints directly, new `@mcp.tool()` functions format responses as human-readable strings, and tests mock the HTTP layer. The `Calendars.Read` scope is upgraded to `Calendars.ReadWrite`.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: FastMCP, httpx, msal  
**Storage**: N/A (stateless wrapper; tokens managed by existing auth system)  
**Testing**: pytest + pytest-asyncio with AsyncMock  
**Target Platform**: Linux (Azure App Service, gunicorn + uvicorn)  
**Project Type**: MCP server (remote web service)  
**Performance Goals**: < 5 seconds for listing events on a typical calendar  
**Constraints**: Consumer MSA accounts only; Calendars.ReadWrite scope  
**Scale/Scope**: Single-user personal calendar; no delegation or shared mailboxes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Thin MCP Wrapper | ✅ PASS | Each tool maps directly to one Graph REST call |
| II. Consumer-Account Only | ✅ PASS | Uses consumer endpoint, MSA only |
| III. Secure by Default | ✅ PASS | Reuses existing OAuth flow; only adds `Calendars.ReadWrite` scope |
| IV. Test Before Ship | ✅ PASS | All new tools and GraphClient methods will have tests |
| V. Automated Deployment | ✅ PASS | No infra changes; code-only PR via existing CI/CD |
| Least Privilege | ✅ PASS | Upgrading `Calendars.Read` → `Calendars.ReadWrite` is the minimum needed for write operations |

No violations. No complexity justifications needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-calendar-wrapper/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
msgraph_mcp/
├── config.py            # MODIFY: Calendars.Read → Calendars.ReadWrite
├── graph.py             # MODIFY: Add 8 calendar methods to GraphClient
└── server.py            # MODIFY: Add 7 calendar @mcp.tool() functions

tests/
├── test_graph.py        # MODIFY: Add tests for new GraphClient methods
└── test_tools.py        # MODIFY: Add tests for new calendar tools
```

**Structure Decision**: All changes are additions to existing files following the established flat layout. No new files or directories in the source tree.

## Design Decisions

### Graph API Endpoints

| Tool | Graph Endpoint | Method |
|------|---------------|--------|
| list_calendars | `GET /me/calendars` | GET |
| list_events | `GET /me/calendarView?startDateTime=...&endDateTime=...` | GET |
| list_events (no filter) | `GET /me/events?$top=...&$orderby=start/dateTime` | GET |
| get_event | `GET /me/events/{id}` | GET |
| create_event | `POST /me/events` | POST |
| update_event | `PATCH /me/events/{id}` | PATCH |
| delete_event | `DELETE /me/events/{id}` | DELETE |
| get_availability | `POST /me/calendar/getSchedule` | POST |

### Key Design Choices

1. **calendarView vs /me/events for listing**: Use `calendarView` when date range is provided (expands recurring events into instances). Fall back to `/me/events` with `$orderby=start/dateTime` when no date range is specified.

2. **Free/busy via getSchedule**: Use `POST /me/calendar/getSchedule` with the authenticated user's own email in the `schedules` array. The user's email is already available from the auth layer (`auth_provider.get_user_email_for_token`).

3. **Specific time window check**: Reuse the same `getSchedule` endpoint via a single `get_availability` tool. When `check_only=False` (default), return the full slot breakdown for a range. When `check_only=True`, pass the window as start/end and return a simple "You are free/busy" answer based on whether any `scheduleItems` overlap.

4. **Timezone handling**: Accept an optional `timezone` parameter (IANA format, e.g., "America/New_York"). Default to UTC. Pass timezone info in Graph API datetime objects `{"dateTime": "...", "timeZone": "..."}`.

5. **Scope upgrade**: Change `Calendars.Read` → `Calendars.ReadWrite` in `config.py`. This is the only permission change. Also update the Azure app registration (manual step).

## Complexity Tracking

> No violations — table not needed.
