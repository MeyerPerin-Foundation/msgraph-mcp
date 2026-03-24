"""Minimal MCP server that echoes user input."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("msgraph-mcp")


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the message sent by the user."""
    return f"Echo: {message}"


if __name__ == "__main__":
    mcp.run()
