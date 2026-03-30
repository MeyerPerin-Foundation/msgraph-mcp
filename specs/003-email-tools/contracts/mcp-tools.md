# MCP Tool Contracts: Email Tools

**Feature Branch**: `003-email-tools`
**Date**: 2026-03-30

## Overview

Five MCP tools are added to `server.py` for email operations via the Microsoft Graph Mail API. All tools require the user to be authenticated via the existing OAuth flow. All tools return plain-text string responses suitable for AI assistant consumption.

---

## `list_mail_folders`

**Purpose**: Retrieve the user's mail folders with message counts.

**Parameters**: None

**Returns**: Formatted string listing all mail folders with their IDs, display names, total message counts, and unread counts.

**Example response**:
```
Found 6 mail folders:

1. Inbox (id: AAMkADI...) — 142 messages, 3 unread
2. Drafts (id: AAMkADJ...) — 5 messages, 0 unread
3. Sent Items (id: AAMkADK...) — 89 messages, 0 unread
4. Deleted Items (id: AAMkADL...) — 12 messages, 0 unread
5. Junk Email (id: AAMkADM...) — 7 messages, 0 unread
6. Archive (id: AAMkADN...) — 230 messages, 0 unread
```

**Graph API call**: `GET /me/mailFolders`

**Error cases**:
- Authentication failure → `"Authentication failed. Please re-authenticate."`
- Graph service error → `"Microsoft Graph service error. Please try again later."`

---

## `list_messages`

**Purpose**: Retrieve recent email messages from the inbox or a specific folder.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `folder_id` | `str \| None` | No | `None` | Mail folder ID. If omitted, lists messages from all folders (default inbox view). |
| `count` | `int` | No | `10` | Number of messages to retrieve (max page size). |

**Returns**: Formatted string listing messages with sender, subject, date, body preview, and read status.

**Example response**:
```
Found 10 messages:

1. [Unread] From: John Doe <john@example.com>
   Subject: Budget Report Q4
   Date: 2026-03-30 14:22 UTC
   Preview: Hi team, please find attached the Q4 budget report. Key highlights include...

2. [Read] From: Jane Smith <jane@example.com>
   Subject: Re: Meeting tomorrow
   Date: 2026-03-30 10:15 UTC
   Preview: Sounds good, see you at 10am!

...
```

**Graph API call**:
- Without `folder_id`: `GET /me/messages?$top={count}&$orderby=receivedDateTime desc`
- With `folder_id`: `GET /me/mailFolders/{folder_id}/messages?$top={count}&$orderby=receivedDateTime desc`

**Body preview**: The body content is converted to plain text (HTML stripped if necessary) and truncated to 500 characters with `"..."` appended if truncated.

**Error cases**:
- Folder not found → `"Not found: the specified mail folder does not exist."`
- Authentication failure → `"Authentication failed. Please re-authenticate."`

---

## `read_message`

**Purpose**: Retrieve the full content of a specific email message.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `message_id` | `str` | Yes | The ID of the message to read |

**Returns**: Formatted string with the complete message details including all recipients and full body text.

**Example response**:
```
Subject: Budget Report Q4
From: John Doe <john@example.com>
To: team@example.com, manager@example.com
CC: finance@example.com
Date: 2026-03-30 14:22 UTC
Importance: normal
Status: Unread

Body:
Hi team,

Please find attached the Q4 budget report. Key highlights include:
- Revenue increased 12% YoY
- Operating costs remained flat
- Net margin improved to 18%

Let me know if you have questions.

Best,
John
```

**Graph API call**: `GET /me/messages/{message_id}`

**Body handling**: The body content is converted to plain text (HTML stripped if necessary). No truncation is applied for single-message reads.

**Error cases**:
- Message not found → `"Not found: the specified message does not exist."`
- Authentication failure → `"Authentication failed. Please re-authenticate."`

---

## `search_messages`

**Purpose**: Search email messages by keyword across the entire mailbox.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | `str` | Yes | — | Search query (supports KQL-style keywords) |
| `count` | `int` | No | `10` | Maximum number of results to return |

**Returns**: Formatted string listing matching messages with sender, subject, date, and body preview.

**Example response**:
```
Found 3 messages matching "budget report":

1. [Unread] From: John Doe <john@example.com>
   Subject: Budget Report Q4
   Date: 2026-03-30 14:22 UTC
   Preview: Hi team, please find attached the Q4 budget report...

2. [Read] From: Finance Team <finance@example.com>
   Subject: Q3 Budget Report Review
   Date: 2026-02-15 09:00 UTC
   Preview: The Q3 budget report has been finalized...

3. [Read] From: John Doe <john@example.com>
   Subject: Re: Budget report questions
   Date: 2026-01-20 16:45 UTC
   Preview: Good questions — I'll address them in the next revision...
```

**Graph API call**: `GET /me/messages?$search="{query}"&$top={count}`

**Notes**:
- `$search` cannot be combined with `$orderby` — results are returned in relevance order.
- The search query is passed directly to Graph without parsing or validation.
- Empty results return: `"No messages found matching \"{query}\"."`

**Error cases**:
- Authentication failure → `"Authentication failed. Please re-authenticate."`
- Graph service error → `"Microsoft Graph service error. Please try again later."`

---

## `send_message`

**Purpose**: Send an email message on behalf of the authenticated user.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `to` | `str` | Yes | — | Comma-separated list of recipient email addresses |
| `subject` | `str` | Yes | — | Email subject line |
| `body` | `str` | Yes | — | Plain-text email body |
| `cc` | `str \| None` | No | `None` | Comma-separated list of CC email addresses |

**Returns**: Confirmation string.

**Example response**:
```
Email sent successfully.

To: john@example.com, jane@example.com
CC: manager@example.com
Subject: Meeting tomorrow
```

**Graph API call**: `POST /me/sendMail`

**Request body**:
```json
{
  "message": {
    "subject": "Meeting tomorrow",
    "body": {
      "contentType": "text",
      "content": "Hi, let's meet at 10am."
    },
    "toRecipients": [
      { "emailAddress": { "name": "", "address": "john@example.com" } },
      { "emailAddress": { "name": "", "address": "jane@example.com" } }
    ],
    "ccRecipients": [
      { "emailAddress": { "name": "", "address": "manager@example.com" } }
    ]
  }
}
```

**Recipient parsing**: The `to` and `cc` strings are split by comma, each entry is trimmed, and wrapped in the `emailAddress` object format. No name resolution is performed — the `name` field is set to an empty string.

**Validation**:
- `to` must contain at least one valid email address.
- `subject` must not be empty.
- `body` must not be empty.

**Error cases**:
- Missing or empty `to` → `"At least one recipient email address is required."`
- Missing or empty `subject` → `"Subject is required."`
- Missing or empty `body` → `"Message body is required."`
- Permission denied (no `Mail.Send` scope) → `"Access denied. The required permissions may not be granted."`
- Authentication failure → `"Authentication failed. Please re-authenticate."`

---

## Common Patterns

### Authentication Flow (all tools)

Identical to the existing To-Do tools — uses `_get_graph_client()` helper in `server.py`:

```python
client = await _get_graph_client()
# client is a GraphClient instance with a valid Microsoft Graph bearer token
```

### Response Formatting

All tools return human-readable plain text, not JSON. The AI assistant can parse and present the information naturally. IDs are included so the user (or AI) can reference them in follow-up operations (e.g., reading a specific message after listing).

### HTML-to-Text Conversion

For email bodies with `contentType == "html"`, a simple `HTMLParser`-based tag stripper converts to plain text. This is applied in `graph.py` helper functions, not in the MCP tool layer.
