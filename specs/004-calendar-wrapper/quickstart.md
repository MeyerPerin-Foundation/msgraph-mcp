# Quickstart: Calendar Read-Write Wrapper

**Feature**: 004-calendar-wrapper  
**Date**: 2026-03-31

## What's Being Built

Seven new MCP tools for Microsoft 365 calendar operations:

| Tool | Operation | Priority |
|------|-----------|----------|
| `list_calendars` | List user's calendars | P3 |
| `list_events` | List/filter calendar events | P1 |
| `get_event` | Get full event details | P1 |
| `create_event` | Create a new event | P2 |
| `update_event` | Update an existing event | P3 |
| `delete_event` | Delete an event | P3 |
| `get_availability` | Check free/busy availability | P3 |

## Files to Modify

| File | Change |
|------|--------|
| `msgraph_mcp/config.py` | `Calendars.Read` → `Calendars.ReadWrite` |
| `msgraph_mcp/graph.py` | Add 8 methods to `GraphClient` |
| `msgraph_mcp/server.py` | Add 7 `@mcp.tool()` functions |
| `tests/test_graph.py` | Add tests for GraphClient calendar methods |
| `tests/test_tools.py` | Add tests for calendar tool functions |

## Implementation Pattern

Each calendar tool follows the same pattern as existing mail/task tools:

```python
@mcp.tool()
async def list_events(...) -> str:
    """List calendar events, optionally filtered by date range."""
    try:
        client = await _get_graph_client()
    except (ValueError, RuntimeError) as exc:
        return str(exc)
    try:
        events = await client.get_events(count=count)
        # Format as human-readable string
        return formatted_output
    except GraphApiError as exc:
        return exc.message
```

## Key Decisions

1. **calendarView** for date-range queries (expands recurring events); `/me/events` for unfiltered
2. **getSchedule** endpoint for free/busy (single tool with `check_only` flag)
3. **Calendars.ReadWrite** scope (replaces Calendars.Read)
4. **Optional timezone** parameter defaulting to UTC
5. **Plain text** event bodies (consistent with existing task pattern)

## Manual Step

After deployment, update the Azure app registration in the MeyerPerin Foundation tenant to include the `Calendars.ReadWrite` permission (replacing `Calendars.Read`).
