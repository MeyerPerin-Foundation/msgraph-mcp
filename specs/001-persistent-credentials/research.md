# Research: Persistent Credential Cache

**Feature**: 001-persistent-credentials  
**Date**: 2026-03-26

## R1: Storage Backend for Credential Persistence

**Decision**: Use a single JSON file on the local file system via atomic writes.

**Rationale**: The server is a single-instance Azure App Service. The data volume is tiny (a few registered clients, a handful of tokens). A JSON file is simple, requires no additional dependencies, and aligns with the "Thin MCP Wrapper" constitution principle. Azure App Service Linux provides a durable `/home/` mount that survives restarts and deployments.

**Alternatives considered**:
- **SQLite**: More robust concurrency handling, but adds complexity for a single-process, single-user server. Overkill for the expected data volume (< 10 entries total).
- **Redis / Azure Cache**: Adds an external dependency and cost. Violates the "Thin MCP Wrapper" principle for a personal-use server.
- **Azure Blob Storage**: Adds SDK dependency and latency. Not justified for a few kilobytes of credential data.

## R2: MSAL Token Cache Persistence

**Decision**: Use MSAL's built-in `SerializableTokenCache` with `serialize()` / `deserialize()` and persist to a separate JSON file alongside the MCP credential store.

**Rationale**: MSAL's `SerializableTokenCache` was designed for exactly this use case. It has a `has_state_changed` flag to avoid unnecessary writes, and `serialize()` / `deserialize()` produce/consume JSON strings. Keeping the MSAL cache in a separate file avoids coupling its internal format with the MCP credential data model.

**Alternatives considered**:
- **Embed MSAL cache inside the MCP credential file**: Would couple two different serialization formats and make the code harder to maintain.
- **Use MSAL's `PersistedTokenCache` extension**: This is a .NET-only feature, not available in the Python MSAL library.

## R3: File Corruption Protection

**Decision**: Use atomic write pattern — write to a temporary file, then rename (replace) to the target path.

**Rationale**: `os.replace()` is atomic on both Linux and Windows NTFS. If the process crashes mid-write, the temporary file is left behind but the original credential file remains intact. On the next load, the server reads the intact original.

**Alternatives considered**:
- **File locking (fcntl/msvcrt)**: Adds platform-specific code. Not needed for a single-process server.
- **Write-ahead log**: Massive overkill for a file that holds < 10 entries.

## R4: What to Persist vs. What to Leave Ephemeral

**Decision**:
- **Persist**: registered clients, MCP access tokens (with user email), MCP refresh tokens (with user email), MSAL token cache.
- **Do NOT persist**: pending OAuth flows, MCP authorization codes.

**Rationale**: Pending flows contain MSAL flow objects with internal state that cannot be meaningfully serialized and replayed after a restart. Authorization codes are intentionally short-lived (5 minutes) and are consumed once. Both are inherently tied to an in-progress browser interaction that would be broken by a restart anyway.

## R5: Storage Location Configuration

**Decision**: Use environment variable `MSGRAPH_CACHE_DIR` with a sensible default.

**Rationale**: On Azure App Service Linux, `/home/` is the durable mount. Default to `/home/msgraph-mcp-cache/` in production and `.local/cache/` for local development (detected via whether `MSGRAPH_CLIENT_ID` is set and the platform). The env var allows operators to override if needed.

**Alternatives considered**:
- **Hardcoded path**: Inflexible across environments.
- **Same directory as the app code**: Would be wiped by deployments on Azure App Service (only `/home/` survives).

## R6: Serialization Format for MCP Credentials

**Decision**: Use Pydantic's `model_dump()` / `model_validate()` with JSON serialization.

**Rationale**: `OAuthClientInformationFull`, `AccessToken`, and `RefreshToken` are all Pydantic models already. Using Pydantic's native serialization avoids custom serialize/deserialize logic and keeps the code aligned with the existing type system. The `AnyUrl` fields require `mode="json"` in `model_dump()` to produce serializable strings.

**Alternatives considered**:
- **pickle**: Not human-readable, security risk with untrusted data.
- **Custom dict mapping**: Unnecessary when Pydantic handles it natively.

## R7: Graceful Degradation

**Decision**: If the cache file is unreadable (corrupt, missing permissions, parse error), log a warning and continue with empty in-memory state.

**Rationale**: The server must never fail to start because of a cache issue. The cache is a convenience — the user can always re-authenticate. A logged warning makes the issue discoverable without blocking operation.

## R8: Persistence Timing

**Decision**: Write to disk after every state-mutating operation (register, token issue, token revoke) using a debounced/coalesced write.

**Rationale**: Writing after every mutation ensures durability. The write volume is extremely low (a few writes per auth session). A simple "save after mutation" approach is sufficient without batching or debouncing, given the tiny data size (< 10 KB).

**Alternatives considered**:
- **Periodic timer**: Risks losing state if the process crashes between saves.
- **atexit hook**: Not reliable on SIGKILL or Azure App Service forced termination.
