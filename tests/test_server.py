"""Smoke tests for the MCP contract and HTTP health route."""

import asyncio

import httpx
from fastmcp import Client

from mcp_starter.app import app
from mcp_starter.server import create_server


def test_mcp_components() -> None:
    async def check() -> None:
        async with Client(create_server()) as client:
            assert {tool.name for tool in await client.list_tools()} == {"greet"}
            assert {str(resource.uri) for resource in await client.list_resources()} == {
                "info://server"
            }
            assert {prompt.name for prompt in await client.list_prompts()} == {"welcome"}
            result = await client.call_tool("greet", {"name": "An"})
            assert result.data == "Xin chào, An!"

    asyncio.run(check())


def test_http_health() -> None:
    async def check() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    asyncio.run(check())
