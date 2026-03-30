"""Tests for the To-Do MCP tools in server.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from msgraph_mcp.graph import GraphApiError


# ── Fixtures ──────────────────────────────────────────────────────────

SAMPLE_LISTS = [
    {"id": "list1", "displayName": "Tasks", "wellknownListName": "defaultList"},
    {"id": "list2", "displayName": "Shopping"},
]

SAMPLE_TASKS = [
    {
        "id": "t1",
        "title": "Buy milk",
        "status": "notStarted",
        "importance": "normal",
        "dueDateTime": {"dateTime": "2024-01-20T00:00:00.0000000", "timeZone": "UTC"},
        "body": {"content": "From the store", "contentType": "text"},
    },
    {
        "id": "t2",
        "title": "Call dentist",
        "status": "completed",
        "importance": "high",
        "dueDateTime": None,
        "body": {"content": "", "contentType": "text"},
    },
]


def _fake_access_token(token_str: str = "mcp-token-123") -> MagicMock:
    """Build a mock AccessToken object."""
    tok = MagicMock()
    tok.token = token_str
    return tok


def _patch_auth(
    *,
    access_token: MagicMock | None = None,
    user_email: str | None = "user@example.com",
    ms_token: str = "ms-graph-token",
    ms_token_error: Exception | None = None,
):
    """Return a context-manager stack that patches auth helpers.

    Yields a dict of the mocks for optional assertion.
    """
    if access_token is None:
        access_token = _fake_access_token()

    patches = {
        "get_access_token": patch(
            "msgraph_mcp.server.get_access_token",
            return_value=access_token,
        ),
        "get_user_email": patch.object(
            _get_auth_provider(),
            "get_user_email_for_token",
            return_value=user_email,
        ),
        "get_microsoft_token": patch.object(
            _get_auth_provider(),
            "get_microsoft_token",
            new_callable=AsyncMock,
            side_effect=ms_token_error,
            return_value=ms_token,
        ),
    }
    return patches


def _get_auth_provider():
    """Import and return the auth_provider from server module."""
    from msgraph_mcp.server import auth_provider

    return auth_provider


# ── list_task_lists ───────────────────────────────────────────────────


class TestListTaskLists:
    @pytest.mark.asyncio
    async def test_returns_formatted_lists(self):
        from msgraph_mcp.server import list_task_lists

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_task_lists = AsyncMock(return_value=SAMPLE_LISTS)
                MockGC.return_value = instance

                result = await list_task_lists()

        assert "Tasks" in result
        assert "Shopping" in result
        assert "list1" in result
        assert "(default)" in result

    @pytest.mark.asyncio
    async def test_empty_lists(self):
        from msgraph_mcp.server import list_task_lists

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_task_lists = AsyncMock(return_value=[])
                MockGC.return_value = instance

                result = await list_task_lists()

        assert "No task lists found" in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import list_task_lists

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_task_lists = AsyncMock(
                    side_effect=GraphApiError(401, "Authentication failed. Please re-authenticate.")
                )
                MockGC.return_value = instance

                result = await list_task_lists()

        assert "re-authenticate" in result.lower()

    @pytest.mark.asyncio
    async def test_no_auth_token(self):
        from msgraph_mcp.server import list_task_lists

        with patch("msgraph_mcp.server.get_access_token", return_value=None):
            result = await list_task_lists()

        assert "Authentication required" in result

    @pytest.mark.asyncio
    async def test_token_refresh_failure(self):
        from msgraph_mcp.server import list_task_lists

        patches = _patch_auth(ms_token_error=RuntimeError("Token refresh failed"))
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            result = await list_task_lists()

        assert "Token refresh failed" in result


# ── list_tasks ────────────────────────────────────────────────────────


class TestListTasks:
    @pytest.mark.asyncio
    async def test_returns_formatted_tasks(self):
        from msgraph_mcp.server import list_tasks

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_tasks = AsyncMock(return_value=SAMPLE_TASKS)
                MockGC.return_value = instance

                result = await list_tasks(list_id="list1")

        assert "Buy milk" in result
        assert "Call dentist" in result
        assert "notStarted" in result
        assert "completed" in result
        assert "2024-01-20" in result
        assert "From the store" in result

    @pytest.mark.asyncio
    async def test_empty_tasks(self):
        from msgraph_mcp.server import list_tasks

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_tasks = AsyncMock(return_value=[])
                MockGC.return_value = instance

                result = await list_tasks(list_id="list1")

        assert "No tasks found" in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import list_tasks

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_tasks = AsyncMock(
                    side_effect=GraphApiError(404, "Not found: the specified task list does not exist.")
                )
                MockGC.return_value = instance

                result = await list_tasks(list_id="bad-list")

        assert "Not found" in result


# ── create_task ───────────────────────────────────────────────────────


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_with_all_params(self):
        from msgraph_mcp.server import create_task

        created = {
            "id": "t-new",
            "title": "New task",
            "dueDateTime": {"dateTime": "2024-06-15T00:00:00.0000000", "timeZone": "UTC"},
        }
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.create_task = AsyncMock(return_value=created)
                MockGC.return_value = instance

                result = await create_task(
                    title="New task",
                    list_id="list1",
                    due_date="2024-06-15",
                    body="Some notes",
                )

        assert "Task created" in result
        assert "t-new" in result
        assert "2024-06-15" in result

    @pytest.mark.asyncio
    async def test_create_title_only(self):
        from msgraph_mcp.server import create_task

        created = {"id": "t-simple", "title": "Simple task"}
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_default_list_id = AsyncMock(return_value="default-list")
                instance.create_task = AsyncMock(return_value=created)
                MockGC.return_value = instance

                result = await create_task(title="Simple task")

        assert "Task created" in result
        assert "t-simple" in result
        instance.get_default_list_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_due_date(self):
        from msgraph_mcp.server import create_task

        result = await create_task(title="Bad date", due_date="not-a-date")
        assert "Invalid due_date format" in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import create_task

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.create_task = AsyncMock(
                    side_effect=GraphApiError(400, "Bad request: missing required field")
                )
                MockGC.return_value = instance

                result = await create_task(title="Bad task", list_id="list1")

        assert "Bad request" in result


# ── update_task ───────────────────────────────────────────────────────


class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_mark_complete(self):
        from msgraph_mcp.server import update_task

        updated = {"id": "t1", "title": "Buy milk", "status": "completed"}
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.update_task = AsyncMock(return_value=updated)
                MockGC.return_value = instance

                result = await update_task(
                    list_id="list1", task_id="t1", status="completed"
                )

        assert "Task updated" in result

    @pytest.mark.asyncio
    async def test_change_title(self):
        from msgraph_mcp.server import update_task

        updated = {"id": "t1", "title": "New title"}
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.update_task = AsyncMock(return_value=updated)
                MockGC.return_value = instance

                result = await update_task(
                    list_id="list1", task_id="t1", title="New title"
                )

        assert "Task updated" in result
        assert "New title" in result

    @pytest.mark.asyncio
    async def test_set_due_date(self):
        from msgraph_mcp.server import update_task

        updated = {"id": "t1", "title": "Task"}
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.update_task = AsyncMock(return_value=updated)
                MockGC.return_value = instance

                result = await update_task(
                    list_id="list1", task_id="t1", due_date="2025-12-31"
                )

        assert "Task updated" in result

    @pytest.mark.asyncio
    async def test_invalid_due_date(self):
        from msgraph_mcp.server import update_task

        result = await update_task(
            list_id="list1", task_id="t1", due_date="bad-date"
        )
        assert "Invalid due_date format" in result

    @pytest.mark.asyncio
    async def test_no_fields_provided(self):
        from msgraph_mcp.server import update_task

        result = await update_task(list_id="list1", task_id="t1")
        assert "No fields provided" in result

    @pytest.mark.asyncio
    async def test_invalid_status(self):
        from msgraph_mcp.server import update_task

        result = await update_task(
            list_id="list1", task_id="t1", status="invalid"
        )
        assert "Invalid status" in result

    @pytest.mark.asyncio
    async def test_invalid_importance(self):
        from msgraph_mcp.server import update_task

        result = await update_task(
            list_id="list1", task_id="t1", importance="critical"
        )
        assert "Invalid importance" in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import update_task

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.update_task = AsyncMock(
                    side_effect=GraphApiError(404, "Not found: the specified task does not exist.")
                )
                MockGC.return_value = instance

                result = await update_task(
                    list_id="list1", task_id="bad-id", title="X"
                )

        assert "Not found" in result


# ── delete_task ───────────────────────────────────────────────────────


class TestDeleteTask:
    @pytest.mark.asyncio
    async def test_delete_success(self):
        from msgraph_mcp.server import delete_task

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.delete_task = AsyncMock(return_value=None)
                MockGC.return_value = instance

                result = await delete_task(list_id="list1", task_id="t1")

        assert "deleted successfully" in result.lower()
        assert "t1" in result

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        from msgraph_mcp.server import delete_task

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.delete_task = AsyncMock(
                    side_effect=GraphApiError(404, "Not found: the specified task does not exist.")
                )
                MockGC.return_value = instance

                result = await delete_task(list_id="list1", task_id="bad-id")

        assert "Not found" in result
