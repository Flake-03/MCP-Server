"""MCP tools: operations clients can call."""

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    def greet(name: str) -> str:
        """Greet a person by name."""
        return f"Xin chào, {name}!"
