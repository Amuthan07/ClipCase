"""CLI entrypoint for the Phase 1 offline eval benchmark: one recording, all configured models."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import clipcase  # noqa: E402

from eval.orchestrator import run_benchmark
from eval.store import connect, init_db

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = str(REPO_ROOT / "db" / "eval.db")
DEFAULT_PRINCIPLES_PATH = REPO_ROOT / "test_case_creation_principles.md"

MODEL_ENV_VARS = {
    "claude": "ANTHROPIC_API_KEY",
    "gpt-4o": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def _load_api_keys() -> dict[str, str]:
    clipcase.load_env()
    return {
        model: os.environ[env_var]
        for model, env_var in MODEL_ENV_VARS.items()
        if os.environ.get(env_var)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline eval benchmark against one recording.")
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument("--fps", type=int, default=clipcase.DEFAULT_FPS)
    parser.add_argument("--sample-interval", type=int, default=clipcase.FRAME_SAMPLE_INTERVAL)
    parser.add_argument("--frames-dir", default="frames")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    if not clipcase.check_ffmpeg():
        print("ERROR: ffmpeg not found on PATH.")
        sys.exit(1)

    video_path = clipcase.resolve_video_path(args.video)
    if not video_path:
        print(f"ERROR: could not resolve video path: {args.video}")
        sys.exit(1)

    principles = DEFAULT_PRINCIPLES_PATH.read_text() if DEFAULT_PRINCIPLES_PATH.exists() else ""

    print(f"Extracting frames from {video_path} (fps={args.fps})...")
    frame_count = clipcase.extract_frames(video_path, args.frames_dir, args.fps)
    if frame_count == 0:
        print("ERROR: no frames extracted.")
        sys.exit(1)
    print(f"  {frame_count} frames extracted.")

    sampled = clipcase.get_sampled_frames(args.frames_dir, args.sample_interval)
    print(f"  Sampled {len(sampled)} frames (every {args.sample_interval}th).")

    api_keys = _load_api_keys()
    if not api_keys:
        print("ERROR: no API keys found. Set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY in .env.")
        sys.exit(1)
    print(f"Running benchmark with: {', '.join(sorted(api_keys))}\n")

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        init_db(str(db_path))
    conn = connect(str(db_path))

    try:
        generations = asyncio.run(
            run_benchmark(
                conn,
                source_path=video_path,
                frames=sampled,
                principles=principles,
                api_keys=api_keys,
            )
        )
    finally:
        conn.close()

    print(f"\n{'Model':<10}{'Latency (ms)':<14}{'Prompt tok':<12}{'Completion tok':<16}{'Cost (USD)':<10}")
    for g in generations:
        cost = f"{g.cost_usd:.4f}" if g.cost_usd is not None else "-"
        print(
            f"{g.model:<10}{g.latency_ms or '-':<14}{g.prompt_tokens or '-':<12}"
            f"{g.completion_tokens or '-':<16}{cost:<10}"
        )
    print(f"\nResults written to {db_path}")


if __name__ == "__main__":
    main()
