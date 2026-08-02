"""Production request path: single default model, one call, self-reported confidence.

No fan-out, no ground truth - see design principle "Single benchmarked-best model in
production" in clipcaseArchitecturePipeline.md. "Compare across models" stays an explicit,
user-triggered opt-in via eval/run_benchmark.py, never this default path.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import clipcase  # noqa: E402

from eval.pricing import calculate_cost
from eval.store import ProductionRequest, connect, init_db, insert_production_request

# Provisional: Gemini is the only model with real Phase 1 benchmark data right now (Anthropic
# and OpenAI runs are blocked on account billing). Revisit once a full 3-way comparison exists -
# this default is "the only one we could measure", not "the one we proved is best".
DEFAULT_MODEL = "gemini"

_ANALYZE_FN_NAMES = {
    "claude": ("analyze_with_anthropic", "anthropic"),
    "gpt-4o": ("analyze_with_openai", "openai"),
    "gemini": ("analyze_with_gemini", "gemini"),
}


class ConfidenceResult(TypedDict):
    test_case_doc: str
    confidence_score: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int
    cost_usd: float | None
    model: str


def generate_with_confidence(
    frames: list[str], principles: str, api_key: str, model: str = DEFAULT_MODEL
) -> ConfidenceResult:
    if model not in _ANALYZE_FN_NAMES:
        raise ValueError(f"Unknown production model: {model!r}. Expected one of {list(_ANALYZE_FN_NAMES)}")
    analyze_fn_name, provider = _ANALYZE_FN_NAMES[model]
    analyze_fn = getattr(clipcase, analyze_fn_name)

    usage: dict = {}
    start = time.monotonic()
    flow_analysis = analyze_fn(frames, principles, api_key, usage_sink=usage)
    raw_output = clipcase.generate_test_cases(
        flow_analysis, principles, provider, api_key, usage_sink=usage, request_confidence=True
    )
    latency_ms = int((time.monotonic() - start) * 1000)

    test_case_doc, confidence_score = clipcase.parse_confidence_score(raw_output)
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")

    return ConfidenceResult(
        test_case_doc=test_case_doc,
        confidence_score=confidence_score,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cost_usd=calculate_cost(model, prompt_tokens, completion_tokens),
        model=model,
    )


def _load_api_key(model: str) -> str | None:
    import os

    clipcase.load_env()
    env_var = {"claude": "ANTHROPIC_API_KEY", "gpt-4o": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}[model]
    return os.environ.get(env_var)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the production confidence path against one recording.")
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(_ANALYZE_FN_NAMES))
    parser.add_argument("--fps", type=int, default=clipcase.DEFAULT_FPS)
    parser.add_argument("--sample-interval", type=int, default=clipcase.FRAME_SAMPLE_INTERVAL)
    parser.add_argument("--frames-dir", default="frames")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parent.parent / "db" / "eval.db"))
    args = parser.parse_args()

    if not clipcase.check_ffmpeg():
        print("ERROR: ffmpeg not found on PATH.")
        sys.exit(1)

    video_path = clipcase.resolve_video_path(args.video)
    if not video_path:
        print(f"ERROR: could not resolve video path: {args.video}")
        sys.exit(1)

    principles_path = Path(__file__).resolve().parent.parent / "test_case_creation_principles.md"
    principles = principles_path.read_text() if principles_path.exists() else ""

    print(f"Extracting frames from {video_path} (fps={args.fps})...")
    frame_count = clipcase.extract_frames(video_path, args.frames_dir, args.fps)
    if frame_count == 0:
        print("ERROR: no frames extracted.")
        sys.exit(1)
    sampled = clipcase.get_sampled_frames(args.frames_dir, args.sample_interval)
    print(f"  Sampled {len(sampled)} frames.")

    api_key = _load_api_key(args.model)
    if not api_key:
        print(f"ERROR: no API key found for model {args.model!r}.")
        sys.exit(1)

    print(f"Running production path with model={args.model} (single call, no fan-out)...")
    result = generate_with_confidence(sampled, principles, api_key, model=args.model)

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        init_db(str(db_path))
    conn = connect(str(db_path))
    try:
        insert_production_request(
            conn,
            ProductionRequest(
                id=str(uuid.uuid4()),
                model=result["model"],
                confidence_score=result["confidence_score"],
                latency_ms=result["latency_ms"],
                cost_usd=result["cost_usd"],
            ),
        )
    finally:
        conn.close()

    print(f"\nConfidence: {result['confidence_score']}")
    print(f"Latency: {result['latency_ms']}ms  Cost: ${result['cost_usd']}")
    print(f"\n{result['test_case_doc'][:500]}...\n")
    print(f"Logged to {db_path}")


if __name__ == "__main__":
    main()
