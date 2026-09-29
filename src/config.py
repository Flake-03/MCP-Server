"""Validated runtime configuration."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed configuration for the MCP process."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = Field("127.0.0.1", validation_alias="MCP_HOST")
    port: int = Field(8000, ge=1, le=65535, validation_alias="MCP_PORT")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    projects_root: Path = Field(Path("/projects"), validation_alias="PROJECTS_ROOT")
    docs_repository_url: str = Field(
        "https://github.com/Flake-03/Project-Document.git",
        validation_alias="DOCS_REPOSITORY_URL",
    )
    docs_repository_dir: Path = Field(
        Path("/data/git/project-document"), validation_alias="DOCS_REPOSITORY_DIR"
    )
    docs_base_branch: str = Field("main", validation_alias="DOCS_BASE_BRANCH")
    github_token: str = Field("", validation_alias="GITHUB_TOKEN")
    git_author_name: str = Field("Project Docs Bot", validation_alias="GIT_AUTHOR_NAME")
    git_author_email: str = Field(
        "project-docs-bot@example.invalid", validation_alias="GIT_AUTHOR_EMAIL"
    )
    max_project_files: int = Field(
        2_000, ge=1, le=20_000, validation_alias="MAX_PROJECT_FILES"
    )
    max_file_bytes: int = Field(
        512_000, ge=1_024, le=5_000_000, validation_alias="MAX_FILE_BYTES"
    )
    max_search_matches: int = Field(
        50, ge=1, le=200, validation_alias="MAX_SEARCH_MATCHES"
    )
    max_publish_files: int = Field(8, ge=1, le=50, validation_alias="MAX_PUBLISH_FILES")
    max_publish_bytes: int = Field(
        250_000, ge=1_024, le=2_000_000, validation_alias="MAX_PUBLISH_BYTES"
    )

    @field_validator("docs_repository_url")
    @classmethod
    def validate_repository_url(cls, value: str) -> str:
        normalized = value.removesuffix("/")
        if not normalized.startswith("https://github.com/") or not normalized.endswith(
            ".git"
        ):
            raise ValueError(
                "DOCS_REPOSITORY_URL must be an HTTPS github.com URL ending in .git"
            )
        return normalized

    @field_validator("docs_base_branch")
    @classmethod
    def validate_branch(cls, value: str) -> str:
        if (
            not value
            or value.startswith("-")
            or any(part in value for part in ("..", " ", "~", "^", ":"))
        ):
            raise ValueError("DOCS_BASE_BRANCH is not a safe Git branch name")
        return value
