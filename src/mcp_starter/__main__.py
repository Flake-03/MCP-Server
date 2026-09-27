"""Start the MCP server with Streamable HTTP."""

import uvicorn

from mcp_starter.config import get_host, get_port


if __name__ == "__main__":
    uvicorn.run("mcp_starter.app:app", host=get_host(), port=get_port())
