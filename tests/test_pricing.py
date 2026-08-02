from eval.pricing import calculate_cost


def test_known_model_computes_cost():
    cost = calculate_cost("gpt-4o", prompt_tokens=1_000_000, completion_tokens=0)
    assert cost == 2.50


def test_combines_input_and_output_rates():
    cost = calculate_cost("claude", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == 3.00 + 15.00


def test_unknown_model_returns_none():
    assert calculate_cost("mystery-model", prompt_tokens=100, completion_tokens=100) is None


def test_missing_tokens_returns_none():
    assert calculate_cost("gpt-4o", prompt_tokens=None, completion_tokens=100) is None
    assert calculate_cost("gpt-4o", prompt_tokens=100, completion_tokens=None) is None
