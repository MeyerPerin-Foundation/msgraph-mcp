"""Tests for the GraphClient Microsoft Graph API wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from msgraph_mcp.graph import GRAPH_BASE_URL, GraphApiError, GraphClient, _extract_body_text, strip_html


# ── Helpers ───────────────────────────────────────────────────────────


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> httpx.Response:
    """Build a fake httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "https://example.com"),
    )
    return resp


# ── GraphApiError ─────────────────────────────────────────────────────


class TestGraphApiError:
    def test_fields(self):
        err = GraphApiError(status_code=404, message="Not found", detail="extra")
        assert err.status_code == 404
        assert err.message == "Not found"
        assert err.detail == "extra"
        assert str(err) == "Not found"

    def test_optional_detail(self):
        err = GraphApiError(status_code=500, message="Server error")
        assert err.detail is None


# ── _request helper ───────────────────────────────────────────────────


class TestRequest:
    @pytest.mark.asyncio
    async def test_success(self):
        client = GraphClient("tok")
        mock_resp = _mock_response(200, {"value": []})
        with patch("msgraph_mcp.graph.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.request = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            resp = await client._request("GET", "/me/todo/lists")
            assert resp.status_code == 200
            instance.request.assert_called_once_with(
                "GET",
                f"{GRAPH_BASE_URL}/me/todo/lists",
                headers={"Authorization": "Bearer tok"},
                json=None,
            )

    @pytest.mark.asyncio
    async def test_401_error(self):
        client = GraphClient("bad-tok")
        mock_resp = _mock_response(401, {"error": {"message": "Invalid token"}})
        with patch("msgraph_mcp.graph.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.request = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with pytest.raises(GraphApiError) as exc_info:
                await client._request("GET", "/me/todo/lists")
            assert exc_info.value.status_code == 401
            assert "re-authenticate" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_404_error(self):
        client = GraphClient("tok")
        mock_resp = _mock_response(404, {"error": {"message": "Resource not found"}})
        with patch("msgraph_mcp.graph.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.request = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with pytest.raises(GraphApiError) as exc_info:
                await client._request("GET", "/me/todo/lists/bad", resource="task list")
            assert exc_info.value.status_code == 404
            assert "task list" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_500_error(self):
        client = GraphClient("tok")
        mock_resp = _mock_response(500, {"error": {"message": "Internal server error"}})
        with patch("msgraph_mcp.graph.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.request = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with pytest.raises(GraphApiError) as exc_info:
                await client._request("GET", "/me/todo/lists")
            assert exc_info.value.status_code == 500
            assert "service error" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_network_error(self):
        client = GraphClient("tok")
        with patch("msgraph_mcp.graph.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.request = AsyncMock(side_effect=httpx.ConnectError("fail"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with pytest.raises(GraphApiError) as exc_info:
                await client._request("GET", "/me/todo/lists")
            assert exc_info.value.status_code == 0
            assert "could not reach" in exc_info.value.message.lower()


# ── get_task_lists ────────────────────────────────────────────────────


class TestGetTaskLists:
    @pytest.mark.asyncio
    async def test_returns_lists(self):
        client = GraphClient("tok")
        sample = [
            {"id": "list1", "displayName": "Tasks", "wellknownListName": "defaultList"},
            {"id": "list2", "displayName": "Shopping"},
        ]
        client._request = AsyncMock(return_value=_mock_response(200, {"value": sample}))
        result = await client.get_task_lists()
        assert result == sample

    @pytest.mark.asyncio
    async def test_empty_lists(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(200, {"value": []}))
        result = await client.get_task_lists()
        assert result == []


# ── get_tasks ─────────────────────────────────────────────────────────


class TestGetTasks:
    @pytest.mark.asyncio
    async def test_returns_tasks(self):
        client = GraphClient("tok")
        sample = [
            {"id": "t1", "title": "Buy milk", "status": "notStarted", "importance": "normal"},
        ]
        client._request = AsyncMock(return_value=_mock_response(200, {"value": sample}))
        result = await client.get_tasks("list1")
        assert result == sample

    @pytest.mark.asyncio
    async def test_empty_tasks(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(200, {"value": []}))
        result = await client.get_tasks("list1")
        assert result == []


# ── get_default_list_id ───────────────────────────────────────────────


class TestGetDefaultListId:
    @pytest.mark.asyncio
    async def test_finds_default(self):
        client = GraphClient("tok")
        client.get_task_lists = AsyncMock(return_value=[
            {"id": "list1", "displayName": "Custom"},
            {"id": "list2", "displayName": "Tasks", "wellknownListName": "defaultList"},
        ])
        result = await client.get_default_list_id()
        assert result == "list2"

    @pytest.mark.asyncio
    async def test_falls_back_to_first(self):
        client = GraphClient("tok")
        client.get_task_lists = AsyncMock(return_value=[
            {"id": "list1", "displayName": "Custom"},
        ])
        result = await client.get_default_list_id()
        assert result == "list1"

    @pytest.mark.asyncio
    async def test_no_lists_raises(self):
        client = GraphClient("tok")
        client.get_task_lists = AsyncMock(return_value=[])
        with pytest.raises(GraphApiError):
            await client.get_default_list_id()


# ── create_task ───────────────────────────────────────────────────────


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_creates_with_all_fields(self):
        client = GraphClient("tok")
        created = {"id": "t1", "title": "New task", "status": "notStarted"}
        client._request = AsyncMock(return_value=_mock_response(200, created))

        result = await client.create_task("list1", "New task", body="Notes", due_date="2024-01-20")
        assert result == created

        call_args = client._request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["title"] == "New task"
        assert payload["body"] == {"content": "Notes", "contentType": "text"}
        assert payload["dueDateTime"]["dateTime"] == "2024-01-20T00:00:00.0000000"
        assert payload["dueDateTime"]["timeZone"] == "UTC"

    @pytest.mark.asyncio
    async def test_creates_title_only(self):
        client = GraphClient("tok")
        created = {"id": "t2", "title": "Simple"}
        client._request = AsyncMock(return_value=_mock_response(200, created))

        result = await client.create_task("list1", "Simple")
        assert result == created

        call_args = client._request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "body" not in payload
        assert "dueDateTime" not in payload


# ── update_task ───────────────────────────────────────────────────────


class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_update_title(self):
        client = GraphClient("tok")
        updated = {"id": "t1", "title": "Updated title"}
        client._request = AsyncMock(return_value=_mock_response(200, updated))

        result = await client.update_task("list1", "t1", title="Updated title")
        assert result == updated

        call_args = client._request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload == {"title": "Updated title"}

    @pytest.mark.asyncio
    async def test_update_status_and_due_date(self):
        client = GraphClient("tok")
        updated = {"id": "t1", "title": "Task", "status": "completed"}
        client._request = AsyncMock(return_value=_mock_response(200, updated))

        result = await client.update_task(
            "list1", "t1", status="completed", due_date="2025-06-15"
        )
        assert result["status"] == "completed"

        call_args = client._request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["status"] == "completed"
        assert payload["dueDateTime"]["dateTime"] == "2025-06-15T00:00:00.0000000"

    @pytest.mark.asyncio
    async def test_update_body_and_importance(self):
        client = GraphClient("tok")
        updated = {"id": "t1", "title": "Task"}
        client._request = AsyncMock(return_value=_mock_response(200, updated))

        await client.update_task("list1", "t1", body="New notes", importance="high")

        call_args = client._request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["body"] == {"content": "New notes", "contentType": "text"}
        assert payload["importance"] == "high"


# ── delete_task ───────────────────────────────────────────────────────


class TestDeleteTask:
    @pytest.mark.asyncio
    async def test_delete_success(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(204, {}))
        await client.delete_task("list1", "t1")
        client._request.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        client = GraphClient("tok")
        client._request = AsyncMock(
            side_effect=GraphApiError(404, "Not found: the specified task does not exist.")
        )
        with pytest.raises(GraphApiError) as exc_info:
            await client.delete_task("list1", "bad-id")
        assert exc_info.value.status_code == 404


# ── strip_html ────────────────────────────────────────────────────────


class TestStripHtml:
    def test_simple_html(self):
        assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_nested_tags(self):
        html = "<div><ul><li>Item 1</li><li>Item 2</li></ul></div>"
        result = strip_html(html)
        assert "Item 1" in result
        assert "Item 2" in result

    def test_empty_input(self):
        assert strip_html("") == ""

    def test_plain_text_passthrough(self):
        assert strip_html("no tags here") == "no tags here"


# ── _extract_body_text ────────────────────────────────────────────────


class TestExtractBodyText:
    def test_plain_text_body(self):
        msg = {"body": {"contentType": "text", "content": "Hello world"}}
        assert _extract_body_text(msg) == "Hello world"

    def test_html_body(self):
        msg = {"body": {"contentType": "html", "content": "<p>Hello</p>"}}
        assert _extract_body_text(msg) == "Hello"

    def test_truncation(self):
        long_text = "A" * 600
        msg = {"body": {"contentType": "text", "content": long_text}}
        result = _extract_body_text(msg, max_length=500)
        assert len(result) == 503  # 500 + "..."
        assert result.endswith("...")

    def test_no_truncation_when_short(self):
        msg = {"body": {"contentType": "text", "content": "Short"}}
        result = _extract_body_text(msg, max_length=500)
        assert result == "Short"

    def test_missing_body(self):
        assert _extract_body_text({}) == ""

    def test_none_body(self):
        assert _extract_body_text({"body": None}) == ""


# ── get_mail_folders ──────────────────────────────────────────────────


class TestGetMailFolders:
    @pytest.mark.asyncio
    async def test_returns_folders(self):
        client = GraphClient("tok")
        sample = [
            {"id": "f1", "displayName": "Inbox", "totalItemCount": 100, "unreadItemCount": 5},
            {"id": "f2", "displayName": "Sent Items", "totalItemCount": 50, "unreadItemCount": 0},
        ]
        client._request = AsyncMock(return_value=_mock_response(200, {"value": sample}))
        result = await client.get_mail_folders()
        assert result == sample

    @pytest.mark.asyncio
    async def test_empty_folders(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(200, {"value": []}))
        result = await client.get_mail_folders()
        assert result == []


# ── get_messages ──────────────────────────────────────────────────────


class TestGetMessages:
    @pytest.mark.asyncio
    async def test_inbox_messages(self):
        client = GraphClient("tok")
        sample = [{"id": "m1", "subject": "Hello"}]
        client._request = AsyncMock(return_value=_mock_response(200, {"value": sample}))
        result = await client.get_messages()
        assert result == sample
        call_args = client._request.call_args
        path = call_args[0][1]
        assert "/me/messages?" in path
        assert "$orderby=receivedDateTime" in path

    @pytest.mark.asyncio
    async def test_folder_messages(self):
        client = GraphClient("tok")
        sample = [{"id": "m2", "subject": "Folder msg"}]
        client._request = AsyncMock(return_value=_mock_response(200, {"value": sample}))
        result = await client.get_messages(folder_id="f1", count=5)
        assert result == sample
        call_args = client._request.call_args
        path = call_args[0][1]
        assert "/me/mailFolders/f1/messages?" in path
        assert "$top=5" in path

    @pytest.mark.asyncio
    async def test_empty_messages(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(200, {"value": []}))
        result = await client.get_messages()
        assert result == []


# ── get_message ───────────────────────────────────────────────────────


class TestGetMessage:
    @pytest.mark.asyncio
    async def test_returns_message(self):
        client = GraphClient("tok")
        msg = {"id": "m1", "subject": "Test", "body": {"contentType": "text", "content": "Hi"}}
        client._request = AsyncMock(return_value=_mock_response(200, msg))
        result = await client.get_message("m1")
        assert result == msg

    @pytest.mark.asyncio
    async def test_not_found(self):
        client = GraphClient("tok")
        client._request = AsyncMock(
            side_effect=GraphApiError(404, "Not found: the specified message does not exist.")
        )
        with pytest.raises(GraphApiError) as exc_info:
            await client.get_message("bad-id")
        assert exc_info.value.status_code == 404


# ── search_messages ───────────────────────────────────────────────────


class TestSearchMessages:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        client = GraphClient("tok")
        sample = [{"id": "m1", "subject": "Budget"}]
        client._request = AsyncMock(return_value=_mock_response(200, {"value": sample}))
        result = await client.search_messages("budget")
        assert result == sample
        call_args = client._request.call_args
        path = call_args[0][1]
        assert '$search="budget"' in path
        assert "$orderby" not in path

    @pytest.mark.asyncio
    async def test_empty_results(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(200, {"value": []}))
        result = await client.search_messages("nonexistent")
        assert result == []


# ── send_message ──────────────────────────────────────────────────────


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_returns_none(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(202, None))
        result = await client.send_message(
            to=["user@example.com"], subject="Hi", body="Hello"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_send_with_cc(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(202, None))
        await client.send_message(
            to=["a@example.com"],
            subject="Hi",
            body="Hello",
            cc=["b@example.com"],
        )
        call_args = client._request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert len(payload["message"]["ccRecipients"]) == 1
        assert payload["message"]["ccRecipients"][0]["emailAddress"]["address"] == "b@example.com"

    @pytest.mark.asyncio
    async def test_send_payload_structure(self):
        client = GraphClient("tok")
        client._request = AsyncMock(return_value=_mock_response(202, None))
        await client.send_message(
            to=["a@test.com", "b@test.com"], subject="Subj", body="Body"
        )
        call_args = client._request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        msg = payload["message"]
        assert msg["subject"] == "Subj"
        assert msg["body"] == {"contentType": "text", "content": "Body"}
        assert len(msg["toRecipients"]) == 2

    @pytest.mark.asyncio
    async def test_send_403_error(self):
        client = GraphClient("tok")
        client._request = AsyncMock(
            side_effect=GraphApiError(403, "Access denied. The required permissions may not be granted.")
        )
        with pytest.raises(GraphApiError) as exc_info:
            await client.send_message(to=["a@test.com"], subject="X", body="Y")
        assert exc_info.value.status_code == 403
