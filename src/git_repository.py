"""Managed Git checkout and pull-request publication."""

import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from filelock import FileLock

from config import Settings
from github import GitHubClient, GitHubRepository
from models import DocumentChange, PublishResult, SearchMatch
from paths import (
    resolve_within,
    resolve_write_within,
    safe_document_path,
    validate_project_id,
)


class ManagedDocsRepository:
    """Own a disposable checkout whose writes always end in a pull request."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._root = settings.docs_repository_dir
        self._lock = FileLock(f"{self._root}.lock", timeout=120)
        repository = GitHubRepository.from_clone_url(settings.docs_repository_url)
        self._github = GitHubClient(settings.github_token, repository)

    def publish(
        self,
        project_id: str,
        title: str,
        body: str,
        changes: list[DocumentChange],
    ) -> PublishResult:
        """Commit complete Markdown replacements, push a branch, and open a PR."""
        validate_project_id(project_id)
        self._validate_publish(title, body, changes)
        with self._lock:
            self._ensure_checkout()
            self._require_base_branch()
            branch = self._new_branch(project_id)
            self._git(
                "switch",
                "--force-create",
                branch,
                f"origin/{self._settings.docs_base_branch}",
            )
            changed_paths: list[str] = []
            for change in changes:
                relative = safe_document_path(project_id, change.path)
                destination = resolve_write_within(self._root, relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(change.content.rstrip() + "\n", encoding="utf-8")
                changed_paths.append(relative.as_posix())
            self._git("add", "--", f"projects/{project_id}")
            if not self._git_has_staged_changes():
                raise ValueError(
                    "documentation content is unchanged from the base branch"
                )
            self._git("commit", "-m", title)
            commit = self._git("rev-parse", "HEAD").stdout.strip()
            self._git("push", "--set-upstream", "origin", branch)
            pr_url = self._github.create_pull_request(
                title=title,
                body=body,
                head=branch,
                base=self._settings.docs_base_branch,
            )
            return PublishResult(
                branch=branch,
                commit=commit,
                pull_request_url=pr_url,
                changed_files=sorted(changed_paths),
            )

    def read_document(self, project_id: str, path: str) -> str:
        """Read one Markdown file from the latest fetched base branch."""
        with self._lock:
            self._sync_base()
            relative = safe_document_path(project_id, path)
            candidate = resolve_within(self._root, relative.as_posix())
            if not candidate.is_file() or candidate.is_symlink():
                raise ValueError("document does not exist")
            if candidate.stat().st_size > self._settings.max_file_bytes:
                raise ValueError("document exceeds MAX_FILE_BYTES")
            return candidate.read_text(encoding="utf-8")

    def search_documents(
        self, query: str, project_id: str | None, limit: int
    ) -> list[SearchMatch]:
        """Search Markdown documents on the latest fetched base branch."""
        needle = query.strip().casefold()
        if not needle or len(needle) > 200:
            raise ValueError("query must contain 1 to 200 non-whitespace characters")
        with self._lock:
            self._sync_base()
            search_root = self._root / "projects"
            if project_id is not None:
                validate_project_id(project_id)
                search_root = search_root / project_id
            if not search_root.exists():
                return []
            matches: list[SearchMatch] = []
            for path in sorted(search_root.rglob("*.md")):
                if path.is_symlink() or not path.is_file():
                    continue
                if path.stat().st_size > self._settings.max_file_bytes:
                    continue
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1
                ):
                    if needle in line.casefold():
                        matches.append(
                            SearchMatch(
                                path=path.relative_to(self._root).as_posix(),
                                line=line_number,
                                text=line[:500],
                            )
                        )
                        if len(matches) >= limit:
                            return matches
            return matches

    def ready(self) -> bool:
        """Report whether local roots and Git are available without network I/O."""
        return (
            bool(self._settings.github_token)
            and self._settings.projects_root.is_dir()
            and self._git_available()
        )

    def _sync_base(self) -> None:
        self._ensure_checkout()
        self._require_base_branch()
        self._git("switch", "--detach", f"origin/{self._settings.docs_base_branch}")

    def _ensure_checkout(self) -> None:
        if (self._root / ".git").is_dir():
            self._git("fetch", "--prune", "origin")
            return
        if self._root.exists() and any(self._root.iterdir()):
            raise RuntimeError(f"managed repository path is not empty: {self._root}")
        self._root.parent.mkdir(parents=True, exist_ok=True)
        self._run_git(
            "clone",
            self._settings.docs_repository_url,
            str(self._root),
            cwd=self._root.parent,
        )

    def _require_base_branch(self) -> None:
        result = self._git(
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/remotes/origin/{self._settings.docs_base_branch}",
            check=False,
        )
        if result.returncode == 0:
            return
        raise RuntimeError(
            f"documentation repository has no {self._settings.docs_base_branch!r} base branch; "
            "create its initial commit on GitHub before publishing documentation"
        )

    def _validate_publish(
        self, title: str, body: str, changes: list[DocumentChange]
    ) -> None:
        if not title.strip() or len(title) > 120:
            raise ValueError("title must contain 1 to 120 characters")
        if len(body) > 10_000:
            raise ValueError("pull request body exceeds 10,000 characters")
        if not changes or len(changes) > self._settings.max_publish_files:
            raise ValueError(
                f"changes must contain 1 to {self._settings.max_publish_files} files"
            )
        if (
            sum(len(change.content.encode("utf-8")) for change in changes)
            > self._settings.max_publish_bytes
        ):
            raise ValueError("documentation changes exceed MAX_PUBLISH_BYTES")
        paths = [change.path for change in changes]
        if len(set(paths)) != len(paths):
            raise ValueError("changes contain duplicate document paths")

    def _new_branch(self, project_id: str) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        safe_id = re.sub(r"[^a-zA-Z0-9._-]", "-", project_id)
        return f"docs/{safe_id}/{timestamp}-{uuid4().hex[:8]}"

    def _git_has_staged_changes(self) -> bool:
        result = self._git("diff", "--cached", "--quiet", check=False)
        if result.returncode not in {0, 1}:
            raise RuntimeError("git failed while checking staged documentation changes")
        return result.returncode == 1

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._run_git(*args, cwd=self._root, check=check)

    def _run_git(
        self, *args: str, cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": self._settings.git_author_name,
                "GIT_AUTHOR_EMAIL": self._settings.git_author_email,
                "GIT_COMMITTER_NAME": self._settings.git_author_name,
                "GIT_COMMITTER_EMAIL": self._settings.git_author_email,
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        if self._settings.github_token:
            env["GIT_ASKPASS"] = str(Path(__file__).with_name("git_askpass.sh"))
            env["GITHUB_TOKEN"] = self._settings.github_token
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            check=check,
            capture_output=True,
            text=True,
            timeout=120,
        )

    @staticmethod
    def _git_available() -> bool:
        try:
            subprocess.run(
                ["git", "--version"], check=True, capture_output=True, timeout=5
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return True
