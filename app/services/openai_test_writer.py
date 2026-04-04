from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

from app.core.config import DEFAULT_OPENAI_MODEL, OPENAI_REASONING_EFFORT
from app.models.schemas import ModuleSummary


class OpenAITestWriter:
    def __init__(self) -> None:
        self.model = DEFAULT_OPENAI_MODEL
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def provider_name(self) -> str:
        return "openai" if self.enabled else "heuristic"

    def generate_module_test(self, module: ModuleSummary, mode: str, repo_path: Path) -> str | None:
        if not self._client:
            return None

        source_path = Path(module.file_path)
        source = source_path.read_text(encoding="utf-8")
        if len(source) > 20_000:
            return None

        if module.language == "python":
            return self._generate_python_test(module, mode, source)
        return self._generate_script_test(module, mode, source, repo_path)

    def _generate_python_test(self, module: ModuleSummary, mode: str, source: str) -> str | None:
        inferred_cases = [
            {
                "function_name": function.name,
                "cases": [case.model_dump() for case in function.inferred_cases],
            }
            for function in module.functions
            if function.inferred_cases
        ]

        instructions = (
            "You write compact, runnable pytest modules for Python codebases. "
            "Return only the full Python file content. "
            "Do not use markdown fences. "
            "Prefer deterministic assertions over mocks. "
            "Do not invent APIs that are not visible in the source."
        )
        prompt = (
            f"Module import path: {module.module_import}\n"
            f"Generation mode: {mode}\n"
            f"Known inferred cases: {json.dumps(inferred_cases)}\n\n"
            "Write a pytest file that:\n"
            "- imports the module with importlib\n"
            "- verifies module import works\n"
            "- verifies public functions exist\n"
            "- uses deterministic assertions when the source clearly supports them\n"
            "- in balanced mode, may call zero-argument functions if safe\n\n"
            f"Source code:\n{source}"
        )
        return self._run_prompt(instructions, prompt)

    def _generate_script_test(self, module: ModuleSummary, mode: str, source: str, repo_path: Path) -> str | None:
        relative_path = Path(module.file_path).resolve().relative_to(repo_path.resolve()).as_posix()
        functions = [function.name for function in module.functions]
        extension_hint = ".test.ts" if module.language == "typescript" else ".test.cjs"

        instructions = (
            "You write compact, runnable test files for JavaScript and TypeScript codebases. "
            "Return only the full test file content. "
            "Do not use markdown fences. "
            "Use Node's built-in test primitives. "
            "Do not invent APIs that are not visible in the source."
        )
        prompt = (
            f"Module relative path: {relative_path}\n"
            f"Module language: {module.language}\n"
            f"Generation mode: {mode}\n"
            f"Discovered functions: {json.dumps(functions)}\n"
            f"Target test file extension: {extension_hint}\n\n"
            "Write a test file that:\n"
            "- loads the module from its absolute file path\n"
            "- verifies the module loads successfully\n"
            "- verifies discovered functions exist when present\n"
            "- in balanced mode, may call zero-argument functions if clearly safe\n"
            "- stays compatible with Node execution\n\n"
            f"Source code:\n{source}"
        )
        return self._run_prompt(instructions, prompt)

    def _run_prompt(self, instructions: str, prompt: str) -> str | None:
        try:
            # Use standard chat completions with reasoning parameters
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "developer", "content": instructions},
                    {"role": "user", "content": prompt}
                ],
                reasoning_effort=OPENAI_REASONING_EFFORT if self.model == "gpt-5-mini" else None,
                max_completion_tokens=4000
            )
            text = response.choices[0].message.content.strip()
        except Exception as e:
            # Fallback for models that might not support 'developer' role yet or other issues
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": instructions},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=4000
                )
                text = response.choices[0].message.content.strip()
            except Exception as e2:
                print(f"OpenAI generation failed: {e2}")
                return None

        if not text:
            return None
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if "```" in text:
                text = text.rsplit("```", 1)[0]
        return text.strip() + "\n"
