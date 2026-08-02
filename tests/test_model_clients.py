import clipcase
from eval.models import claude_client, gemini_client, gpt4o_client

CASES = [
    (claude_client, "analyze_with_anthropic", "claude"),
    (gpt4o_client, "analyze_with_openai", "gpt-4o"),
    (gemini_client, "analyze_with_gemini", "gemini"),
]


def _fake_analyze(prompt_tokens, completion_tokens):
    def analyze(frames, principles, api_key, usage_sink=None):
        if usage_sink is not None:
            usage_sink["prompt_tokens"] = usage_sink.get("prompt_tokens", 0) + prompt_tokens
            usage_sink["completion_tokens"] = usage_sink.get("completion_tokens", 0) + completion_tokens
        return "flow analysis"

    return analyze


def _fake_generate_test_cases(prompt_tokens, completion_tokens):
    def generate_test_cases(flow, principles, provider, api_key, usage_sink=None):
        if usage_sink is not None:
            usage_sink["prompt_tokens"] = usage_sink.get("prompt_tokens", 0) + prompt_tokens
            usage_sink["completion_tokens"] = usage_sink.get("completion_tokens", 0) + completion_tokens
        return "| TC | ... |"

    return generate_test_cases


def test_each_client_calls_its_own_analyze_function(monkeypatch):
    for client, analyze_fn_name, model_key in CASES:
        monkeypatch.setattr(clipcase, analyze_fn_name, _fake_analyze(100, 50))
        monkeypatch.setattr(clipcase, "generate_test_cases", _fake_generate_test_cases(200, 300))

        result = client.generate(["frame_0001.png"], "principles text", "fake-key")

        assert result["generated_output"] == "| TC | ... |"
        assert result["latency_ms"] >= 0


def test_tokens_accumulate_across_both_calls(monkeypatch):
    monkeypatch.setattr(clipcase, "analyze_with_anthropic", _fake_analyze(100, 50))
    monkeypatch.setattr(clipcase, "generate_test_cases", _fake_generate_test_cases(200, 300))

    result = claude_client.generate(["f.png"], "principles", "key")

    assert result["prompt_tokens"] == 300
    assert result["completion_tokens"] == 350


def test_cost_is_computed_from_real_tokens(monkeypatch):
    monkeypatch.setattr(clipcase, "analyze_with_anthropic", _fake_analyze(1_000_000, 0))
    monkeypatch.setattr(clipcase, "generate_test_cases", _fake_generate_test_cases(0, 0))

    result = claude_client.generate(["f.png"], "principles", "key")

    # 1M prompt tokens at claude's $3.00/1M input rate
    assert result["cost_usd"] == 3.00


def test_no_usage_reported_means_no_cost(monkeypatch):
    def analyze_without_usage(frames, principles, api_key, usage_sink=None):
        return "flow analysis"

    def generate_without_usage(flow, principles, provider, api_key, usage_sink=None):
        return "| TC | ... |"

    monkeypatch.setattr(clipcase, "analyze_with_anthropic", analyze_without_usage)
    monkeypatch.setattr(clipcase, "generate_test_cases", generate_without_usage)

    result = claude_client.generate(["f.png"], "principles", "key")

    assert result["prompt_tokens"] is None
    assert result["cost_usd"] is None


def test_generate_test_cases_receives_correct_provider(monkeypatch):
    received = {}

    def fake_generate_test_cases(flow, principles, provider, api_key, usage_sink=None):
        received["provider"] = provider
        return "doc"

    monkeypatch.setattr(clipcase, "analyze_with_anthropic", _fake_analyze(10, 10))
    monkeypatch.setattr(clipcase, "generate_test_cases", fake_generate_test_cases)

    claude_client.generate(["f.png"], "principles", "key")

    assert received["provider"] == "anthropic"
