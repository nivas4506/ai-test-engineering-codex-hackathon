import time

import pytest

from app.services.openai_test_writer import FAST_AUTOMATION_MODELS, OpenAITestWriter


@pytest.mark.unit
def test_available_models_include_fast_automation_profile() -> None:
    writer = OpenAITestWriter()

    model_ids = [model.id for model in writer.available_models()]

    assert "automation-fast" in model_ids
    assert "gpt-5-mini" in model_ids


@pytest.mark.unit
def test_fast_automation_returns_first_completed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    writer = OpenAITestWriter()
    writer._client = object()

    delays = {
        "gpt-5-mini": 0.03,
        "gpt-5-codex": 0.01,
        "gpt-5.1-codex-mini": 0.02,
    }

    def fake_run_prompt_for_model(selected_model: str, instructions: str, prompt: str) -> str:
        time.sleep(delays[selected_model])
        return f"def test_{selected_model.replace('-', '_')}():\n    assert True\n"

    monkeypatch.setattr(writer, "_run_prompt_for_model", fake_run_prompt_for_model)

    generated = writer._run_fast_automation("instructions", "prompt")

    assert generated is not None
    assert "gpt_5_codex" in generated
    assert set(FAST_AUTOMATION_MODELS) == {"gpt-5-mini", "gpt-5-codex", "gpt-5.1-codex-mini"}
