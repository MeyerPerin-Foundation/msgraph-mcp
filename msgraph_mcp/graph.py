"""Microsoft Graph API client for To-Do operations."""

from __future__ import annotations

import httpx

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class GraphApiError(Exception):
    """Error returned by the Microsoft Graph API."""

    def __init__(self, status_code: int, message: str, detail: str | None = None) -> None:
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(message)


def _friendly_error(status_code: int, body: dict | None, resource: str = "resource") -> str:
    """Map an HTTP status code to a user-friendly error message."""
    detail = ""
    if body and "error" in body:
        detail = body["error"].get("message", "")

    if status_code == 400:
        return f"Bad request: {detail}" if detail else "Bad request."
    if status_code == 401:
        return "Authentication failed. Please re-authenticate."
    if status_code == 403:
        return "Access denied. The required permissions may not be granted."
    if status_code == 404:
        return f"Not found: the specified {resource} does not exist."
    if status_code == 429:
        return "Rate limited by Microsoft Graph. Please try again shortly."
    if status_code >= 500:
        return "Microsoft Graph service error. Please try again later."
    return f"Unexpected error ({status_code}): {detail}" if detail else f"Unexpected error ({status_code})."


class GraphClient:
    """Thin async wrapper around the Microsoft Graph REST API for To-Do operations."""

    def __init__(self, token: str) -> None:
        self._token = token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        resource: str = "resource",
    ) -> httpx.Response:
        """Make an authenticated request to the Graph API.

        Raises ``GraphApiError`` on non-2xx responses or network failures.
        """
        url = f"{GRAPH_BASE_URL}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, headers=headers, json=json)
        except httpx.HTTPError:
            raise GraphApiError(
                status_code=0,
                message="Could not reach Microsoft Graph. Please check your connection.",
            )

        if response.status_code >= 300:
            try:
                body = response.json()
            except Exception:
                body = None
            raise GraphApiError(
                status_code=response.status_code,
                message=_friendly_error(response.status_code, body, resource),
                detail=str(body) if body else None,
            )

        return response

    # ── Task-list operations ──────────────────────────────────────────

    async def get_task_lists(self) -> list[dict]:
        """Return all To-Do task lists for the authenticated user."""
        resp = await self._request("GET", "/me/todo/lists", resource="task list")
        return resp.json().get("value", [])

    async def get_default_list_id(self) -> str:
        """Return the ID of the default To-Do task list.

        Falls back to the first list if no list has ``wellknownListName == 'defaultList'``.
        """
        lists = await self.get_task_lists()
        for tl in lists:
            if tl.get("wellknownListName") == "defaultList":
                return tl["id"]
        if lists:
            return lists[0]["id"]
        raise GraphApiError(
            status_code=404,
            message="Not found: the specified task list does not exist.",
        )

    # ── Task operations ───────────────────────────────────────────────

    async def get_tasks(self, list_id: str) -> list[dict]:
        """Return all tasks in a given task list."""
        resp = await self._request(
            "GET",
            f"/me/todo/lists/{list_id}/tasks",
            resource="task list",
        )
        return resp.json().get("value", [])

    async def create_task(
        self,
        list_id: str,
        title: str,
        body: str | None = None,
        due_date: str | None = None,
    ) -> dict:
        """Create a new task in a task list and return the created task."""
        payload: dict = {"title": title}
        if body is not None:
            payload["body"] = {"content": body, "contentType": "text"}
        if due_date is not None:
            payload["dueDateTime"] = {
                "dateTime": f"{due_date}T00:00:00.0000000",
                "timeZone": "UTC",
            }
        resp = await self._request(
            "POST",
            f"/me/todo/lists/{list_id}/tasks",
            json=payload,
            resource="task",
        )
        return resp.json()

    async def update_task(
        self,
        list_id: str,
        task_id: str,
        *,
        title: str | None = None,
        status: str | None = None,
        body: str | None = None,
        due_date: str | None = None,
        importance: str | None = None,
    ) -> dict:
        """Update specific fields of a task and return the updated task."""
        payload: dict = {}
        if title is not None:
            payload["title"] = title
        if status is not None:
            payload["status"] = status
        if body is not None:
            payload["body"] = {"content": body, "contentType": "text"}
        if due_date is not None:
            payload["dueDateTime"] = {
                "dateTime": f"{due_date}T00:00:00.0000000",
                "timeZone": "UTC",
            }
        if importance is not None:
            payload["importance"] = importance

        resp = await self._request(
            "PATCH",
            f"/me/todo/lists/{list_id}/tasks/{task_id}",
            json=payload,
            resource="task",
        )
        return resp.json()

    async def delete_task(self, list_id: str, task_id: str) -> None:
        """Delete a task from a task list."""
        await self._request(
            "DELETE",
            f"/me/todo/lists/{list_id}/tasks/{task_id}",
            resource="task",
        )
