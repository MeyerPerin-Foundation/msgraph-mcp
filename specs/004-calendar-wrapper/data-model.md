# Data Model: Calendar Read-Write Wrapper

**Feature**: 004-calendar-wrapper  
**Date**: 2026-03-31

## Entities

### Calendar

Represents a user's calendar container. Returned by `GET /me/calendars`.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique calendar identifier |
| name | string | Display name of the calendar |
| color | string | Calendar color (e.g., "auto", "lightBlue") |
| isDefaultCalendar | boolean | Whether this is the user's default calendar |
| owner | object | `{name: str, address: str}` — calendar owner |

### Event

Represents a scheduled calendar item. Used across list, get, create, update, delete operations.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique event identifier |
| subject | string | Event title/subject (required for create) |
| body | object | `{contentType: "text"\|"html", content: str}` |
| start | dateTimeTimeZone | `{dateTime: str, timeZone: str}` (required for create) |
| end | dateTimeTimeZone | `{dateTime: str, timeZone: str}` (required for create) |
| location | object | `{displayName: str}` |
| attendees | list[object] | `[{emailAddress: {address, name}, type, status: {response, time}}]` |
| organizer | object | `{emailAddress: {address, name}}` |
| isAllDay | boolean | Whether the event spans all day |
| recurrence | object \| null | Recurrence pattern and range |
| onlineMeeting | object \| null | `{joinUrl: str}` if online meeting |
| isOnlineMeeting | boolean | Whether event has online meeting |
| onlineMeetingProvider | string | Provider name (e.g., "teamsForBusiness") |
| showAs | string | "free", "tentative", "busy", "oof", "workingElsewhere" |
| importance | string | "low", "normal", "high" |
| sensitivity | string | "normal", "personal", "private", "confidential" |

### dateTimeTimeZone

Used by Graph API for all time-related fields.

| Field | Type | Description |
|-------|------|-------------|
| dateTime | string | ISO 8601 datetime (e.g., "2026-04-01T09:00:00.0000000") |
| timeZone | string | IANA timezone name (e.g., "UTC", "America/New_York") |

### ScheduleInformation

Returned by `POST /me/calendar/getSchedule`.

| Field | Type | Description |
|-------|------|-------------|
| scheduleId | string | Email address of the queried user |
| availabilityView | string | Per-slot availability: 0=free, 1=tentative, 2=busy, 3=oof, 4=workingElsewhere |
| scheduleItems | list[ScheduleItem] | Individual busy blocks with details |
| workingHours | object | User's configured working hours |

### ScheduleItem

An individual busy block within a schedule response.

| Field | Type | Description |
|-------|------|-------------|
| status | string | "free", "tentative", "busy", "oof", "workingElsewhere", "unknown" |
| start | dateTimeTimeZone | Block start time |
| end | dateTimeTimeZone | Block end time |
| subject | string \| null | Event subject (may be hidden by privacy settings) |
| location | string \| null | Event location |

## Validation Rules

| Rule | Applies to | Description |
|------|-----------|-------------|
| Subject required | create_event | Subject must be non-empty |
| Start/end required | create_event, get_availability | Both start and end times must be provided |
| Start before end | create_event, update_event, get_availability | Start time must be before end time |
| Valid timezone | all time inputs | Must be a valid IANA timezone name; defaults to "UTC" |
| Email format | create_event (attendees) | Attendee emails must be valid email format |

## State Transitions

Events do not have explicit state transitions managed by this wrapper. The Graph API manages event lifecycle (created → updated → deleted). The wrapper is stateless.
