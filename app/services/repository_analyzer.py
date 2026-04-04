from __future__ import annotations

import ast
from pathlib import Path

from app.models.schemas import AnalysisResult, ModuleFunction, ModuleSummary


class RepositoryAnalyzer:
    def analyze(self, repository_path: str) -> AnalysisResult:
        repo_path = Path(repository_path).resolve()
        if not repo_path.exists() or not repo_path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        python_files = []
        modules = []
        for file_path in sorted(repo_path.rglob("*.py")):
            if self._should_skip(file_path):
                continue
            python_files.append(str(file_path))
            modules.append(self._summarize_module(repo_path, file_path))

        return AnalysisResult(
            repository_path=str(repo_path),
            python_files=python_files,
            modules=modules,
        )

    def _summarize_module(self, repo_path: Path, file_path: Path) -> ModuleSummary:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                functions.append(
                    ModuleFunction(
                        name=node.name,
                        line_number=node.lineno,
                        arg_count=len(node.args.args),
                        has_defaults=bool(node.args.defaults),
                    )
                )

        relative = file_path.relative_to(repo_path)
        module_import = ".".join(relative.with_suffix("").parts)
        return ModuleSummary(
            file_path=str(file_path),
            module_import=module_import,
            functions=functions,
        )

    def _should_skip(self, file_path: Path) -> bool:
        parts = set(file_path.parts)
        return any(part in parts for part in {"venv", ".venv", "__pycache__", "generated_tests", "workspace"})
