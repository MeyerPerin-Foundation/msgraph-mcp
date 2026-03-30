# Quickstart: Email Tools

**Feature Branch**: `003-email-tools`

## Prerequisites

1. The `msgraph-mcp` server is deployed to Azure App Service (or running locally).
2. You have authenticated with your Microsoft personal account through the MCP OAuth flow.
3. The `Mail.Read` scope has been consented (required for reading emails).
4. The `Mail.Send` scope has been consented (required for sending emails).

## Usage from Copilot CLI

Once the server is deployed and you are authenticated, you can interact with your email through natural language. The AI assistant will call the appropriate MCP tools behind the scenes.

### List Your Mail Folders

> "Show me my mail folders"

The assistant calls `list_mail_folders` and returns the names, IDs, and message counts for all your mail folders (Inbox, Sent Items, Drafts, etc.).

### View Recent Emails

> "Show me my latest emails"

The assistant calls `list_messages` and returns your 10 most recent emails with sender, subject, date, and a preview of the body.

> "Show me emails in my Sent Items folder"

The assistant calls `list_mail_folders` to find the Sent Items folder ID, then calls `list_messages` with that folder ID.

> "Show me my last 5 emails"

The assistant calls `list_messages` with `count=5`.

### Read a Specific Email

> "Read the email about the budget report"

The assistant identifies the message from a previous listing and calls `read_message` with the message ID. The full email is returned with all recipients, subject, date, and complete body text.

### Search Emails

> "Search my emails for 'project proposal'"

The assistant calls `search_messages` with the query and returns matching messages sorted by relevance.

> "Find emails from John about the quarterly review"

The assistant calls `search_messages` with a relevant query string.

### Send an Email

> "Send an email to john@example.com with subject 'Meeting tomorrow' saying 'Hi John, let's meet at 10am.'"

The assistant calls `send_message` with the recipient, subject, and body. A confirmation is returned after the email is sent.

> "Email john@example.com and jane@example.com, CC manager@example.com, about the project update"

The assistant calls `send_message` with multiple To and CC recipients.

## Tips

- **List first**: If you need to read emails from a specific folder, ask to see your mail folders first. The assistant will use the returned IDs for follow-up operations.
- **Body previews**: When listing emails, body content is truncated to 500 characters. Ask to "read" a specific email to see the full content.
- **Search scope**: Email search spans your entire mailbox, not just the inbox.
- **Plain text**: Email bodies are displayed as plain text. HTML formatting is stripped for readability in the terminal.
- **Multiple recipients**: When sending, separate email addresses with commas (e.g., "john@example.com, jane@example.com").

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Authentication failed" | MCP token expired or invalid | Re-authenticate with the MCP server |
| "Not found" on a message | Message ID is stale (message was deleted or moved) | List messages again to get current IDs |
| "Access denied" when sending | `Mail.Send` scope not consented | Re-authenticate and consent to the required scope |
| "Access denied" when reading | `Mail.Read` scope not consented | Re-authenticate and consent to the required scope |
| "Rate limited" | Too many requests to Graph API | Wait a moment and retry |
| Garbled email body | Complex HTML email with nested tables/styles | Expected — HTML stripping is intentionally simple |
