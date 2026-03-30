# Data Model: Email Tools

**Feature Branch**: `003-email-tools`
**Date**: 2026-03-30

## Overview

This feature does not introduce local data models or database tables. All data lives in Microsoft Graph and is accessed via REST API calls. The entities below describe the Graph API resource shapes that the MCP tools consume and produce.

## Entities

### MailFolder

Represents a mail folder in the authenticated user's mailbox (e.g., Inbox, Sent Items, Drafts).

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Opaque identifier assigned by Graph API |
| `displayName` | `str` | User-visible name of the folder (e.g., "Inbox", "Sent Items") |
| `totalItemCount` | `int` | Total number of messages in the folder |
| `unreadItemCount` | `int` | Number of unread messages in the folder |

**Graph API resource**: `mailFolder`
**Endpoint**: `GET /me/mailFolders`

**Notes**:
- Every Microsoft account has standard folders: Inbox, Drafts, Sent Items, Deleted Items, Junk Email.
- Users may also have custom folders.
- Child folders (subfolders) are out of scope for this feature.

---

### Message

Represents a single email message in the user's mailbox.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Opaque identifier assigned by Graph API |
| `subject` | `str` | Subject line of the email |
| `from` | `emailAddress` | Sender's email address (nested object) |
| `toRecipients` | `list[emailAddress]` | List of To recipients |
| `ccRecipients` | `list[emailAddress]` | List of CC recipients |
| `receivedDateTime` | `str` | ISO 8601 timestamp when the message was received |
| `isRead` | `bool` | Whether the message has been read |
| `importance` | `str` | `"low"`, `"normal"`, or `"high"` |
| `bodyPreview` | `str` | Auto-generated plain-text preview (max ~255 chars) |
| `body` | `body` | Full message body (nested object) |

**Nested type: `emailAddress`**

```json
{
  "emailAddress": {
    "name": "John Doe",
    "address": "john@example.com"
  }
}
```

**Nested type: `body`**

```json
{
  "contentType": "text",
  "content": "Hello, this is the email body."
}
```

- `contentType` is either `"text"` or `"html"`.
- When `contentType` is `"html"`, the content contains HTML markup that must be stripped for terminal display.

**Graph API resource**: `message`
**Endpoints**:
- `GET /me/messages` — list messages across all folders
- `GET /me/mailFolders/{folderId}/messages` — list messages in a specific folder
- `GET /me/messages/{messageId}` — get a single message

**Notes**:
- `from` is a reserved keyword in the Graph API perspective — it's always nested as `from.emailAddress.name` / `from.emailAddress.address`.
- Attachments are out of scope for this feature.
- The `body.content` field can be very large for HTML emails. List views use truncated previews; single reads return the full text.

---

### SendMail Request (outbound only)

Represents the payload for sending an email via `POST /me/sendMail`. This is not a stored entity — it is a request body.

```json
{
  "message": {
    "subject": "Meeting tomorrow",
    "body": {
      "contentType": "text",
      "content": "Hi, let's meet at 10am."
    },
    "toRecipients": [
      { "emailAddress": { "name": "", "address": "recipient@example.com" } }
    ],
    "ccRecipients": [
      { "emailAddress": { "name": "", "address": "cc@example.com" } }
    ]
  }
}
```

**Notes**:
- `body.contentType` is always set to `"text"` since the MCP tool accepts plain-text input.
- `toRecipients` is required and must contain at least one entry.
- `ccRecipients` is optional (empty array if not provided).
- The endpoint returns `202 Accepted` with no response body on success.

## Relationships

```
User (authenticated)
 └── MailFolder (1:many)
      └── Message (1:many)
```

A user owns multiple mail folders. Each folder contains multiple messages. All access is scoped to the authenticated user via the `Mail.Read` and `Mail.Send` permissions.

## No Local Storage

All state is managed by Microsoft Graph. The MCP server is stateless with respect to email data — it acts purely as a passthrough between the AI client and the Graph API.
