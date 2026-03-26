# Feature Specification: Persistent Credential Cache

**Feature Branch**: `001-persistent-credentials`  
**Created**: 2026-03-26  
**Status**: Draft  
**Input**: User description: "The system should cache credentials that survive restarts"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Survive Server Restarts Without Re-authentication (Priority: P1)

As a user who has already authenticated with the MCP server, I want my session to remain valid after the server restarts (e.g., due to an Azure App Service deployment or recycle), so that I do not need to re-authenticate through the browser every time the server is updated or recycled.

**Why this priority**: This is the core problem. Today, every server restart wipes all authentication state, forcing every connected client to re-register and re-authenticate. This makes the server impractical for production use, especially with automated CI/CD deployments.

**Independent Test**: Can be fully tested by authenticating, restarting the server process, and verifying that a previously issued token still works for tool calls.

**Acceptance Scenarios**:

1. **Given** a user has completed OAuth authentication and holds a valid MCP access token, **When** the server process restarts, **Then** the user's access token remains valid and tool calls succeed without re-authentication.
2. **Given** a user has completed OAuth authentication and holds a valid MCP refresh token, **When** the server process restarts, **Then** the user can obtain a new access token using the refresh token without going through the browser login again.
3. **Given** a user has completed OAuth authentication and the server holds cached Microsoft Graph tokens for that user, **When** the server process restarts, **Then** the server can still make Graph API calls on behalf of that user using the cached tokens.

---

### User Story 2 - Reconnect Without Browser Login (Priority: P2)

As a Copilot CLI user, I want the MCP server to remember my dynamically registered client after a restart, so that Copilot CLI does not need to perform a fresh dynamic client registration and browser-based login every time the server is recycled.

**Why this priority**: Client re-registration is the most visible symptom of the restart problem. When the server forgets the client, Copilot CLI receives a "Client ID not found" error and must start the entire OAuth flow from scratch, including opening a browser window.

**Independent Test**: Can be tested by registering a client, restarting the server, and verifying that the server still recognizes the client ID.

**Acceptance Scenarios**:

1. **Given** a client has been dynamically registered with the server, **When** the server process restarts, **Then** the server still recognizes the client ID and does not return a "Client ID not found" error.
2. **Given** a client has been dynamically registered, **When** the server restarts and the client attempts to use an existing refresh token, **Then** the server issues a new access token without requiring the user to open a browser.

---

### User Story 3 - Graceful Cache Expiry (Priority: P3)

As a server operator, I want expired or revoked credentials to be cleaned up automatically, so that the credential store does not grow unbounded and stale credentials do not remain accessible.

**Why this priority**: Without cleanup, persisted credential data will accumulate over time, potentially growing large and containing stale entries. This is a hygiene concern rather than a core functional requirement.

**Independent Test**: Can be tested by creating credentials with short TTLs, waiting for them to expire, and verifying they are no longer returned by the server.

**Acceptance Scenarios**:

1. **Given** an MCP access token has expired, **When** the server loads credentials from persistent storage, **Then** the expired token is not treated as valid.
2. **Given** an MCP refresh token has been revoked, **When** the server restarts and loads credentials, **Then** the revoked token is not available for use.

---

### Edge Cases

- What happens if the persistent storage file becomes corrupted or unreadable? The server should start with empty state and log a warning rather than crashing.
- What happens if the server is scaled to multiple instances? Each instance would have its own local credential store; cross-instance sharing is out of scope for this feature.
- What happens if the storage medium is full or write-protected? The server should continue operating with in-memory-only state and log a warning.
- What happens during a concurrent restart race (two processes reading/writing the same storage)? The server should handle file locking or use atomic writes to avoid corruption.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist dynamically registered MCP client information across server restarts.
- **FR-002**: System MUST persist issued MCP access tokens (and their associated user email mappings) across server restarts.
- **FR-003**: System MUST persist issued MCP refresh tokens (and their associated user email mappings) across server restarts.
- **FR-004**: System MUST persist the MSAL token cache (Microsoft Graph tokens) across server restarts so that `acquire_token_silent()` continues to work.
- **FR-005**: System MUST NOT persist in-flight OAuth authorization state (pending flows and authorization codes), since these are short-lived and cannot meaningfully survive a restart.
- **FR-006**: System MUST automatically discard expired tokens when loading from persistent storage.
- **FR-007**: System MUST handle storage failures gracefully by falling back to in-memory-only operation with a logged warning.
- **FR-008**: System MUST protect persisted credential data so that it is not world-readable on the file system.
- **FR-009**: System MUST allow the storage location to be configured via an environment variable.

### Key Entities

- **Registered Client**: A dynamically registered MCP OAuth client (client ID, client secret, redirect URIs, scopes, metadata).
- **MCP Access Token**: A server-issued bearer token mapped to a user email, with an expiration time.
- **MCP Refresh Token**: A server-issued refresh token mapped to a user email, with an expiration time.
- **MSAL Token Cache**: The serialized Microsoft token cache containing Graph API access/refresh tokens and account metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a server restart, previously authenticated users can make tool calls without re-authenticating through the browser.
- **SC-002**: After a server restart, previously registered clients are recognized without re-registration.
- **SC-003**: After a server restart, the server can make Microsoft Graph API calls on behalf of previously authenticated users without requiring a new browser login.
- **SC-004**: Expired credentials are not honored after a restart — token expiration rules remain enforced.
- **SC-005**: If the persistent storage is unavailable, the server starts successfully with in-memory-only operation within its normal startup time.

## Assumptions

- The server runs as a single instance (Azure App Service with one worker). Multi-instance credential sharing is out of scope.
- The Azure App Service file system (`/home/` on Linux App Service) provides durable storage that survives restarts and deployments.
- Pending OAuth flows and authorization codes are inherently short-lived (seconds to minutes) and do not need to be persisted.
- The existing token expiration and revocation logic will continue to apply to persisted credentials.
- Credential data at rest does not require encryption beyond file system permissions, since the App Service environment is already access-controlled. Encryption at rest may be added later as an enhancement.
