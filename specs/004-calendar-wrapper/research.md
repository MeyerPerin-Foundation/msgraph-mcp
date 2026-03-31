# Research: Calendar Read-Write Wrapper

**Feature**: 004-calendar-wrapper  
**Date**: 2026-03-31

## R1: Graph Calendar API Endpoint Selection

**Decision**: Use `calendarView` for date-range queries, `/me/events` for unfiltered listing.

**Rationale**: The `calendarView` endpoint (`GET /me/calendarView?startDateTime=...&endDateTime=...`) automatically expands recurring events into individual instances within the requested range, which is the expected behavior when browsing a schedule. The `/me/events` endpoint returns raw event objects (recurring events as series, not instances) and is better for unfiltered "show my next N events" queries.

**Alternatives considered**:
- Using `/me/events` with `$filter` on start/end: Does not expand recurring events, which would miss individual instances of recurring meetings. Rejected.
- Using `calendarView` for all queries: Requires `startDateTime` and `endDateTime` as mandatory parameters, making a simple "show next 10 events" query awkward. Rejected as sole endpoint.

## R2: Free/Busy Implementation

**Decision**: Use `POST /me/calendar/getSchedule` for both range-based and window-based availability queries.

**Rationale**: The `getSchedule` endpoint returns structured `scheduleItems` (with status: free, busy, tentative, oof, workingElsewhere) and an `availabilityView` string. It is the canonical Graph API for free/busy lookups. The same endpoint serves both use cases:
- **Range query**: Call with a wide time range, return `scheduleItems` to the user.
- **Window check**: Call with the specific window, check if all `scheduleItems` show free status.

**Request format**:
```json
{
  "schedules": ["user@example.com"],
  "startTime": {"dateTime": "2026-04-01T09:00:00", "timeZone": "UTC"},
  "endTime": {"dateTime": "2026-04-01T17:00:00", "timeZone": "UTC"},
  "availabilityViewInterval": 30
}
```

**Response format**: Returns `scheduleInformation` objects with `scheduleItems` (individual busy blocks) and `availabilityView` (string of 0/1/2/3/4 characters per interval slot).

**User email requirement**: The `schedules` array requires the user's email address. This is available from `auth_provider.get_user_email_for_token()` in the tool layer and will be passed to the GraphClient method.

**Alternatives considered**:
- Fetching events via `calendarView` and computing free/busy manually: More complex, misses details like OOF vs busy distinction, and duplicates logic Graph already provides. Rejected.

## R3: Scope Upgrade

**Decision**: Change `Calendars.Read` → `Calendars.ReadWrite` in `GRAPH_SCOPES`.

**Rationale**: `Calendars.Read` is sufficient for list/get/getSchedule operations, but create/update/delete require `Calendars.ReadWrite`. A single scope covers all calendar operations. The Azure app registration must also be updated manually to include `Calendars.ReadWrite`.

**Alternatives considered**:
- Adding `Calendars.ReadWrite` alongside `Calendars.Read`: Requesting both is redundant since `ReadWrite` implies `Read`. Rejected.
- Using `Calendars.ReadWrite.Shared`: Only needed for shared/delegated calendars, which are out of scope. Rejected.

## R4: Timezone Handling

**Decision**: Accept an optional `timezone` parameter (IANA timezone name, e.g., "America/New_York"). Default to "UTC".

**Rationale**: The Graph API `dateTimeTimeZone` resource type uses `{"dateTime": "...", "timeZone": "..."}` format. IANA timezone names are directly accepted. Defaulting to UTC avoids ambiguity when timezone is omitted.

**Alternatives considered**:
- Requiring timezone on every call: Too burdensome for users. Rejected.
- Using Windows timezone names: IANA names are more universal and also supported by Graph. Rejected.

## R5: Event Body Content Type

**Decision**: Event bodies will be sent as plain text (`contentType: "text"`), consistent with the existing task body pattern.

**Rationale**: The existing `create_task` method uses `{"content": body, "contentType": "text"}`. Calendar event bodies in Graph support `text` and `html`. Using `text` keeps the interface simple and consistent.

**Alternatives considered**:
- Supporting HTML body: Adds complexity, and AI assistants typically work with plain text. Could be added later. Rejected for v1.

## R6: Two Tools vs One for Availability

**Decision**: Implement availability as a single `get_availability` tool with both a range query mode and a specific window mode, controlled by parameters.

**Rationale**: Both modes use the same `getSchedule` endpoint. A single tool with `start_time`, `end_time`, and an optional `check_only` boolean keeps the interface simple. When `check_only` is false (default), return the full slot breakdown. When `check_only` is true, return a simple "You are free/busy during this window" message.

**Alternatives considered**:
- Two separate tools (`get_availability` and `check_if_free`): Would duplicate endpoint logic. A single tool with a mode flag is simpler. Rejected.
