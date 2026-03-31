# msgraph-mcp Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-31

## Active Technologies
- Python 3.13 + mcp 1.26.0, msal 1.35.1, Pydantic v2, Starlette (001-persistent-credentials)
- JSON files on local file system (Azure `/home/` durable mount) (001-persistent-credentials)
- Python 3.13 + mcp 1.26.0, httpx, Pydantic v2, Starlette (002-todo-crud)
- N/A (all data lives in Microsoft Graph) (002-todo-crud)
- Python 3.13 + FastMCP, httpx, msal (004-calendar-wrapper)
- N/A (stateless wrapper; tokens managed by existing auth system) (004-calendar-wrapper)

- Python 3.13 + FastMCP, Starlette, MSAL, httpx (main)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.13: Follow standard conventions

## Recent Changes
- 004-calendar-wrapper: Added Python 3.13 + FastMCP, httpx, msal
- 003-email-tools: Added Python 3.13 + mcp 1.26.0, httpx, Pydantic v2, Starlette
- 002-todo-crud: Added Python 3.13 + mcp 1.26.0, httpx, Pydantic v2, Starlette


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
