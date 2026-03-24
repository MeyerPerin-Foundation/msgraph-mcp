"""Minimal MCP server that echoes user input."""

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("msgraph-mcp", host="0.0.0.0", port=8000)


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the message sent by the user."""
    return f"Echo: {message}"


async def health(request: Request) -> JSONResponse:
    """Health check endpoint for Azure warmup probe."""
    return JSONResponse({"status": "ok"})


# Add health route so Azure warmup probe on / succeeds
mcp._custom_starlette_routes.append(Route("/", health))

# ASGI app for deployment (streamable HTTP transport)
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
