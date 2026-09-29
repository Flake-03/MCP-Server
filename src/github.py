"""Minimal GitHub REST client for opening documentation pull requests."""

from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class GitHubRepository:
    """Owner and repository parsed from a canonical HTTPS clone URL."""

    owner: str
    name: str

    @classmethod
    def from_clone_url(cls, url: str) -> "GitHubRepository":
        """Parse `https://github.com/<owner>/<repo>.git`."""
        path = url.removeprefix("https://github.com/").removesuffix(".git")
        parts = path.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("GitHub repository URL must contain owner and repository")
        return cls(owner=parts[0], name=parts[1])


class GitHubClient:
    """Create pull requests using a fine-grained GitHub token."""

    def __init__(self, token: str, repository: GitHubRepository) -> None:
        self._token = token
        self._repository = repository

    def create_pull_request(self, title: str, body: str, head: str, base: str) -> str:
        """Create a pull request and return its browser URL."""
        if not self._token:
            raise RuntimeError("GITHUB_TOKEN is required to create a pull request")
        response = httpx.post(
            f"https://api.github.com/repos/{self._repository.owner}/{self._repository.name}/pulls",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"title": title, "body": body, "head": head, "base": base},
            timeout=30,
        )
        response.raise_for_status()
        url = response.json().get("html_url")
        if not isinstance(url, str) or not url:
            raise RuntimeError("GitHub pull-request response did not contain html_url")
        return url
