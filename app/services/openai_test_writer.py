from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

from app.core.config import DEFAULT_OPENAI_MODEL, OPENAI_REASONING_EFFORT
from app.models.schemas import AvailableModel, ModuleSummary


OPENAI_CODE_MODELS: tuple[AvailableModel, ...] = (
    AvailableModel(
        id="gpt-5-mini",
        label="GPT-5 mini",
        provider="openai",
        category="budget",
        description="Fast and cost-efficient default for routine repository test generation.",
        recommended=True,
    ),
    AvailableModel(
        id="gpt-5",
        label="GPT-5",
        provider="openai",
        category="balanced",
        description="Stronger general reasoning for complex repo analysis and edge-case generation.",
    ),
    AvailableModel(
        id="gpt-5.1",
        label="GPT-5.1",
        provider="openai",
        category="balanced",
        description="High-quality reasoning for harder codebases and more deliberate test planning.",
    ),
    AvailableModel(
        id="gpt-5-codex",
        label="GPT-5 Codex",
        provider="openai",
        category="coding",
        description="Coding-optimized option for generating and repairing test files.",
    ),
    AvailableModel(
        id="gpt-5.1-codex",
        label="GPT-5.1 Codex",
        provider="openai",
        category="coding",
        description="Most capable coding-oriented option in this product for codebase-aware test generation.",
    ),
    AvailableModel(
        id="gpt-5.1-codex-mini",
        label="GPT-5.1 Codex mini",
        provider="openai",
        category="coding",
        description="Lower-cost coding model for smaller repos and faster iteration.",
    ),
)

HEURISTIC_FALLBACK_MODEL = AvailableModel(
    id="heuristic",
    label="Heuristic fallback",
    provider="heuristic",
    category="fallback",
    description="Built-in deterministic generator used when OpenAI is unavailable.",
    recommended=False,
)


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

    def available_models(self) -> list[AvailableModel]:
        models = [
            model.model_copy(update={"available": self.enabled})
            for model in OPENAI_CODE_MODELS
        ]
        return [HEURISTIC_FALLBACK_MODEL, *models]

    def resolve_model(self, model_override: str | None = None) -> str | None:
        if not self.enabled:
            return None

        requested = (model_override or self.model or "").strip()
        if not requested:
            return DEFAULT_OPENAI_MODEL

        supported_ids = {model.id for model in OPENAI_CODE_MODELS}
        return requested if requested in supported_ids else self.model

    def generate_module_test(self, module: ModuleSummary, mode: str, repo_path: Path, model_override: str | None = None) -> str | None:
        if not self._client:
            return None

        source_path = Path(module.file_path)
        source = source_path.read_text(encoding="utf-8")
        if len(source) > 20_000:
            return None

        if module.language == "python":
            return self._generate_python_test(module, mode, source, model_override)
        return self._generate_script_test(module, mode, source, repo_path, model_override)

    def _generate_python_test(self, module: ModuleSummary, mode: str, source: str, model_override: str | None = None) -> str | None:
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
        return self._run_prompt(instructions, prompt, model_override)

    def _generate_script_test(
        self,
        module: ModuleSummary,
        mode: str,
        source: str,
        repo_path: Path,
        model_override: str | None = None,
    ) -> str | None:
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
        return self._run_prompt(instructions, prompt, model_override)

    def _run_prompt(self, instructions: str, prompt: str, model_override: str | None = None) -> str | None:
        selected_model = self.resolve_model(model_override)
        if not selected_model:
            return None
        try:
            response = self._client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "developer", "content": instructions},
                    {"role": "user", "content": prompt}
                ],
                reasoning_effort=OPENAI_REASONING_EFFORT if selected_model.startswith("gpt-5") else None,
                max_completion_tokens=4000
            )
            text = response.choices[0].message.content.strip()
        except Exception as e:
            try:
                response = self._client.chat.completions.create(
                    model=selected_model,
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
