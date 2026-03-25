"""MCP server with Microsoft OAuth authentication."""

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from msgraph_mcp.auth import MicrosoftOAuthProvider
from msgraph_mcp.config import MSGRAPH_CLIENT_ID, MSGRAPH_SERVER_URL

# Initialize the OAuth provider
auth_provider = MicrosoftOAuthProvider()

# Configure FastMCP with MCP-native OAuth (only if client ID is set)
mcp_kwargs: dict = {"name": "msgraph-mcp", "host": "0.0.0.0", "port": 8000}

if MSGRAPH_CLIENT_ID:
    mcp_kwargs["auth"] = AuthSettings(
        issuer_url=AnyHttpUrl(MSGRAPH_SERVER_URL),
        resource_server_url=AnyHttpUrl(MSGRAPH_SERVER_URL),
        required_scopes=["mcp:tools"],
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["mcp:tools"],
        ),
    )
    mcp_kwargs["auth_server_provider"] = auth_provider

mcp = FastMCP(**mcp_kwargs)


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the message sent by the user."""
    return f"Echo: {message}"


async def health(request: Request) -> JSONResponse:
    """Health check endpoint for Azure warmup probe."""
    return JSONResponse({"status": "ok"})


# Register custom routes before building the ASGI app
mcp._custom_starlette_routes.append(Route("/", health))
if MSGRAPH_CLIENT_ID:
    mcp._custom_starlette_routes.append(
        Route("/auth/microsoft/callback", auth_provider.handle_microsoft_callback)
    )

# ASGI app for deployment (streamable HTTP transport)
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
