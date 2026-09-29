"""FastMCP server construction and tool registration."""

import asyncio

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from config import Settings
from git_repository import ManagedDocsRepository
from models import (
    DocumentChange,
    FileEntry,
    PublishResult,
    SearchMatch,
)
from project_reader import ProjectReader


def create_server(settings: Settings) -> FastMCP:
    """Create the stateless project-documentation MCP server."""
    projects = ProjectReader(
        settings.projects_root,
        settings.max_project_files,
        settings.max_file_bytes,
        settings.max_search_matches,
    )
    documents = ManagedDocsRepository(settings)
    mcp = FastMCP(
        "Project Documentation",
        instructions=(
            "Use project tools to inspect source code and document tools to read or update reviewed documentation. "
            "publish_documents always creates a Git branch and pull request; it never merges."
        ),
    )

    @mcp.tool
    async def list_project_files(
        project_id: str, pattern: str = "**/*"
    ) -> list[FileEntry]:
        """List readable text files in a configured project; pattern is a glob such as `**/*.py`."""
        return await asyncio.to_thread(projects.list_files, project_id, pattern)

    @mcp.tool
    async def read_project_file(
        project_id: str, path: str, start_line: int = 1, end_line: int = 400
    ) -> str:
        """Read at most 500 numbered lines from one project-relative text file."""
        return await asyncio.to_thread(
            projects.read_file, project_id, path, start_line, end_line
        )

    @mcp.tool
    async def search_project_text(
        project_id: str, query: str, pattern: str = "**/*"
    ) -> list[SearchMatch]:
        """Find a literal string in bounded project text files."""
        return await asyncio.to_thread(
            projects.search, project_id, query, pattern
        )

    @mcp.tool
    async def search_documents(
        query: str, project_id: str | None = None
    ) -> list[SearchMatch]:
        """Search merged Markdown documentation, optionally within one project."""
        return await asyncio.to_thread(
            documents.search_documents, query, project_id, settings.max_search_matches
        )

    @mcp.tool
    async def read_document(project_id: str, path: str) -> str:
        """Read one merged Markdown document below `projects/<project_id>/`."""
        return await asyncio.to_thread(documents.read_document, project_id, path)

    @mcp.tool
    async def publish_documents(
        project_id: str,
        title: str,
        body: str,
        changes: list[DocumentChange],
    ) -> PublishResult:
        """Replace project Markdown files, push a unique branch, and open a pull request."""
        return await asyncio.to_thread(
            documents.publish, project_id, title, body, changes
        )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/ready", methods=["GET"])
    async def ready(_request) -> JSONResponse:
        is_ready = documents.ready()
        return JSONResponse(
            {"status": "ready" if is_ready else "not-ready"},
            status_code=200 if is_ready else 503,
        )

    return mcp
