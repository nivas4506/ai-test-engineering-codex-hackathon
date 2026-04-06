from pathlib import Path

import pytest

from app.services.repository_analyzer import RepositoryAnalyzer


@pytest.mark.unit
def test_repository_analyzer_builds_dependency_map_and_api_endpoints(tmp_path: Path) -> None:
    repository = tmp_path / "api-repo"
    repository.mkdir()
    (repository / "helpers.py").write_text(
        "def build_message(name: str) -> str:\n"
        "    return f'hello {name}'\n",
        encoding="utf-8",
    )
    (repository / "main.py").write_text(
        "from fastapi import APIRouter\n"
        "from helpers import build_message\n\n"
        "router = APIRouter()\n\n"
        "@router.get('/hello')\n"
        "def hello():\n"
        "    return {'message': build_message('world')}\n",
        encoding="utf-8",
    )

    analysis = RepositoryAnalyzer().analyze(str(repository))

    assert analysis.summary.total_modules == 2
    assert analysis.summary.total_functions == 2
    assert analysis.summary.total_api_endpoints == 1
    assert any(link.source_module == "main" and link.target_module == "helpers" for link in analysis.dependency_map)
    assert analysis.api_endpoints[0].method == "GET"
    assert analysis.api_endpoints[0].path == "/hello"
    assert analysis.api_endpoints[0].handler == "hello"
