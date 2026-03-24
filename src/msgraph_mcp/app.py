"""FastAPI application for msgraph-mcp."""

from fastapi import FastAPI

app = FastAPI(
    title="msgraph-mcp",
    version="0.1.0",
    description="Microsoft Graph MCP integration",
)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
