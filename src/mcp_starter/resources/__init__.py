"""MCP resources: data clients can read."""

from fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:
    @mcp.resource("info://server")
    def server_info() -> str:
        """Basic information about this MCP server."""
        return "Starter MCP Server: ví dụ FastMCP qua HTTP."
