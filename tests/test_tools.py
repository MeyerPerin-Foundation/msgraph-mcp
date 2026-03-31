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


# ── Sample mail data ──────────────────────────────────────────────────

SAMPLE_MESSAGES = [
    {
        "id": "msg1",
        "subject": "Budget Report",
        "from": {"emailAddress": {"name": "John Doe", "address": "john@example.com"}},
        "toRecipients": [{"emailAddress": {"address": "team@example.com"}}],
        "ccRecipients": [{"emailAddress": {"address": "finance@example.com"}}],
        "receivedDateTime": "2026-03-30T14:22:00Z",
        "isRead": False,
        "importance": "normal",
        "body": {"contentType": "text", "content": "Hi team, please find attached the budget report."},
    },
    {
        "id": "msg2",
        "subject": "Meeting Notes",
        "from": {"emailAddress": {"name": "Jane Smith", "address": "jane@example.com"}},
        "toRecipients": [{"emailAddress": {"address": "team@example.com"}}],
        "ccRecipients": [],
        "receivedDateTime": "2026-03-29T10:00:00Z",
        "isRead": True,
        "importance": "high",
        "body": {"contentType": "text", "content": "Notes from yesterday's meeting."},
    },
]

SAMPLE_FOLDERS = [
    {"id": "f1", "displayName": "Inbox", "totalItemCount": 142, "unreadItemCount": 3},
    {"id": "f2", "displayName": "Sent Items", "totalItemCount": 89, "unreadItemCount": 0},
]


# ── list_messages ─────────────────────────────────────────────────────


class TestListMessages:
    @pytest.mark.asyncio
    async def test_returns_formatted_messages(self):
        from msgraph_mcp.server import list_messages

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_messages = AsyncMock(return_value=SAMPLE_MESSAGES)
                MockGC.return_value = instance

                result = await list_messages()

        assert "John Doe" in result
        assert "Budget Report" in result
        assert "2026-03-30" in result
        assert "[Unread]" in result
        assert "[Read]" in result
        assert "msg1" in result

    @pytest.mark.asyncio
    async def test_folder_specific(self):
        from msgraph_mcp.server import list_messages

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_messages = AsyncMock(return_value=SAMPLE_MESSAGES)
                MockGC.return_value = instance

                result = await list_messages(folder_id="f1")

        assert "Messages:" in result
        instance.get_messages.assert_called_once_with(folder_id="f1", count=10)

    @pytest.mark.asyncio
    async def test_empty_inbox(self):
        from msgraph_mcp.server import list_messages

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_messages = AsyncMock(return_value=[])
                MockGC.return_value = instance

                result = await list_messages()

        assert "No messages found" in result

    @pytest.mark.asyncio
    async def test_auth_failure(self):
        from msgraph_mcp.server import list_messages

        with patch("msgraph_mcp.server.get_access_token", return_value=None):
            result = await list_messages()

        assert "Authentication required" in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import list_messages

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_messages = AsyncMock(
                    side_effect=GraphApiError(401, "Authentication failed. Please re-authenticate.")
                )
                MockGC.return_value = instance

                result = await list_messages()

        assert "re-authenticate" in result.lower()


# ── read_message ──────────────────────────────────────────────────────


class TestReadMessage:
    @pytest.mark.asyncio
    async def test_returns_full_message(self):
        from msgraph_mcp.server import read_message

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_message = AsyncMock(return_value=SAMPLE_MESSAGES[0])
                MockGC.return_value = instance

                result = await read_message(message_id="msg1")

        assert "Subject: Budget Report" in result
        assert "From: John Doe <john@example.com>" in result
        assert "To: team@example.com" in result
        assert "CC: finance@example.com" in result
        assert "Importance: normal" in result
        assert "Status: Unread" in result
        assert "Body:" in result
        assert "budget report" in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import read_message

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_message = AsyncMock(
                    side_effect=GraphApiError(404, "Not found: the specified message does not exist.")
                )
                MockGC.return_value = instance

                result = await read_message(message_id="bad-id")

        assert "Not found" in result


# ── search_messages ───────────────────────────────────────────────────


class TestSearchMessages:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        from msgraph_mcp.server import search_messages

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.search_messages = AsyncMock(return_value=SAMPLE_MESSAGES[:1])
                MockGC.return_value = instance

                result = await search_messages(query="budget")

        assert "Budget Report" in result
        assert "John Doe" in result

    @pytest.mark.asyncio
    async def test_empty_results(self):
        from msgraph_mcp.server import search_messages

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.search_messages = AsyncMock(return_value=[])
                MockGC.return_value = instance

                result = await search_messages(query="nonexistent")

        assert 'No messages found matching "nonexistent"' in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import search_messages

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.search_messages = AsyncMock(
                    side_effect=GraphApiError(401, "Authentication failed. Please re-authenticate.")
                )
                MockGC.return_value = instance

                result = await search_messages(query="test")

        assert "re-authenticate" in result.lower()


# ── send_message ──────────────────────────────────────────────────────


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_success(self):
        from msgraph_mcp.server import send_message

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.send_message = AsyncMock(return_value=None)
                MockGC.return_value = instance

                result = await send_message(
                    to="john@example.com", subject="Hello", body="Hi there"
                )

        assert "Email sent successfully" in result
        assert "john@example.com" in result
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_send_with_cc(self):
        from msgraph_mcp.server import send_message

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.send_message = AsyncMock(return_value=None)
                MockGC.return_value = instance

                result = await send_message(
                    to="a@test.com, b@test.com",
                    subject="Meeting",
                    body="Let's meet",
                    cc="mgr@test.com",
                )

        assert "Email sent successfully" in result
        assert "a@test.com" in result
        assert "b@test.com" in result
        assert "CC: mgr@test.com" in result

    @pytest.mark.asyncio
    async def test_empty_to(self):
        from msgraph_mcp.server import send_message

        result = await send_message(to="", subject="X", body="Y")
        assert "Validation error" in result
        assert "'to'" in result

    @pytest.mark.asyncio
    async def test_empty_subject(self):
        from msgraph_mcp.server import send_message

        result = await send_message(to="a@test.com", subject="", body="Y")
        assert "Validation error" in result
        assert "'subject'" in result

    @pytest.mark.asyncio
    async def test_empty_body(self):
        from msgraph_mcp.server import send_message

        result = await send_message(to="a@test.com", subject="X", body="")
        assert "Validation error" in result
        assert "'body'" in result

    @pytest.mark.asyncio
    async def test_invalid_email_format(self):
        from msgraph_mcp.server import send_message

        result = await send_message(to="not-an-email", subject="X", body="Y")
        assert "Validation error" in result
        assert "not-an-email" in result
        assert "not a valid email" in result

    @pytest.mark.asyncio
    async def test_graph_api_403(self):
        from msgraph_mcp.server import send_message

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.send_message = AsyncMock(
                    side_effect=GraphApiError(403, "Access denied. The required permissions may not be granted.")
                )
                MockGC.return_value = instance

                result = await send_message(
                    to="a@test.com", subject="X", body="Y"
                )

        assert "Access denied" in result


# ── list_mail_folders ─────────────────────────────────────────────────


class TestListMailFolders:
    @pytest.mark.asyncio
    async def test_returns_formatted_folders(self):
        from msgraph_mcp.server import list_mail_folders

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_mail_folders = AsyncMock(return_value=SAMPLE_FOLDERS)
                MockGC.return_value = instance

                result = await list_mail_folders()

        assert "Inbox" in result
        assert "142 messages" in result
        assert "3 unread" in result
        assert "Sent Items" in result
        assert "0 unread" in result
        assert "f1" in result

    @pytest.mark.asyncio
    async def test_empty_folders(self):
        from msgraph_mcp.server import list_mail_folders

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_mail_folders = AsyncMock(return_value=[])
                MockGC.return_value = instance

                result = await list_mail_folders()

        assert "No mail folders found" in result

    @pytest.mark.asyncio
    async def test_graph_api_error(self):
        from msgraph_mcp.server import list_mail_folders

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_mail_folders = AsyncMock(
                    side_effect=GraphApiError(401, "Authentication failed. Please re-authenticate.")
                )
                MockGC.return_value = instance

                result = await list_mail_folders()

        assert "re-authenticate" in result.lower()


# ── Sample calendar data ─────────────────────────────────────────────

SAMPLE_CALENDARS = [
    {"id": "cal1", "name": "Calendar", "isDefaultCalendar": True, "color": "auto"},
    {"id": "cal2", "name": "Work", "isDefaultCalendar": False, "color": "lightBlue"},
]

SAMPLE_EVENTS = [
    {
        "id": "evt1",
        "subject": "Team Standup",
        "start": {"dateTime": "2026-04-01T09:00:00.0000000", "timeZone": "UTC"},
        "end": {"dateTime": "2026-04-01T09:30:00.0000000", "timeZone": "UTC"},
        "location": {"displayName": "Room A"},
        "attendees": [
            {"emailAddress": {"address": "alice@example.com"}, "type": "required", "status": {"response": "accepted"}},
        ],
        "organizer": {"emailAddress": {"address": "org@example.com"}},
        "isAllDay": False,
        "body": {"contentType": "text", "content": "Daily standup meeting."},
        "recurrence": None,
        "onlineMeeting": None,
    },
    {
        "id": "evt2",
        "subject": "Lunch",
        "start": {"dateTime": "2026-04-01T12:00:00.0000000", "timeZone": "UTC"},
        "end": {"dateTime": "2026-04-01T13:00:00.0000000", "timeZone": "UTC"},
        "location": {"displayName": ""},
        "attendees": [],
        "organizer": {"emailAddress": {"address": "org@example.com"}},
        "isAllDay": False,
        "body": {"contentType": "text", "content": ""},
        "recurrence": None,
        "onlineMeeting": None,
    },
]


# ── list_calendars ───────────────────────────────────────────────────


class TestListCalendars:
    @pytest.mark.asyncio
    async def test_list_calendars_success(self):
        from msgraph_mcp.server import list_calendars

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_calendars = AsyncMock(return_value=SAMPLE_CALENDARS)
                MockGC.return_value = instance

                result = await list_calendars()

        assert "Calendar" in result
        assert "Work" in result
        assert "(default)" in result
        assert "cal1" in result
        assert "cal2" in result

    @pytest.mark.asyncio
    async def test_list_calendars_empty(self):
        from msgraph_mcp.server import list_calendars

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_calendars = AsyncMock(return_value=[])
                MockGC.return_value = instance

                result = await list_calendars()

        assert "No calendars found." in result

    @pytest.mark.asyncio
    async def test_list_calendars_auth_failure(self):
        from msgraph_mcp.server import list_calendars

        with patch("msgraph_mcp.server.get_access_token", return_value=None):
            result = await list_calendars()

        assert "Authentication required" in result


# ── list_events ──────────────────────────────────────────────────────


class TestListEvents:
    @pytest.mark.asyncio
    async def test_list_events_no_filter(self):
        from msgraph_mcp.server import list_events

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_events = AsyncMock(return_value=SAMPLE_EVENTS)
                MockGC.return_value = instance

                result = await list_events()

        assert "Team Standup" in result
        assert "Lunch" in result
        assert "evt1" in result
        instance.get_events.assert_called_once_with(count=10)

    @pytest.mark.asyncio
    async def test_list_events_with_date_range(self):
        from msgraph_mcp.server import list_events

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_calendar_view = AsyncMock(return_value=SAMPLE_EVENTS)
                MockGC.return_value = instance

                result = await list_events(
                    start_date="2026-04-01T00:00:00",
                    end_date="2026-04-07T23:59:59",
                    count=20,
                    timezone="America/Chicago",
                )

        assert "Team Standup" in result
        instance.get_calendar_view.assert_called_once_with(
            start="2026-04-01T00:00:00",
            end="2026-04-07T23:59:59",
            timezone="America/Chicago",
            count=20,
        )

    @pytest.mark.asyncio
    async def test_list_events_partial_range(self):
        from msgraph_mcp.server import list_events

        result = await list_events(start_date="2026-04-01T00:00:00")
        assert "Validation error" in result
        assert "both" in result.lower()

    @pytest.mark.asyncio
    async def test_list_events_empty(self):
        from msgraph_mcp.server import list_events

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_events = AsyncMock(return_value=[])
                MockGC.return_value = instance

                result = await list_events()

        assert "No events found." in result

    @pytest.mark.asyncio
    async def test_list_events_graph_api_error(self):
        from msgraph_mcp.server import list_events

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_events = AsyncMock(
                    side_effect=GraphApiError(401, "Authentication failed. Please re-authenticate.")
                )
                MockGC.return_value = instance

                result = await list_events()

        assert "re-authenticate" in result.lower()


# ── get_event ────────────────────────────────────────────────────────


class TestGetEventTool:
    @pytest.mark.asyncio
    async def test_get_event_success(self):
        from msgraph_mcp.server import get_event

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_event = AsyncMock(return_value=SAMPLE_EVENTS[0])
                MockGC.return_value = instance

                result = await get_event(event_id="evt1")

        assert "Team Standup" in result
        assert "Subject:" in result
        assert "Start:" in result
        assert "End:" in result
        assert "Room A" in result
        assert "org@example.com" in result
        assert "alice@example.com" in result
        assert "Daily standup meeting." in result
        assert "evt1" in result

    @pytest.mark.asyncio
    async def test_get_event_not_found(self):
        from msgraph_mcp.server import get_event

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_event = AsyncMock(
                    side_effect=GraphApiError(404, "Not found: the specified event does not exist.")
                )
                MockGC.return_value = instance

                result = await get_event(event_id="bad-id")

        assert "Not found" in result


# ── create_event ─────────────────────────────────────────────────────


class TestCreateEventTool:
    @pytest.mark.asyncio
    async def test_create_event_success(self):
        from msgraph_mcp.server import create_event

        created = {
            "id": "evt-new",
            "subject": "Team Lunch",
            "start": {"dateTime": "2026-04-01T12:00:00.0000000", "timeZone": "America/Chicago"},
            "end": {"dateTime": "2026-04-01T13:00:00.0000000", "timeZone": "America/Chicago"},
            "location": {"displayName": "Cafe"},
        }
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.create_event = AsyncMock(return_value=created)
                MockGC.return_value = instance

                result = await create_event(
                    subject="Team Lunch",
                    start_time="2026-04-01T12:00:00",
                    end_time="2026-04-01T13:00:00",
                    timezone="America/Chicago",
                    location="Cafe",
                    body="Team lunch at the cafe",
                    attendees="alice@example.com, bob@example.com",
                    is_all_day=False,
                    is_online_meeting=True,
                )

        assert "Event created successfully." in result
        assert "Team Lunch" in result
        assert "Cafe" in result
        assert "evt-new" in result

    @pytest.mark.asyncio
    async def test_create_event_missing_subject(self):
        from msgraph_mcp.server import create_event

        result = await create_event(
            subject="",
            start_time="2026-04-01T09:00:00",
            end_time="2026-04-01T10:00:00",
        )
        assert "Validation error" in result
        assert "subject" in result.lower()

    @pytest.mark.asyncio
    async def test_create_event_start_after_end(self):
        from msgraph_mcp.server import create_event

        result = await create_event(
            subject="Meeting",
            start_time="2026-04-01T14:00:00",
            end_time="2026-04-01T13:00:00",
        )
        assert "Validation error" in result
        assert "start_time" in result

    @pytest.mark.asyncio
    async def test_create_event_invalid_email(self):
        from msgraph_mcp.server import create_event

        result = await create_event(
            subject="Meeting",
            start_time="2026-04-01T09:00:00",
            end_time="2026-04-01T10:00:00",
            attendees="not-an-email",
        )
        assert "Validation error" in result
        assert "not-an-email" in result

    @pytest.mark.asyncio
    async def test_create_event_auth_failure(self):
        from msgraph_mcp.server import create_event

        with patch("msgraph_mcp.server.get_access_token", return_value=None):
            result = await create_event(
                subject="Meeting",
                start_time="2026-04-01T09:00:00",
                end_time="2026-04-01T10:00:00",
            )

        assert "Authentication required" in result


# ── update_event ─────────────────────────────────────────────────────


class TestUpdateEventTool:
    @pytest.mark.asyncio
    async def test_update_event_success(self):
        from msgraph_mcp.server import update_event

        updated = {"id": "evt1", "subject": "New Subject"}
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.update_event = AsyncMock(return_value=updated)
                MockGC.return_value = instance

                result = await update_event(event_id="evt1", subject="New Subject")

        assert "Event updated successfully." in result
        assert "New Subject" in result
        assert "evt1" in result

    @pytest.mark.asyncio
    async def test_update_event_no_fields(self):
        from msgraph_mcp.server import update_event

        result = await update_event(event_id="evt1")
        assert "No fields provided" in result

    @pytest.mark.asyncio
    async def test_update_event_graph_api_error(self):
        from msgraph_mcp.server import update_event

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.update_event = AsyncMock(
                    side_effect=GraphApiError(404, "Not found: the specified event does not exist.")
                )
                MockGC.return_value = instance

                result = await update_event(event_id="bad-id", subject="X")

        assert "Not found" in result


# ── delete_event ─────────────────────────────────────────────────────


class TestDeleteEventTool:
    @pytest.mark.asyncio
    async def test_delete_event_success(self):
        from msgraph_mcp.server import delete_event

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.delete_event = AsyncMock(return_value=None)
                MockGC.return_value = instance

                result = await delete_event(event_id="evt1")

        assert "deleted successfully" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_event_not_found(self):
        from msgraph_mcp.server import delete_event

        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.delete_event = AsyncMock(
                    side_effect=GraphApiError(404, "Not found: the specified event does not exist.")
                )
                MockGC.return_value = instance

                result = await delete_event(event_id="bad-id")

        assert "Not found" in result


# ── get_availability ─────────────────────────────────────────────────


class TestGetAvailability:
    @pytest.mark.asyncio
    async def test_get_availability_full(self):
        from msgraph_mcp.server import get_availability

        schedule = {
            "scheduleId": "user@example.com",
            "scheduleItems": [
                {
                    "status": "busy",
                    "subject": "Team Standup",
                    "start": {"dateTime": "2026-04-01T09:00:00.0000000"},
                    "end": {"dateTime": "2026-04-01T09:30:00.0000000"},
                },
            ],
        }
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_schedule = AsyncMock(return_value=schedule)
                MockGC.return_value = instance

                result = await get_availability(
                    start_time="2026-04-01T08:00:00",
                    end_time="2026-04-01T17:00:00",
                )

        assert "Availability from" in result
        assert "Busy" in result
        assert "Team Standup" in result

    @pytest.mark.asyncio
    async def test_get_availability_free(self):
        from msgraph_mcp.server import get_availability

        schedule = {"scheduleId": "user@example.com", "scheduleItems": []}
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_schedule = AsyncMock(return_value=schedule)
                MockGC.return_value = instance

                result = await get_availability(
                    start_time="2026-04-01T08:00:00",
                    end_time="2026-04-01T17:00:00",
                )

        assert "free for the entire period" in result.lower()

    @pytest.mark.asyncio
    async def test_get_availability_check_only_free(self):
        from msgraph_mcp.server import get_availability

        schedule = {"scheduleId": "user@example.com", "scheduleItems": []}
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_schedule = AsyncMock(return_value=schedule)
                MockGC.return_value = instance

                result = await get_availability(
                    start_time="2026-04-01T08:00:00",
                    end_time="2026-04-01T17:00:00",
                    check_only=True,
                )

        assert "free" in result.lower()
        assert "2026-04-01T08:00:00" in result

    @pytest.mark.asyncio
    async def test_get_availability_check_only_busy(self):
        from msgraph_mcp.server import get_availability

        schedule = {
            "scheduleId": "user@example.com",
            "scheduleItems": [
                {"status": "busy", "start": {"dateTime": "2026-04-01T09:00:00"}, "end": {"dateTime": "2026-04-01T10:00:00"}},
            ],
        }
        patches = _patch_auth()
        with patches["get_access_token"], patches["get_user_email"], patches["get_microsoft_token"]:
            with patch("msgraph_mcp.server.GraphClient") as MockGC:
                instance = AsyncMock()
                instance.get_schedule = AsyncMock(return_value=schedule)
                MockGC.return_value = instance

                result = await get_availability(
                    start_time="2026-04-01T08:00:00",
                    end_time="2026-04-01T17:00:00",
                    check_only=True,
                )

        assert "busy" in result.lower()

    @pytest.mark.asyncio
    async def test_get_availability_missing_times(self):
        from msgraph_mcp.server import get_availability

        result = await get_availability(start_time="", end_time="2026-04-01T17:00:00")
        assert "Validation error" in result
        assert "start_time" in result

    @pytest.mark.asyncio
    async def test_get_availability_start_after_end(self):
        from msgraph_mcp.server import get_availability

        result = await get_availability(
            start_time="2026-04-02T08:00:00",
            end_time="2026-04-01T17:00:00",
        )
        assert "Validation error" in result

    @pytest.mark.asyncio
    async def test_get_availability_auth_failure(self):
        from msgraph_mcp.server import get_availability

        with patch("msgraph_mcp.server.get_access_token", return_value=None):
            result = await get_availability(
                start_time="2026-04-01T08:00:00",
                end_time="2026-04-01T17:00:00",
            )

        assert "Authentication required" in result
