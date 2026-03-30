# Feature Specification: Email Tools

**Feature Branch**: `003-email-tools`  
**Created**: 2026-03-30  
**Status**: Draft  
**Input**: User description: "Similar to what you have done with To-Do, now let's create a wrapper around the email functions of MS Graph"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read My Inbox (Priority: P1)

As an authenticated user interacting through Copilot CLI, I want to see my recent email messages so that I can quickly check what's in my inbox without opening Outlook or a browser.

**Why this priority**: Reading email is the most common email operation and the foundation for all other stories. Users need to see their messages before they can reply, search, or manage them.

**Independent Test**: Can be fully tested by authenticating and asking the AI assistant to list recent emails. Delivers immediate value by surfacing the inbox in the terminal.

**Acceptance Scenarios**:

1. **Given** the user is authenticated, **When** they ask to list their recent emails, **Then** the system returns the most recent messages with sender, subject, date, and a preview of the body.
2. **Given** the user is authenticated, **When** they ask to list emails from a specific folder (e.g., "Sent Items"), **Then** the system returns messages from that folder.
3. **Given** the user is authenticated and specifies a message, **When** they ask to read that email, **Then** the system returns the full message including sender, recipients, subject, date, and complete body text.

---

### User Story 2 - Search Emails (Priority: P2)

As an authenticated user, I want to search my emails by keyword so that I can quickly find specific messages without manually browsing folders.

**Why this priority**: Email search is the second most valuable operation — it lets users locate specific information efficiently, which is a natural use case when working in the terminal.

**Independent Test**: Can be tested by asking the assistant to search for emails matching a keyword and verifying relevant results are returned.

**Acceptance Scenarios**:

1. **Given** the user is authenticated and provides a search query, **When** they search their emails, **Then** the system returns matching messages with sender, subject, date, and a snippet showing the match context.
2. **Given** the user searches for a term with no matches, **When** the search completes, **Then** the system returns a clear message indicating no results were found.

---

### User Story 3 - Send Email (Priority: P3)

As an authenticated user, I want to send emails through the AI assistant so that I can compose and send messages without leaving the terminal.

**Why this priority**: Sending email completes the core email workflow — users can read, search, and now respond or initiate conversations. This requires an additional permission scope (`Mail.Send`).

**Independent Test**: Can be tested by sending a test email to the user's own address and verifying it arrives in the inbox.

**Acceptance Scenarios**:

1. **Given** the user is authenticated and provides recipients, subject, and body, **When** they ask to send an email, **Then** the system sends the message and returns a confirmation.
2. **Given** the user provides multiple recipients (To, CC), **When** they send the email, **Then** all recipients receive the message.
3. **Given** the user omits required fields (no recipients or no subject), **When** they try to send, **Then** the system returns a validation error indicating what's missing.

---

### User Story 4 - List Mail Folders (Priority: P4)

As an authenticated user, I want to see my mail folders so that I can browse emails in specific folders like Drafts, Sent Items, or custom folders.

**Why this priority**: Folder listing supports the inbox reading story by letting users discover and navigate their folder structure. It's a supporting operation rather than a primary workflow.

**Independent Test**: Can be tested by asking the assistant to list mail folders and verifying standard folders (Inbox, Sent Items, Drafts) appear.

**Acceptance Scenarios**:

1. **Given** the user is authenticated, **When** they ask to list their mail folders, **Then** the system returns the folder names and identifiers, including standard folders and any custom folders.
2. **Given** the user has no custom folders, **When** they list folders, **Then** the system returns only the standard mail folders.

---

### Edge Cases

- What happens when the user's Microsoft Graph token has expired and cannot be silently refreshed? The system should return a clear error indicating re-authentication is required.
- What happens when the user tries to read an email that does not exist? The system should return a "not found" error.
- What happens when the user's inbox is empty? The system should return an empty list rather than an error.
- What happens when the user tries to send an email without the `Mail.Send` permission? The system should return a clear error indicating the required permission is not granted.
- What happens when the user provides invalid email addresses as recipients? The system should return a validation error.
- What happens when the email body is very long (e.g., HTML newsletters)? The system should return the plain-text version when available, truncating if necessary for readability.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a tool to list recent email messages from the user's inbox or a specified folder, including sender, subject, received date, and a body preview.
- **FR-002**: System MUST provide a tool to read the full content of a specific email message by its identifier, including sender, all recipients, subject, date, and complete body text.
- **FR-003**: System MUST provide a tool to search email messages by keyword, returning matching messages with sender, subject, date, and match context.
- **FR-004**: System MUST provide a tool to send an email with specified recipients (To and optionally CC), subject, and body text.
- **FR-005**: System MUST provide a tool to list the user's mail folders with their names and identifiers.
- **FR-006**: System MUST map each tool directly to Microsoft Graph Mail API calls with minimal transformation (per Constitution Principle I).
- **FR-007**: System MUST use the authenticated user's Microsoft Graph token to make API calls on their behalf.
- **FR-008**: System MUST return clear error messages when Graph API calls fail (not found, unauthorized, rate limited, permission denied).
- **FR-009**: System MUST prefer plain-text email body content over HTML when both are available, for readability in terminal output.
- **FR-010**: The email reading tools MUST require the `Mail.Read` scope (already configured). The send tool MUST require the `Mail.Send` scope (to be added).

### Key Entities

- **Mail Folder**: A named container for email messages (Inbox, Sent Items, Drafts, etc.). Has a display name, identifier, and message count.
- **Message**: An individual email message. Has sender, recipients (To, CC), subject, body (text and/or HTML), received date, read/unread status, and importance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view their 10 most recent emails within 5 seconds of asking.
- **SC-002**: Users can read the full content of any email by referencing its identifier.
- **SC-003**: Users can search emails by keyword and receive relevant results within 5 seconds.
- **SC-004**: Users can send an email with recipients, subject, and body, and the message is delivered successfully.
- **SC-005**: Users can list their mail folders and see folder names with message counts.
- **SC-006**: All operations return meaningful results or error messages — no silent failures.

## Assumptions

- The user has already authenticated with the MCP server via the existing OAuth flow.
- The `Mail.Read` scope is already consented (it is part of the existing scope configuration).
- The `Mail.Send` scope has been added to the Azure app registration. It needs to be added to `GRAPH_SCOPES` in `config.py` so MSAL requests it during consent.
- Email messages are accessed through the Microsoft Graph Mail API (`/me/messages`, `/me/mailFolders`).
- The system returns a configurable number of recent messages (default 10) to keep terminal output manageable.
- Email attachments are out of scope for this feature — only message metadata and body text are handled.
- Reply and forward operations are out of scope for this feature.
- HTML-to-text conversion for email bodies uses a simple approach (strip tags) rather than a full rendering engine.
