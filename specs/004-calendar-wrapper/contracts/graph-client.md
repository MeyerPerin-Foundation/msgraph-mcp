# GraphClient Method Contracts: Calendar

**Feature**: 004-calendar-wrapper  
**Date**: 2026-03-31

New methods to add to `GraphClient` in `msgraph_mcp/graph.py`. All methods follow the existing pattern: call `self._request(method, path, ...)`, return parsed JSON.

---

## get_calendars

```python
async def get_calendars(self) -> list[dict]:
```
- **Endpoint**: `GET /me/calendars`
- **Returns**: `response["value"]` — list of calendar objects

---

## get_events

```python
async def get_events(self, count: int = 10) -> list[dict]:
```
- **Endpoint**: `GET /me/events?$top={count}&$orderby=start/dateTime`
- **Returns**: `response["value"]` — list of event objects

---

## get_calendar_view

```python
async def get_calendar_view(
    self, start: str, end: str, timezone: str = "UTC", count: int = 10
) -> list[dict]:
```
- **Endpoint**: `GET /me/calendarView?startDateTime={start}&endDateTime={end}&$top={count}&$orderby=start/dateTime`
- **Headers**: `Prefer: outlook.timezone="{timezone}"`
- **Returns**: `response["value"]` — list of expanded event instances

---

## get_event

```python
async def get_event(self, event_id: str) -> dict:
```
- **Endpoint**: `GET /me/events/{event_id}`
- **Returns**: Full event object

---

## create_event

```python
async def create_event(
    self,
    subject: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    location: str | None = None,
    body: str | None = None,
    attendees: list[str] | None = None,
    is_all_day: bool = False,
    is_online_meeting: bool = False,
) -> dict:
```
- **Endpoint**: `POST /me/events`
- **Body**: Event resource with subject, start/end as `dateTimeTimeZone`, optional location, body (text), attendees, isAllDay, isOnlineMeeting
- **Returns**: Created event object

---

## update_event

```python
async def update_event(
    self,
    event_id: str,
    *,
    subject: str | None = None,
    start: str | None = None,
    end: str | None = None,
    timezone: str = "UTC",
    location: str | None = None,
    body: str | None = None,
    attendees: list[str] | None = None,
    is_online_meeting: bool | None = None,
) -> dict:
```
- **Endpoint**: `PATCH /me/events/{event_id}`
- **Body**: Only fields that are not None
- **Returns**: Updated event object

---

## delete_event

```python
async def delete_event(self, event_id: str) -> None:
```
- **Endpoint**: `DELETE /me/events/{event_id}`
- **Returns**: None (204 No Content)

---

## get_schedule

```python
async def get_schedule(
    self,
    user_email: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    interval: int = 30,
) -> dict:
```
- **Endpoint**: `POST /me/calendar/getSchedule`
- **Body**:
  ```json
  {
    "schedules": ["{user_email}"],
    "startTime": {"dateTime": "{start}", "timeZone": "{timezone}"},
    "endTime": {"dateTime": "{end}", "timeZone": "{timezone}"},
    "availabilityViewInterval": {interval}
  }
  ```
- **Returns**: First element of `response["value"]` (single user's schedule info)
