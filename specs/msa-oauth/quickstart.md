# Quickstart: MSA OAuth Authentication

## Prerequisites

1. **Azure App Registration**: Register an app at https://portal.azure.com with:
   - Supported account types: "Personal Microsoft accounts only"
   - Platform: Web
   - Redirect URI: `http://localhost:8000/auth/microsoft/callback`
   - Create a client secret
   - Under API permissions, add Microsoft Graph delegated permissions:
     `User.Read`, `Mail.Read`, `Calendars.Read`, `Tasks.ReadWrite`, `Files.Read`

2. **Environment Variables**:
   ```bash
   export MSGRAPH_CLIENT_ID="your-client-id"
   export MSGRAPH_CLIENT_SECRET="your-client-secret"
   export MSGRAPH_REDIRECT_URI="http://localhost:8000/auth/microsoft/callback"
   export MSGRAPH_SERVER_URL="http://localhost:8000"
   ```

## Run Locally

```bash
uv sync
uv run python -m msgraph_mcp.server
```

## Verify Server

```bash
curl http://localhost:8000/
curl http://localhost:8000/.well-known/oauth-protected-resource
```

## Authenticate via Copilot CLI

1. Add to `~/.copilot/mcp-config.json`:
   ```json
   {"mcpServers":{"msgraph-mcp":{"type":"http","url":"http://localhost:8000/mcp"}}}
   ```
2. Restart Copilot CLI
3. Invoke any tool - browser will open for Microsoft sign-in
4. Consent to permissions - tools now work with Graph API access

## Deploy to Azure

Set `MSGRAPH_CLIENT_ID` and `MSGRAPH_CLIENT_SECRET` in Azure Portal app settings.
Bicep sets `MSGRAPH_REDIRECT_URI` and `MSGRAPH_SERVER_URL` automatically.

Update the app registration redirect URI to match the production URL.
