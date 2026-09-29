"""Typed inputs and outputs shared by MCP tools and services."""

from pydantic import BaseModel, Field, field_validator


class FileEntry(BaseModel):
    """Metadata for one readable project file."""

    path: str
    size_bytes: int


class SearchMatch(BaseModel):
    """One bounded literal-search match."""

    path: str
    line: int
    text: str


class DocumentChange(BaseModel):
    """Complete replacement content for one project Markdown document."""

    path: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def markdown_only(cls, value: str) -> str:
        if not value.endswith(".md"):
            raise ValueError("document path must end in .md")
        return value


class PublishResult(BaseModel):
    """Git and GitHub result returned to an agent after publication."""

    branch: str
    commit: str
    pull_request_url: str
    changed_files: list[str]
