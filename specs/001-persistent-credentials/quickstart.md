# Quickstart: Persistent Credential Cache

**Feature**: 001-persistent-credentials

## What This Feature Does

After this feature is implemented, the MCP server will remember authenticated users and registered clients across server restarts and Azure App Service deployments. Users will no longer need to re-authenticate through the browser every time the server is updated.

## How It Works

1. When a client registers or a user authenticates, the server saves credential data to a JSON file on the Azure App Service's durable `/home/` file system.
2. When the server starts up, it loads any previously saved credentials from disk.
3. Expired tokens are automatically discarded during loading.
4. If the credential files are missing or corrupt, the server starts normally with empty state (graceful degradation).

## Configuration

Set the cache directory via environment variable (optional — the default works for Azure App Service):

```
MSGRAPH_CACHE_DIR=/home/msgraph-mcp-cache
```

For local development, the default is `.local/cache` relative to the working directory.

## Verifying It Works

1. Authenticate with the MCP server through Copilot CLI (browser login).
2. Confirm the echo tool works: the server should respond to tool calls.
3. Restart the server (or trigger a deployment).
4. Try the echo tool again — it should work without re-authentication.

## Limitations

- Only works for single-instance deployments. If the server is scaled to multiple instances, each has its own independent credential cache.
- In-flight OAuth flows (browser redirects in progress) are lost on restart — the user would need to retry the login if the server restarts mid-auth-flow.
- The MSAL token cache is eventually consistent with Microsoft's token service — if a Microsoft refresh token has been revoked server-side, `acquire_token_silent()` may fail on the next call even though the cache was restored.
