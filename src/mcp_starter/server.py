"""Create and register the MCP components."""

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from mcp_starter.prompts import register_prompts
from mcp_starter.resources import register_resources
from mcp_starter.tools import register_tools


def create_server() -> FastMCP:
    mcp = FastMCP(
        "Starter MCP Server",
        instructions="Demo server with a greeting tool, an info resource, and a welcome prompt.",
    )
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request):
        return JSONResponse({"status": "ok"})

    return mcp
