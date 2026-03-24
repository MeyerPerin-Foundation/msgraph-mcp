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
  server.py     # MCP server (FastMCP + streamable HTTP transport)
  config.py     # Allowed users configuration
tests/
  test_config.py  # Config tests
infra/
  main.bicep    # Azure App Service infrastructure
.github/
  workflows/deploy.yml  # CI/CD pipeline
```

## Deployment

The server is deployed to Azure App Service via GitHub Actions on push to `main`.

- **Infrastructure**: Bicep template in `infra/main.bicep`
- **Live endpoint**: `https://msgraph-mcp.azurewebsites.net/mcp`

## License

TBD
