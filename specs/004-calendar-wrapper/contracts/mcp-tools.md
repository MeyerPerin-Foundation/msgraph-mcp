# MCP Tool Contracts: Calendar Read-Write Wrapper

**Feature**: 004-calendar-wrapper  
**Date**: 2026-03-31

This document defines the MCP tool interface contracts for the calendar feature. Each tool is a `@mcp.tool()` decorated async function returning a human-readable string.

---

## list_calendars

List all calendars for the authenticated user.

**Parameters**: None

**Returns**: Formatted string with calendar names, IDs, and default indicator.

**Example output**:
```
Calendars:

- Calendar (default)  [id: AAMkAGI2...]
- Work Events  [id: AAMkAGI2...]
- Birthdays  [id: AAMkAGI2...]
```

**Error cases**: Auth failure, Graph API error.

---

## list_events

List calendar events, optionally filtered by date range.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| start_date | str \| None | No | None | Start of date range (ISO 8601, e.g., "2026-04-01T00:00:00") |
| end_date | str \| None | No | None | End of date range (ISO 8601) |
| count | int | No | 10 | Maximum number of events to return |
| timezone | str \| None | No | "UTC" | IANA timezone name |

**Behavior**:
- If both `start_date` and `end_date` provided: uses `calendarView` endpoint (expands recurring events).
- If neither provided: uses `/me/events` ordered by start time.
- If only one of start/end provided: returns validation error.

**Example output**:
```
Events:

1. Team Standup
   Start: 2026-04-01 09:00 (UTC)
   End: 2026-04-01 09:30 (UTC)
   Location: Conference Room A
   Attendees: alice@example.com, bob@example.com
   [id: AAMkAGI2...]

2. Lunch with Client
   Start: 2026-04-01 12:00 (UTC)
   End: 2026-04-01 13:00 (UTC)
   Location: Downtown Restaurant
   [id: AAMkAGI2...]
```

---

## get_event

Get full details of a specific calendar event.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| event_id | str | Yes | The event ID |

**Example output**:
```
Event: Team Standup

Subject: Team Standup
Start: 2026-04-01 09:00 (UTC)
End: 2026-04-01 09:30 (UTC)
Location: Conference Room A
Organizer: alice@example.com
All Day: No
Online Meeting: https://teams.microsoft.com/l/meetup-join/...

Attendees:
  - alice@example.com (organizer) - accepted
  - bob@example.com - tentativelyAccepted
  - carol@example.com - none

Body:
Weekly standup to discuss progress and blockers.

Recurrence: weekly on Monday, Tuesday, Wednesday, Thursday, Friday
[id: AAMkAGI2...]
```

---

## create_event

Create a new calendar event.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| subject | str | Yes | — | Event title |
| start_time | str | Yes | — | Start time (ISO 8601) |
| end_time | str | Yes | — | End time (ISO 8601) |
| timezone | str \| None | No | "UTC" | IANA timezone name |
| location | str \| None | No | None | Location display name |
| body | str \| None | No | None | Event description (plain text) |
| attendees | str \| None | No | None | Comma-separated email addresses |
| is_all_day | bool | No | False | Whether event is all-day |
| is_online_meeting | bool | No | False | Whether to create online meeting |

**Validation**: Subject, start_time, end_time required. Start must be before end.

**Example output**:
```
Event created successfully.
Subject: Team Lunch
Start: 2026-04-01 12:00 (UTC)
End: 2026-04-01 13:00 (UTC)
Location: Cafeteria
[id: AAMkAGI2...]
```

---

## update_event

Update an existing calendar event.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| event_id | str | Yes | — | Event ID to update |
| subject | str \| None | No | None | New subject |
| start_time | str \| None | No | None | New start time (ISO 8601) |
| end_time | str \| None | No | None | New end time (ISO 8601) |
| timezone | str \| None | No | "UTC" | IANA timezone |
| location | str \| None | No | None | New location |
| body | str \| None | No | None | New description |
| attendees | str \| None | No | None | New comma-separated attendees |
| is_online_meeting | bool \| None | No | None | Enable/disable online meeting |

**Validation**: At least one field must be provided. If both start and end provided, start must be before end.

**Example output**:
```
Event updated successfully.
Subject: Team Lunch (Rescheduled)
[id: AAMkAGI2...]
```

---

## delete_event

Delete a calendar event.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| event_id | str | Yes | Event ID to delete |

**Example output**:
```
Event deleted successfully.
```

---

## get_availability

Check the authenticated user's free/busy availability.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| start_time | str | Yes | — | Start of query range (ISO 8601) |
| end_time | str | Yes | — | End of query range (ISO 8601) |
| timezone | str \| None | No | "UTC" | IANA timezone name |
| check_only | bool | No | False | If true, return simple free/busy answer |

**Behavior**:
- `check_only=False` (default): Returns full schedule breakdown with time slots and statuses.
- `check_only=True`: Returns a simple "You are free/busy during this window" message.

**Example output (check_only=False)**:
```
Availability from 2026-04-01 09:00 to 2026-04-01 17:00 (UTC):

- 09:00 - 09:30: Busy (Team Standup)
- 09:30 - 12:00: Free
- 12:00 - 13:00: Busy (Lunch with Client)
- 13:00 - 17:00: Free
```

**Example output (check_only=True)**:
```
You are busy during 2026-04-01 09:00 - 09:30 (UTC).
```

or

```
You are free during 2026-04-01 14:00 - 15:00 (UTC).
```
