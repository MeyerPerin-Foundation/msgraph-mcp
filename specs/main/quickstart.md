# Quickstart: MSA OAuth Authentication

## Prerequisites

1. **Azure App Registration**: Register an app at https://portal.azure.com with:
   - Supported account types: "Personal Microsoft accounts only"
   - Platform: Web
   - Redirect URI: `http://localhost:8000/auth/callback`
   - Create a client secret

2. **Environment Variables**:
   ```bash
   export MSGRAPH_CLIENT_ID="your-client-id"
   export MSGRAPH_CLIENT_SECRET="your-client-secret"
   export MSGRAPH_REDIRECT_URI="http://localhost:8000/auth/callback"
   ```

## Run Locally

```bash
# Install dependencies
uv sync

# Start the server
uv run python -m msgraph_mcp.server

# Server runs at http://localhost:8000
```

## Authenticate

1. Open `http://localhost:8000/auth/login` in a browser
2. Sign in with your Microsoft personal account
3. Consent to requested permissions
4. You'll be redirected to `/auth/callback` with confirmation
5. The server can now call Graph API on your behalf

## Verify

```bash
# Check auth status
curl http://localhost:8000/auth/status

# Test echo tool (should work regardless of auth)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hello"}}}'
```

## Deploy to Azure

The GitHub Actions workflow handles deployment automatically on push to `main`.

For Azure App Service, set these app settings:
- `MSGRAPH_CLIENT_ID`
- `MSGRAPH_CLIENT_SECRET`
- `MSGRAPH_REDIRECT_URI` = `https://msgraph-mcp.azurewebsites.net/auth/callback`
