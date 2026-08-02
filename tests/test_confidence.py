import clipcase
from production.confidence import generate_with_confidence


def test_generate_with_confidence_requests_confidence_flag(monkeypatch):
    received = {}

    def fake_analyze(frames, principles, api_key, usage_sink=None):
        if usage_sink is not None:
            usage_sink["prompt_tokens"] = 500
            usage_sink["completion_tokens"] = 100
        return "flow analysis"

    def fake_generate_test_cases(flow, principles, provider, api_key, usage_sink=None, request_confidence=False):
        received["provider"] = provider
        received["request_confidence"] = request_confidence
        if usage_sink is not None:
            usage_sink["prompt_tokens"] = usage_sink.get("prompt_tokens", 0) + 1000
            usage_sink["completion_tokens"] = usage_sink.get("completion_tokens", 0) + 2000
        return "| TC | ... |\n\nCONFIDENCE_SCORE: 0.9"

    monkeypatch.setattr(clipcase, "analyze_with_gemini", fake_analyze)
    monkeypatch.setattr(clipcase, "generate_test_cases", fake_generate_test_cases)

    result = generate_with_confidence(["f.png"], "principles", "key", model="gemini")

    assert received["provider"] == "gemini"
    assert received["request_confidence"] is True
    assert result["confidence_score"] == 0.9
    assert result["test_case_doc"] == "| TC | ... |"
    assert result["prompt_tokens"] == 1500
    assert result["completion_tokens"] == 2100
    assert result["model"] == "gemini"


def test_unknown_model_raises():
    import pytest

    with pytest.raises(ValueError):
        generate_with_confidence(["f.png"], "principles", "key", model="not-a-model")
