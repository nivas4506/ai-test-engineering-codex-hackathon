from __future__ import annotations

import ast
import re
from pathlib import Path

from app.models.schemas import (
    AnalysisResult,
    ApiEndpoint,
    CodebaseSummary,
    DependencyLink,
    FunctionCase,
    ModuleFunction,
    ModuleSummary,
)
from app.utils.files import ALLOWED_CODE_SUFFIXES, is_supported_project_file


class RepositoryAnalyzer:
    PYTHON_SUFFIXES = {".py"}
    JAVASCRIPT_SUFFIXES = {".js", ".cjs", ".mjs", ".jsx"}
    TYPESCRIPT_SUFFIXES = {".ts", ".tsx"}
    GENERIC_SUFFIXES = ALLOWED_CODE_SUFFIXES - PYTHON_SUFFIXES - JAVASCRIPT_SUFFIXES - TYPESCRIPT_SUFFIXES

    def analyze(self, repository_path: str) -> AnalysisResult:
        repo_path = Path(repository_path).resolve()
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        if repo_path.is_file():
            if not self._is_supported_source(repo_path):
                raise ValueError(
                    "No supported source code or project files were found. Upload source files or standard project manifests."
                )
            modules = [self._summarize_file(repo_path.parent, repo_path)]
        else:
            modules = [
                self._summarize_file(repo_path, file_path)
                for file_path in sorted(repo_path.rglob("*"))
                if file_path.is_file() and self._is_supported_source(file_path) and not self._should_skip(file_path)
            ]

        python_files = [module.file_path for module in modules if module.language == "python"]
        javascript_files = [module.file_path for module in modules if module.language == "javascript"]
        typescript_files = [module.file_path for module in modules if module.language == "typescript"]
        generic_files = [module.file_path for module in modules if module.language == "generic"]

        detected_languages = []
        if python_files:
            detected_languages.append("python")
        if javascript_files:
            detected_languages.append("javascript")
        if typescript_files:
            detected_languages.append("typescript")
        if generic_files:
            detected_languages.append("generic")

        if not modules:
            raise ValueError(
                "No supported source code or project files were found. Upload source files or standard project manifests."
            )

        dependency_map = self._build_dependency_map(modules)
        api_endpoints = self._build_api_endpoints(modules)
        summary = CodebaseSummary(
            total_files=len({module.file_path for module in modules}),
            total_modules=len(modules),
            total_functions=sum(len(module.functions) for module in modules),
            total_classes=sum(len(module.class_names) for module in modules),
            total_api_endpoints=len(api_endpoints),
            detected_languages=detected_languages,
        )

        return AnalysisResult(
            repository_path=str(repo_path),
            python_files=python_files,
            javascript_files=javascript_files,
            typescript_files=typescript_files,
            generic_files=generic_files,
            detected_languages=detected_languages,
            modules=modules,
            dependency_map=dependency_map,
            api_endpoints=api_endpoints,
            summary=summary,
        )

    def _summarize_file(self, repo_path: Path, file_path: Path) -> ModuleSummary:
        suffix = file_path.suffix.lower()
        if suffix in self.PYTHON_SUFFIXES:
            return self._summarize_python_module(repo_path, file_path)
        if suffix in self.TYPESCRIPT_SUFFIXES:
            return self._summarize_script_module(repo_path, file_path, "typescript")
        if suffix in self.JAVASCRIPT_SUFFIXES:
            return self._summarize_script_module(repo_path, file_path, "javascript")
        return self._summarize_generic_module(repo_path, file_path)

    def _summarize_python_module(self, repo_path: Path, file_path: Path) -> ModuleSummary:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = []
        classes = []
        imports = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                required_arg_count = len(node.args.args) - len(node.args.defaults)
                functions.append(
                    ModuleFunction(
                        name=node.name,
                        line_number=node.lineno,
                        arg_count=len(node.args.args),
                        required_arg_count=required_arg_count,
                        parameter_names=[arg.arg for arg in node.args.args],
                        has_defaults=bool(node.args.defaults),
                        inferred_cases=self._infer_python_cases(node),
                    )
                )
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        relative = file_path.relative_to(repo_path)
        module_import = ".".join(relative.with_suffix("").parts)
        return ModuleSummary(
            file_path=str(file_path),
            module_import=module_import,
            language="python",
            functions=functions,
            class_names=classes,
            imports=imports,
        )

    def _summarize_script_module(self, repo_path: Path, file_path: Path, language: str) -> ModuleSummary:
        source = file_path.read_text(encoding="utf-8")
        functions = self._extract_script_functions(source)
        classes = self._extract_script_classes(source)
        imports = self._extract_script_imports(source)
        relative = file_path.relative_to(repo_path).as_posix()
        return ModuleSummary(
            file_path=str(file_path),
            module_import=relative,
            language=language,
            functions=functions,
            class_names=classes,
            imports=imports,
        )

    def _summarize_generic_module(self, repo_path: Path, file_path: Path) -> ModuleSummary:
        relative = file_path.relative_to(repo_path).as_posix()
        return ModuleSummary(
            file_path=str(file_path),
            module_import=relative,
            language="generic",
            functions=[],
            class_names=[],
            imports=[],
        )

    def _extract_script_functions(self, source: str) -> list[ModuleFunction]:
        functions: list[ModuleFunction] = []
        seen_names: set[str] = set()
        patterns = [
            re.compile(r"export\s+function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\((?P<args>[^)]*)\)", re.MULTILINE),
            re.compile(r"function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\((?P<args>[^)]*)\)", re.MULTILINE),
            re.compile(
                r"(?:export\s+)?const\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*\((?P<args>[^)]*)\)\s*=>",
                re.MULTILINE,
            ),
            re.compile(
                r"(?:export\s+)?const\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?P<single>[A-Za-z_$][\w$]*)\s*=>",
                re.MULTILINE,
            ),
        ]

        for pattern in patterns:
            for match in pattern.finditer(source):
                name = match.group("name")
                if name.startswith("_") or name in seen_names:
                    continue
                args_text = match.groupdict().get("args")
                single_arg = match.groupdict().get("single")
                parameter_names = self._parse_script_parameters(args_text, single_arg)
                functions.append(
                    ModuleFunction(
                        name=name,
                        line_number=source[: match.start()].count("\n") + 1,
                        arg_count=len(parameter_names),
                        required_arg_count=len(parameter_names),
                        parameter_names=parameter_names,
                        has_defaults=False,
                        inferred_cases=[],
                    )
                )
                seen_names.add(name)

        return functions

    def _parse_script_parameters(self, args_text: str | None, single_arg: str | None) -> list[str]:
        if single_arg:
            return [single_arg]
        if not args_text:
            return []
        names = []
        for part in args_text.split(","):
            cleaned = part.strip()
            if not cleaned:
                continue
            cleaned = cleaned.split("=", 1)[0].strip()
            cleaned = cleaned.lstrip("...").strip()
            cleaned = cleaned.split(":", 1)[0].strip()
            if cleaned and re.match(r"^[A-Za-z_$][\w$]*$", cleaned):
                names.append(cleaned)
        return names

    def _extract_script_classes(self, source: str) -> list[str]:
        return [match.group("name") for match in re.finditer(r"\bclass\s+(?P<name>[A-Za-z_$][\w$]*)", source)]

    def _extract_script_imports(self, source: str) -> list[str]:
        imports: list[str] = []
        patterns = [
            re.compile(r"import\s+(?:.+?\s+from\s+)?['\"](?P<path>[^'\"]+)['\"]"),
            re.compile(r"require\(\s*['\"](?P<path>[^'\"]+)['\"]\s*\)"),
        ]
        for pattern in patterns:
            imports.extend(match.group("path") for match in pattern.finditer(source))
        return imports

    def _build_dependency_map(self, modules: list[ModuleSummary]) -> list[DependencyLink]:
        module_names = {module.module_import for module in modules}
        dependencies: list[DependencyLink] = []
        seen_links: set[tuple[str, str]] = set()
        for module in modules:
            for imported in module.imports:
                target = self._resolve_local_import(imported, module_names)
                if not target:
                    continue
                link = (module.module_import, target)
                if link in seen_links:
                    continue
                seen_links.add(link)
                dependencies.append(
                    DependencyLink(
                        source_module=module.module_import,
                        target_module=target,
                        relation="imports",
                    )
                )
        return dependencies

    def _resolve_local_import(self, imported: str, module_names: set[str]) -> str | None:
        normalized = imported.replace("/", ".").replace("\\", ".")
        if normalized in module_names:
            return normalized
        for candidate in module_names:
            if candidate.startswith(f"{normalized}.") or normalized.startswith(f"{candidate}."):
                return candidate
        return None

    def _build_api_endpoints(self, modules: list[ModuleSummary]) -> list[ApiEndpoint]:
        endpoints: list[ApiEndpoint] = []
        for module in modules:
            if module.language != "python":
                continue
            endpoints.extend(self._extract_python_endpoints(module))
        return endpoints

    def _extract_python_endpoints(self, module: ModuleSummary) -> list[ApiEndpoint]:
        file_path = Path(module.file_path)
        source = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        router_names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id in {"FastAPI", "APIRouter"}:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            router_names.add(target.id)

        endpoints: list[ApiEndpoint] = []
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not isinstance(decorator.func, ast.Attribute):
                    continue
                if not isinstance(decorator.func.value, ast.Name):
                    continue
                if decorator.func.value.id not in router_names:
                    continue
                method = decorator.func.attr.upper()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
                    continue
                path = "/"
                if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                    path = decorator.args[0].value
                endpoints.append(
                    ApiEndpoint(
                        method=method,
                        path=path,
                        handler=node.name,
                        file_path=module.file_path,
                        line_number=node.lineno,
                    )
                )
        return endpoints

    def _is_supported_source(self, file_path: Path) -> bool:
        return is_supported_project_file(file_path)

    def _should_skip(self, file_path: Path) -> bool:
        parts = set(file_path.parts)
        if any(part in parts for part in {"venv", ".venv", "__pycache__", "generated_tests", "node_modules"}):
            return True
        filename = file_path.name.lower()
        return any(token in filename for token in (".test.", ".spec.", ".d.ts"))

    def _infer_python_cases(self, node: ast.FunctionDef) -> list[FunctionCase]:
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
            return []

        expression = node.body[0].value
        if expression is None:
            return []

        constant_case = self._constant_case(expression)
        if constant_case:
            return [constant_case]

        string_case = self._joined_string_case(node, expression)
        if string_case:
            return [string_case]

        binary_case = self._binary_case(node, expression)
        if binary_case:
            return [binary_case]

        return []

    def _constant_case(self, expression: ast.AST) -> FunctionCase | None:
        if isinstance(expression, ast.Constant):
            return FunctionCase(description="returns constant value", arguments=[], expected_expression=repr(expression.value))
        return None

    def _joined_string_case(self, node: ast.FunctionDef, expression: ast.AST) -> FunctionCase | None:
        if not isinstance(expression, ast.JoinedStr):
            return None
        parts: list[str] = []
        arguments: list[str] = []
        default_map = self._default_argument_map(node)
        for value in expression.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name):
                parameter_name = value.value.id
                if parameter_name in default_map:
                    parts.append(str(default_map[parameter_name]))
                else:
                    sample = f"sample_{parameter_name}"
                    arguments.append(repr(sample))
                    parts.append(sample)
            else:
                return None
        return FunctionCase(
            description="formats string output",
            arguments=arguments,
            expected_expression=repr("".join(parts)),
        )

    def _binary_case(self, node: ast.FunctionDef, expression: ast.AST) -> FunctionCase | None:
        if not isinstance(expression, ast.BinOp):
            return None
        if not isinstance(expression.left, ast.Name) or not isinstance(expression.right, ast.Name):
            return None

        left_name = expression.left.id
        right_name = expression.right.id
        operands = {left_name: 2, right_name: 3}
        if isinstance(expression.op, ast.Add):
            expected = operands[left_name] + operands[right_name]
        elif isinstance(expression.op, ast.Sub):
            expected = operands[left_name] - operands[right_name]
        elif isinstance(expression.op, ast.Mult):
            expected = operands[left_name] * operands[right_name]
        else:
            return None

        return FunctionCase(
            description="computes arithmetic return value",
            arguments=[repr(operands[name]) for name in self._ordered_case_arguments(node, [left_name, right_name])],
            expected_expression=repr(expected),
        )

    def _default_argument_map(self, node: ast.FunctionDef) -> dict[str, object]:
        arg_names = [arg.arg for arg in node.args.args]
        defaults = node.args.defaults
        if not defaults:
            return {}
        paired_names = arg_names[-len(defaults) :]
        mapping: dict[str, object] = {}
        for name, default in zip(paired_names, defaults):
            if isinstance(default, ast.Constant):
                mapping[name] = default.value
        return mapping

    def _ordered_case_arguments(self, node: ast.FunctionDef, names: list[str]) -> list[str]:
        return [arg.arg for arg in node.args.args if arg.arg in names]
