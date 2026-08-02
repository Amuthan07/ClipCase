"""Approximate per-model USD pricing, used only to estimate cost_usd for the eval benchmark.

Rates are per 1M tokens (input, output), publicly listed at time of writing. Providers change
pricing without notice - verify against current pricing pages before trusting these for real
budgeting decisions. Gemini's rate is keyed generically since _pick_gemini_model() may select
different sub-models across runs and analyze/generate don't currently report back which one ran.
"""

from __future__ import annotations

USD_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude": (3.00, 15.00),     # Claude Sonnet 4 (input, output)
    "gpt-4o": (2.50, 10.00),     # GPT-4o (input, output)
    "gemini": (0.30, 2.50),      # Gemini Flash tier, approximate (input, output)
}


def calculate_cost(model: str, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    """Return estimated USD cost, or None if tokens or a pricing entry aren't available."""
    if prompt_tokens is None or completion_tokens is None:
        return None
    rates = USD_PER_MILLION_TOKENS.get(model)
    if rates is None:
        return None
    input_rate, output_rate = rates
    return (prompt_tokens / 1_000_000) * input_rate + (completion_tokens / 1_000_000) * output_rate
