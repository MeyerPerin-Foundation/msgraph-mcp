# Research: Email Tools

**Feature Branch**: `003-email-tools`
**Date**: 2026-03-30

## R1: Graph Mail API Endpoints

**Decision**: Use the Microsoft Graph v1.0 Mail API for all operations.

**Base URL**: `https://graph.microsoft.com/v1.0`

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List mail folders | GET | `/me/mailFolders` |
| List messages (inbox) | GET | `/me/messages?$top={count}&$orderby=receivedDateTime desc` |
| List messages (folder) | GET | `/me/mailFolders/{folderId}/messages?$top={count}&$orderby=receivedDateTime desc` |
| Get message | GET | `/me/messages/{messageId}` |
| Search messages | GET | `/me/messages?$search="{query}"&$top={count}` |
| Send message | POST | `/me/sendMail` |

**Notes**:
- The `/me/messages` endpoint returns messages across all folders by default. Adding `$orderby=receivedDateTime desc` ensures most recent messages appear first.
- For folder-specific listing, use `/me/mailFolders/{folderId}/messages` with the same query parameters.
- The Graph API returns `@odata.nextLink` for pagination. For the initial implementation, we fetch only the first page (controlled by `$top`).

---

## R2: HTML-to-Text Conversion for Email Bodies

**Decision**: Use Python's `html.parser` stdlib module for simple tag stripping. No new dependencies.

**Details**:

Email messages in Graph API have a `body` object with `contentType` ("text" or "html") and `content`. The strategy:

1. If `body.contentType == "text"`, use `body.content` directly.
2. If `body.contentType == "html"`, strip HTML tags using a simple `HTMLParser` subclass that collects text content.
3. After stripping, normalize whitespace (collapse multiple blank lines, trim).

**Why not `beautifulsoup4` or `html2text`?** Adding a new dependency for simple tag stripping violates the principle of minimal dependencies. The stdlib `html.parser` handles the common case of extracting readable text from HTML email bodies. Complex formatting (tables, nested lists) may lose structure, but this is acceptable for terminal output.

**Implementation sketch**:

```python
from html.parser import HTMLParser

class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text: list[str] = []

    def handle_data(self, data: str) -> None:
        self._text.append(data)

    def get_text(self) -> str:
        return "".join(self._text)

def strip_html(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text().strip()
```

---

## R3: Message Body Truncation

**Decision**: Default to 500-character preview for list views; full body for single-message reads.

**Details**:

- `list_messages` and `search_messages` return a truncated body preview (first 500 characters of plain text, with `"..."` appended if truncated). This keeps terminal output manageable when listing 10+ messages.
- `read_message` returns the complete body text with no truncation.
- Graph API's `bodyPreview` field (max ~255 chars, auto-generated) is available but we prefer our own truncation from the full body for consistency and to allow a configurable length.

---

## R4: Search API

**Decision**: Use `GET /me/messages?$search="keyword"` with Graph's built-in KQL-style search.

**Details**:

- Graph API supports a `$search` query parameter on the `/me/messages` endpoint.
- The search query uses KQL (Keyword Query Language) syntax and searches across subject, body, sender, and other message fields.
- Example: `GET /me/messages?$search="budget report"&$top=10`
- The `$search` parameter cannot be combined with `$orderby` (Graph API limitation). Results are returned in relevance order.
- The search query string is passed directly to Graph — the MCP tool does not parse or validate KQL syntax.

**Limitations**:
- `$search` is not supported on folder-scoped endpoints for consumer accounts. Search always spans the entire mailbox.
- Complex KQL operators (AND, OR, from:, subject:) may or may not work depending on the consumer mailbox index.

---

## R5: Send Email API

**Decision**: Use `POST /me/sendMail` with a `message` object.

**Details**:

The Graph API's `/me/sendMail` endpoint accepts a JSON body with a `message` object and an optional `saveToSentItems` flag (defaults to `true`).

**Request body structure**:

```json
{
  "message": {
    "subject": "Hello",
    "body": {
      "contentType": "text",
      "content": "This is the email body."
    },
    "toRecipients": [
      { "emailAddress": { "name": "", "address": "user@example.com" } }
    ],
    "ccRecipients": [
      { "emailAddress": { "name": "", "address": "cc@example.com" } }
    ]
  }
}
```

**Notes**:
- The endpoint returns `202 Accepted` with no response body on success.
- We always set `body.contentType` to `"text"` since the MCP tool accepts plain text input.
- `to` and `cc` parameters in the MCP tool are comma-separated email address strings, parsed into the `emailAddress` array format.
- `saveToSentItems` defaults to `true` (Graph default), so sent messages appear in the user's Sent Items folder.

---

## R6: Mail.Send Scope

**Decision**: Add `Mail.Send` to the `GRAPH_SCOPES` list in `config.py`.

**Details**:

- `Mail.Send` has already been added to the Azure app registration's API permissions.
- The MSAL consent flow requests all scopes in `GRAPH_SCOPES` during the initial interactive authentication.
- Adding `Mail.Send` to the list means existing users will need to re-consent (MSAL will prompt automatically on next interactive login).
- `Mail.Read` is already present in `GRAPH_SCOPES`.

**Change**:

```python
GRAPH_SCOPES: list[str] = [
    "User.Read",
    "Mail.Read",
    "Mail.Send",        # NEW
    "Calendars.Read",
    "Tasks.ReadWrite",
    "Files.Read",
]
```

---

## R7: Code Organization

**Decision**: Add mail methods to the existing `GraphClient` class in `graph.py`. Update the module docstring.

**Details**:

- The `GraphClient` class in `graph.py` already has the `_request()` helper, token management, and error handling. Adding mail methods alongside To-Do methods keeps all Graph API interactions in one place.
- The module docstring currently says "To-Do operations" — update it to "Microsoft Graph API operations" to reflect the broader scope.
- New methods: `get_mail_folders()`, `get_messages()`, `get_message()`, `search_messages()`, `send_message()`
- Each method follows the existing pattern: call `_request()`, return the parsed JSON (or `None` for void responses like send).
- MCP tool functions in `server.py` will call these methods and format the responses as plain text strings.

**Why not a separate `MailClient` class?** A separate class would duplicate the token handling and `_request()` infrastructure. Since `GraphClient` is a thin wrapper, keeping all methods in one class is simpler and consistent with Constitution Principle I.
