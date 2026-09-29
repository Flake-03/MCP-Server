"""Path and identifier validation at filesystem boundaries."""

import re
from pathlib import Path

PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
IGNORED_PARTS = frozenset(
    {
        ".git",
        ".idea",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "lib",
        "node_modules",
        "target",
        "vendor",
    }
)
IGNORED_NAMES = frozenset({".env", ".env.local", ".env.production"})


def validate_project_id(project_id: str) -> str:
    """Return a safe project identifier or raise a user-facing error."""
    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("project_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return project_id


def resolve_within(root: Path, relative_path: str) -> Path:
    """Resolve an existing relative path without permitting any symlink hop."""
    candidate_input = Path(relative_path)
    if candidate_input.is_absolute() or ".." in candidate_input.parts:
        raise ValueError("path must be relative and may not contain '..'")
    try:
        resolved_root = root.resolve(strict=True)
        cursor = resolved_root
        for part in candidate_input.parts:
            cursor /= part
            if cursor.is_symlink():
                raise ValueError("symlink paths are not allowed")
        candidate = cursor.resolve(strict=True)
    except FileNotFoundError as error:
        raise ValueError("path does not exist") from error
    if not candidate.is_relative_to(resolved_root):
        raise ValueError("path resolves outside the configured root")
    return candidate


def resolve_write_within(root: Path, relative_path: Path) -> Path:
    """Resolve a possibly new destination while rejecting symlink components."""
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("path must be relative and may not contain '..'")
    resolved_root = root.resolve(strict=True)
    cursor = resolved_root
    for part in relative_path.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("symlink paths are not allowed")
    if not cursor.resolve(strict=False).is_relative_to(resolved_root):
        raise ValueError("path resolves outside the configured root")
    return cursor


def safe_document_path(project_id: str, relative_path: str) -> Path:
    """Build a repository-relative Markdown path for one project."""
    validate_project_id(project_id)
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".md":
        raise ValueError("document path must be a relative .md path without '..'")
    if any(part.startswith(".") for part in path.parts):
        raise ValueError("hidden document paths are not allowed")
    return Path("projects") / project_id / path
