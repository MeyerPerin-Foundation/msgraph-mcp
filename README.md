# msgraph-mcp

A hosted [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that wraps the Microsoft Graph API, giving AI assistants secure access to Microsoft 365 consumer services (Outlook.com, OneDrive, Microsoft To Do, etc.).

## Why

MCP lets AI models call external tools through a standard protocol. This project exposes Microsoft Graph endpoints as MCP tools so that any MCP-compatible client can read and manage a user's mail, calendar, files, tasks, and more — without needing to know the Graph API directly.

## Key Design Goals

- **Consumer-focused** — targets Microsoft personal accounts (MSA), not Entra ID / work accounts.
- **Hostable** — runs as a standalone service (FastMCP + Gunicorn/Uvicorn) deployed to Azure App Service.
- **Secure by default** — uses OAuth 2.0 authorization code flow with PKCE; tokens are never exposed to the AI client.
- **Thin wrapper** — maps MCP tool calls to Graph REST calls with minimal transformation, keeping the server easy to maintain as the Graph API evolves.

## Quickstart

```bash
# Install dependencies
uv sync

# Run the server locally
uv run python -m msgraph_mcp.server

# Run tests
uv run pytest
```

## Project Structure

```
msgraph_mcp/
  __init__.py   # Package metadata
  server.py     # MCP server (FastMCP + streamable HTTP + OAuth)
  config.py     # Allowed users and OAuth configuration
  auth.py       # MicrosoftOAuthProvider (MCP OAuth ↔ Microsoft OAuth bridge)
  store.py      # Persistent credential cache (tokens, clients, MSAL cache)
tests/
  conftest.py     # Shared test fixtures
  test_config.py  # Config tests
  test_auth.py    # OAuth provider tests
  test_store.py   # Credential store tests
infra/
  main.bicep    # Azure App Service infrastructure
.github/
  workflows/deploy.yml  # CI/CD pipeline
```

## Authentication

The server uses MCP-native OAuth to authenticate users with Microsoft personal accounts.

### Prerequisites

1. Register an app at [Azure Portal](https://portal.azure.com):
   - Account type: "Personal Microsoft accounts only"
   - Platform: Web
   - Redirect URI: `http://localhost:8000/auth/microsoft/callback`
   - Add Graph delegated permissions: `User.Read`, `Mail.Read`, `Calendars.Read`, `Tasks.ReadWrite`, `Files.Read`

2. Set environment variables:
   ```bash
   export MSGRAPH_CLIENT_ID="your-client-id"
   export MSGRAPH_CLIENT_SECRET="your-client-secret"
   ```

3. Copilot CLI auto-discovers auth via `/.well-known/oauth-protected-resource` — no special config needed.

## Credential Persistence

The server persists MCP tokens, client registrations, and the MSAL token cache to disk so that users do not need to re-authenticate after a server restart.

| Variable | Default | Description |
|---|---|---|
| `MSGRAPH_CACHE_DIR` | `.local/cache` | Directory where credential files are stored. On Azure App Service this is set to `/home/msgraph-mcp-cache` (persistent across restarts). |

Stored files:

- `credentials.json` — MCP registered clients, access tokens, and refresh tokens.
- `msal_cache.json` — Microsoft identity platform token cache.

Both files are written atomically and with restrictive permissions (`0o600`). Expired tokens are automatically filtered out when loaded.

## Deployment

The server is deployed to Azure App Service via GitHub Actions on push to `main`.

- **Infrastructure**: Bicep template in `infra/main.bicep`
- **Live endpoint**: `https://msgraph-mcp.azurewebsites.net/mcp`

## License

TBD
