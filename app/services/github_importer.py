from __future__ import annotations

import re
from dataclasses import dataclass

import requests

from app.utils.files import save_uploaded_input


GITHUB_REPOSITORY_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE,
)


@dataclass
class GithubImportResult:
    upload_id: str
    repository_path: str
    original_filename: str


class GithubRepositoryImporter:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("Accept", "application/vnd.github+json")
        self.session.headers.setdefault("User-Agent", "ai-test-engineering")

    def import_repository(self, repository_url: str) -> GithubImportResult:
        owner, repo = self._parse_repository_url(repository_url)
        default_branch = self._resolve_default_branch(owner, repo)
        archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{default_branch}"
        response = self.session.get(archive_url, timeout=30)
        response.raise_for_status()

        original_filename = f"{repo}-{default_branch}.zip"
        upload_id, repository_path = save_uploaded_input(original_filename, response.content)
        return GithubImportResult(
            upload_id=upload_id,
            repository_path=str(repository_path),
            original_filename=original_filename,
        )

    def _parse_repository_url(self, repository_url: str) -> tuple[str, str]:
        match = GITHUB_REPOSITORY_PATTERN.match(repository_url.strip())
        if not match:
            raise ValueError("Enter a valid public GitHub repository URL.")
        return match.group("owner"), match.group("repo")

    def _resolve_default_branch(self, owner: str, repo: str) -> str:
        metadata_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = self.session.get(metadata_url, timeout=15)
        if response.status_code == 404:
            raise ValueError("GitHub repository not found or not publicly accessible.")
        response.raise_for_status()
        payload = response.json()
        return payload.get("default_branch") or "main"
