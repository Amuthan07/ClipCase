"""clipcase — convert screen recording videos into structured test cases.

Re-exports the core module's public API at package level so `import clipcase;
clipcase.analyze_with_anthropic(...)` keeps working exactly as it did when this was a single
flat clipcase.py file - both for external code and this repo's own eval/production tooling.
"""

from clipcase.core import (
    DEFAULT_FPS,
    FRAME_SAMPLE_INTERVAL,
    MAX_FRAMES_PER_BATCH,
    SUPPORTED_IMAGE_EXTS,
    SUPPORTED_VIDEO_EXTS,
    analyze_with_anthropic,
    analyze_with_gemini,
    analyze_with_openai,
    check_ffmpeg,
    encode_image_base64,
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
from clipcase.cli import main

__all__ = [
    "DEFAULT_FPS",
    "FRAME_SAMPLE_INTERVAL",
    "MAX_FRAMES_PER_BATCH",
    "SUPPORTED_IMAGE_EXTS",
    "SUPPORTED_VIDEO_EXTS",
    "analyze_with_anthropic",
    "analyze_with_gemini",
    "analyze_with_openai",
    "check_ffmpeg",
    "encode_image_base64",
    "export_csv",
    "export_markdown",
    "export_xlsx",
    "extract_frames",
    "generate_test_cases",
    "get_sampled_frames",
    "get_video_info",
    "load_env",
    "main",
    "parse_confidence_score",
    "parse_markdown_table",
    "resolve_video_path",
]
