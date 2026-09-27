"""MCP prompts: reusable messages clients can request."""

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt
    def welcome(name: str) -> str:
        """Create a short greeting prompt for a person."""
        return f"Hãy chào {name} bằng một câu thân thiện bằng tiếng Việt."
