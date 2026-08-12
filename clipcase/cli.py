"""clipcase.cli — the `clipcase` command: video -> AI analysis -> exported test cases."""

import argparse
import os
import sys

from clipcase.core import (
    DEFAULT_FPS,
    FRAME_SAMPLE_INTERVAL,
    MAX_FRAMES_PER_BATCH,
    analyze_with_anthropic,
    analyze_with_gemini,
    analyze_with_openai,
    check_ffmpeg,
    export_csv,
    export_markdown,
    export_xlsx,
    extract_frames,
    generate_test_cases,
    get_sampled_frames,
    get_video_info,
    load_env,
    parse_confidence_score,
    parse_markdown_table,
    resolve_video_path,
)


def main():
    parser = argparse.ArgumentParser(
        description="Clipcase — Convert screen recording videos into structured test cases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  clipcase recording.mov
  clipcase recording.mov --fps 2 --provider anthropic
  clipcase recording.mov --fps 1 --provider openai --output my_tests
  clipcase recording.mov --frames-only
        """,
    )
    parser.add_argument("video", help="Path to the video file (.mov, .mp4, .webm)")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS, help=f"Frames per second to extract (default: {DEFAULT_FPS})")
    parser.add_argument("--provider", choices=["anthropic", "openai", "gemini"], default="anthropic", help="LLM provider (default: anthropic)")
    parser.add_argument("--output", default=None, help="Output file base name (default: derived from video name)")
    parser.add_argument("--output-dir", default="output", help="Directory for generated test case files (default: output)")
    parser.add_argument("--frames-dir", default="frames", help="Directory to store extracted frames (default: frames)")
    parser.add_argument("--frames-only", action="store_true", help="Only extract frames, skip AI analysis")
    parser.add_argument("--sample-interval", type=int, default=FRAME_SAMPLE_INTERVAL, help=f"Sample every Nth frame for analysis (default: {FRAME_SAMPLE_INTERVAL})")
    parser.add_argument("--principles", default=None, help="Path to test case principles file (default: test_case_creation_principles.md)")

    args = parser.parse_args()

    # Load env vars
    load_env()

    print("=" * 60)
    print("  Clipcase — Video to Test Case Generator")
    print("=" * 60)

    # Step 1: Check ffmpeg
    print("\n[1/5] Checking ffmpeg...")
    if not check_ffmpeg():
        print("  ERROR: ffmpeg is not installed.")
        print("  Install it:")
        print("    macOS:   brew install ffmpeg")
        print("    Ubuntu:  sudo apt install ffmpeg")
        print("    Windows: choco install ffmpeg")
        sys.exit(1)
    print("  ✅ ffmpeg found")

    # Step 2: Resolve video file
    print("\n[2/5] Locating video file...")
    video_path = resolve_video_path(args.video)
    if not video_path:
        print(f"  ERROR: Video file not found: {args.video}")
        print("  Tip: macOS screen recordings may have hidden Unicode characters in filenames.")
        print("  Try using a glob pattern or renaming the file.")
        sys.exit(1)

    video_name = os.path.basename(video_path)
    print(f"  ✅ Found: {video_name}")

    # Get video info
    info = get_video_info(video_path)
    if info and "format" in info:
        duration = float(info["format"].get("duration", 0))
        mins, secs = divmod(int(duration), 60)
        print(f"  Duration: {mins}m {secs}s")
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                print(f"  Resolution: {stream.get('width')}x{stream.get('height')}")
                break

    # Step 3: Extract frames
    print(f"\n[3/5] Extracting frames at {args.fps} fps...")
    frames_dir = os.path.join(os.path.dirname(video_path), args.frames_dir)
    frame_count = extract_frames(video_path, frames_dir, args.fps)
    if frame_count == 0:
        print("  ERROR: No frames extracted. Check video file.")
        sys.exit(1)
    print(f"  ✅ {frame_count} frames extracted to {frames_dir}/")

    if args.frames_only:
        print("\n  Done (--frames-only mode). Frames saved for manual review.")
        return

    # Step 4: Analyze frames with LLM
    print(f"\n[4/5] Analyzing frames with {args.provider}...")

    # Check API key
    if args.provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("  ERROR: ANTHROPIC_API_KEY not set.")
            print("  Set it: export ANTHROPIC_API_KEY=sk-ant-...")
            print("  Or add to .env file: ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)
    elif args.provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("  ERROR: OPENAI_API_KEY not set.")
            print("  Set it: export OPENAI_API_KEY=sk-...")
            print("  Or add to .env file: OPENAI_API_KEY=sk-...")
            sys.exit(1)
    elif args.provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("  ERROR: GEMINI_API_KEY not set.")
            print("  Set it: export GEMINI_API_KEY=AIza...")
            print("  Or add to .env file: GEMINI_API_KEY=AIza...")
            print("  Get a free key at: https://aistudio.google.com/app/apikey")
            sys.exit(1)

    # Load principles
    principles = ""
    principles_path = args.principles
    if not principles_path:
        # Look for default principles file
        default_path = os.path.join(os.path.dirname(video_path), "test_case_creation_principles.md")
        if os.path.exists(default_path):
            principles_path = default_path

    if principles_path and os.path.exists(principles_path):
        with open(principles_path) as f:
            principles = f.read()
        print(f"  Loaded principles: {os.path.basename(principles_path)}")
    else:
        print("  No principles file found (optional). Using default prompts.")

    # Sample frames
    sampled = get_sampled_frames(frames_dir, args.sample_interval)
    print(f"  Sampled {len(sampled)} frames (every {args.sample_interval}th frame)")

    # Send frames in batches for analysis
    all_analyses = []
    for batch_start in range(0, len(sampled), MAX_FRAMES_PER_BATCH):
        batch = sampled[batch_start:batch_start + MAX_FRAMES_PER_BATCH]
        batch_num = batch_start // MAX_FRAMES_PER_BATCH + 1
        total_batches = (len(sampled) + MAX_FRAMES_PER_BATCH - 1) // MAX_FRAMES_PER_BATCH
        print(f"  Analyzing batch {batch_num}/{total_batches} ({len(batch)} frames)...")

        if args.provider == "anthropic":
            analysis = analyze_with_anthropic(batch, principles, api_key)
        elif args.provider == "openai":
            analysis = analyze_with_openai(batch, principles, api_key)
        else:
            analysis = analyze_with_gemini(batch, principles, api_key)
        all_analyses.append(analysis)

    flow_analysis = "\n\n---\n\n".join(all_analyses)
    print(f"  ✅ Flow analysis complete")

    # Step 5: Generate test cases
    print(f"\n[5/5] Generating test cases...")
    raw_output = generate_test_cases(
        flow_analysis, principles, args.provider, api_key, request_confidence=True
    )
    test_case_md, confidence_score = parse_confidence_score(raw_output)
    if confidence_score is not None:
        print(f"  Confidence (self-assessed): {confidence_score:.0%}")

    # Parse the generated table
    headers, rows = parse_markdown_table(test_case_md)
    if not rows:
        print("  WARNING: Could not parse test cases from LLM output.")
        print("  Saving raw output for manual review...")
        fallback_dir = os.path.join(os.getcwd(), args.output_dir)
        os.makedirs(fallback_dir, exist_ok=True)
        raw_path = os.path.join(
            fallback_dir,
            (args.output or "test_cases") + "_raw.md",
        )
        with open(raw_path, "w") as f:
            f.write(test_case_md)
        print(f"  Saved raw output: {raw_path}")
        return

    print(f"  ✅ Generated {len(rows)} test cases")

    # Export
    base_name = args.output or os.path.splitext(video_name)[0].replace(" ", "_") + "_test_cases"
    output_dir = os.path.join(os.getcwd(), args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, f"{base_name}.md")
    csv_path = os.path.join(output_dir, f"{base_name}.csv")
    xlsx_path = os.path.join(output_dir, f"{base_name}.xlsx")

    print(f"\n  Exporting...")
    export_markdown(headers, rows, md_path, video_name, flow_analysis, confidence_score)
    export_csv(headers, rows, csv_path)
    export_xlsx(headers, rows, xlsx_path)

    # Summary
    smoke = sum(1 for r in rows if r.get("Smoke") == "☑")
    regression = sum(1 for r in rows if r.get("Regression") == "☑")
    e2e = sum(1 for r in rows if r.get("E2E") == "☑")

    print(f"\n{'=' * 60}")
    print(f"  DONE — {len(rows)} test cases generated")
    print(f"  Smoke: {smoke} | Regression: {regression} | E2E: {e2e}")
    if confidence_score is not None:
        print(f"  Confidence: {confidence_score:.0%}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
