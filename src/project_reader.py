"""Bounded, read-only access to configured source projects."""

import fnmatch
from pathlib import Path

from models import FileEntry, SearchMatch
from paths import (
    IGNORED_NAMES,
    IGNORED_PARTS,
    resolve_within,
    validate_project_id,
)


class ProjectReader:
    """Read text files below direct children of one configured root."""

    def __init__(
        self, root: Path, max_files: int, max_file_bytes: int, max_matches: int
    ) -> None:
        self._root = root
        self._max_files = max_files
        self._max_file_bytes = max_file_bytes
        self._max_matches = max_matches

    def project_root(self, project_id: str) -> Path:
        """Resolve an existing project directory by its safe identifier."""
        validate_project_id(project_id)
        project = resolve_within(self._root, project_id)
        if not project.is_dir():
            raise ValueError(f"project_id {project_id!r} is not a directory")
        return project

    def list_files(self, project_id: str, pattern: str = "**/*") -> list[FileEntry]:
        """Return sorted file metadata up to the configured project limit."""
        project = self.project_root(project_id)
        entries: list[FileEntry] = []
        for candidate in sorted(project.rglob("*")):
            relative = candidate.relative_to(project)
            if (
                self._ignored(relative)
                or not candidate.is_file()
                or candidate.is_symlink()
            ):
                continue
            if pattern not in {"*", "**/*"} and not fnmatch.fnmatch(
                relative.as_posix(), pattern
            ):
                continue
            size = candidate.stat().st_size
            if size <= self._max_file_bytes and not self._is_binary(candidate):
                entries.append(FileEntry(path=relative.as_posix(), size_bytes=size))
            if len(entries) >= self._max_files:
                break
        return entries

    def read_file(
        self, project_id: str, path: str, start_line: int, end_line: int
    ) -> str:
        """Read an inclusive line range from one bounded UTF-8 text file."""
        if start_line < 1 or end_line < start_line or end_line - start_line > 499:
            raise ValueError("line range must contain 1 to 500 lines")
        project = self.project_root(project_id)
        candidate = resolve_within(project, path)
        relative = candidate.relative_to(project)
        if self._ignored(relative) or not candidate.is_file() or candidate.is_symlink():
            raise ValueError("file is not readable")
        if candidate.stat().st_size > self._max_file_bytes:
            raise ValueError("file exceeds MAX_FILE_BYTES")
        if self._is_binary(candidate):
            raise ValueError("file is not valid UTF-8 text")
        text = candidate.read_text(encoding="utf-8")
        lines = text.splitlines()
        selected = lines[start_line - 1 : end_line]
        return "\n".join(
            f"{number}: {line}"
            for number, line in enumerate(selected, start=start_line)
        )

    def search(
        self, project_id: str, query: str, pattern: str = "**/*"
    ) -> list[SearchMatch]:
        """Perform case-insensitive literal search across bounded text files."""
        needle = query.strip().casefold()
        if not needle or len(needle) > 200:
            raise ValueError("query must contain 1 to 200 non-whitespace characters")
        project = self.project_root(project_id)
        matches: list[SearchMatch] = []
        for entry in self.list_files(project_id, pattern):
            text = resolve_within(project, entry.path).read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if needle in line.casefold():
                    matches.append(
                        SearchMatch(path=entry.path, line=line_number, text=line[:500])
                    )
                    if len(matches) >= self._max_matches:
                        return matches
        return matches

    @staticmethod
    def _ignored(relative: Path) -> bool:
        return relative.name in IGNORED_NAMES or any(
            part in IGNORED_PARTS or part.startswith(".env") for part in relative.parts
        )

    @staticmethod
    def _is_binary(path: Path) -> bool:
        try:
            sample = path.read_bytes()[:8_192]
            if b"\0" in sample:
                return True
            sample.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            return True
        return False
