"""ASGI entry point for Uvicorn."""

from mcp_starter.server import create_server


mcp = create_server()
app = mcp.http_app(stateless_http=True)
