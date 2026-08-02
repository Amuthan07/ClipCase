"""Offline eval wrapper around clipcase's existing Gemini calls. Wraps, does not reimplement."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import clipcase  # noqa: E402

from eval.pricing import calculate_cost


class GenerationResult(TypedDict):
    generated_output: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int
    cost_usd: float | None


def generate(frames: list[str], principles: str, api_key: str) -> GenerationResult:
    """Run clipcase's Gemini flow-analysis + test-case generation, timed for the eval benchmark.

    Token usage is accumulated across both API calls (frame analysis + test case generation)
    via clipcase's usage_sink parameter, so it reflects the full pipeline cost for one recording.
    Cost is approximate: Gemini pricing is keyed generically since _pick_gemini_model() may pick
    different sub-models across runs (see eval/pricing.py).
    """
    usage: dict = {}
    start = time.monotonic()
    flow_analysis = clipcase.analyze_with_gemini(frames, principles, api_key, usage_sink=usage)
    test_cases = clipcase.generate_test_cases(
        flow_analysis, principles, "gemini", api_key, usage_sink=usage
    )
    latency_ms = int((time.monotonic() - start) * 1000)

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")

    return GenerationResult(
        generated_output=test_cases,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cost_usd=calculate_cost("gemini", prompt_tokens, completion_tokens),
    )
