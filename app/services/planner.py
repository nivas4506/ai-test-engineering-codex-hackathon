from __future__ import annotations

from app.models.schemas import AnalysisResult, PlanResult, PlannedModule


class PlannerService:
    def create_plan(self, analysis: AnalysisResult) -> PlanResult:
        planned_modules = []
        for module in analysis.modules:
            function_count = len(module.functions)
            if function_count >= 3:
                priority = "high"
            elif function_count >= 1:
                priority = "medium"
            else:
                priority = "low"

            strategy = ["import smoke test"]
            if function_count:
                strategy.append("callable existence test")
            if any(fn.arg_count == 0 for fn in module.functions):
                strategy.append("zero-argument execution smoke test")
            if module.language in {"javascript", "typescript"}:
                strategy.append("node-compatible module load test")
            if module.language == "generic":
                strategy = [
                    "source file existence test",
                    "readability smoke test",
                    "non-empty file assertion",
                ]

            planned_modules.append(
                PlannedModule(
                    module_import=module.module_import,
                    file_path=module.file_path,
                    priority=priority,
                    strategy=strategy,
                    rationale=(
                        f"{module.language.title()} module exposes {function_count} public top-level functions."
                        if module.language != "generic"
                        else "Generic source file is validated through smoke tests without changing the codebase."
                    ),
                )
            )

        language_summary = ", ".join(language.title() for language in analysis.detected_languages) or "Unknown"
        summary = f"Planned {len(planned_modules)} modules for generated test coverage across {language_summary} sources."
        return PlanResult(modules=planned_modules, summary=summary)
