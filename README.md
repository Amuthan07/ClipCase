# video2testcase

Convert screen recording videos of application usage into structured, comprehensive test cases — automatically.

Drop a `.mov`/`.mp4` video, run one command, and get test cases in **Markdown**, **CSV**, and **Excel** formats.

---

## How It Works

```
Video (.mov/.mp4) ──▶ ffmpeg (frame extraction) ──▶ AI Vision (frame analysis) ──▶ Test Cases (MD/CSV/XLSX)
```

1. **Frame extraction** — Uses `ffmpeg` to extract screenshots from the video at a configurable frame rate.
2. **AI analysis** — Sends sampled frames to a vision-capable LLM (Claude or GPT-4o) to understand the complete user flow.
3. **Test case generation** — The AI generates structured test cases following QA best practices, covering positive, negative, and edge case scenarios.
4. **Export** — Outputs test cases in Markdown, CSV, and styled Excel formats.

---

## Prerequisites

| Dependency | Why | Install |
|------------|-----|---------|
| **Python 3.9+** | Runtime | [python.org](https://python.org) |
| **ffmpeg** | Frame extraction from video | `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Linux) / `choco install ffmpeg` (Windows) |
| **API Key** | AI analysis (Claude or GPT-4o) | See [API Setup](#api-setup) below |

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> video2testcase
cd video2testcase
pip install -r requirements.txt
```

### 2. Set your API key

```bash
cp .env.example .env
# Edit .env and paste your API key
```

Or export directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
# or
export OPENAI_API_KEY=sk-...
```

### 3. Run

```bash
python video2testcase.py your_recording.mov
```

That's it. Your test cases will appear as:
- `your_recording_test_cases.md`
- `your_recording_test_cases.csv`
- `your_recording_test_cases.xlsx`

---

## Usage

```
python video2testcase.py <video_file> [options]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--fps` | `2` | Frames per second to extract |
| `--provider` | `anthropic` | LLM provider: `anthropic` or `openai` |
| `--output` | auto | Base name for output files |
| `--frames-dir` | `frames` | Directory for extracted frames |
| `--frames-only` | off | Only extract frames, skip AI |
| `--sample-interval` | `10` | Use every Nth frame for analysis |
| `--principles` | auto | Path to custom principles file |

### Examples

```bash
# Basic — uses Claude, 2 fps
python video2testcase.py recording.mov

# Use OpenAI GPT-4o instead
python video2testcase.py recording.mov --provider openai

# Higher frame rate for fast-paced UI
python video2testcase.py recording.mov --fps 4

# Just extract frames (no AI cost), review manually
python video2testcase.py recording.mov --frames-only

# Custom output name
python video2testcase.py recording.mov --output login_flow_tests

# Analyze more frames (lower interval = more frames sent to AI)
python video2testcase.py recording.mov --sample-interval 5
```

---

## API Setup

### Option A: Anthropic (Claude) — Recommended

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

### Option B: OpenAI (GPT-4o)

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an API key
3. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
4. Use `--provider openai` when running

---

## Custom Test Case Principles

You can customize how test cases are written by providing your own principles file:

```bash
python video2testcase.py recording.mov --principles my_standards.md
```

If you place a file named `test_case_creation_principles.md` in the same directory as the video, it will be picked up automatically.

The included `test_case_creation_principles.md` covers:
- Clarity, independence, repeatability, traceability, maintainability
- Naming conventions (Verify that..., Verify if the user...)
- Pre-conditions, expected outcomes, test data guidelines
- Test type classification (Smoke, Sanity, Regression, E2E)

---

## Output Formats

### Markdown (`.md`)
Full document with flow analysis, test case table, and summary statistics.

### CSV (`.csv`)
Tab-importable into Google Sheets, Jira, TestRail, or any test management tool. Checkmarks rendered as `✓`.

### Excel (`.xlsx`)
Professionally styled with:
- Color-coded header row
- Alternating row shading
- Auto-filters on every column
- Frozen header row
- Auto-sized columns

---

## Project Structure

```
video2testcase/
├── video2testcase.py                   # Main CLI tool
├── requirements.txt                    # Python dependencies
├── .env.example                        # API key template
├── .gitignore                          # Git ignore rules
├── test_case_creation_principles.md    # QA principles (auto-loaded)
├── test_case_template.md               # Reference template
└── README.md                           # This file
```

---

## Tips

- **Short videos work best**: 1–5 minute recordings of a single flow produce the most focused test cases.
- **Record one flow per video**: Login flow, checkout flow, onboarding flow — keep them separate.
- **Review and refine**: AI-generated test cases are a strong starting point. Have your QA team review and adjust.
- **Lower `--sample-interval`** for complex UIs where many small changes happen quickly.
- **Use `--frames-only`** to preview what the AI will see before spending API credits.

---

## Cost Estimate

Each run makes 2–4 API calls depending on video length:

| Provider | Approximate Cost per Run |
|----------|-------------------------|
| Claude (Anthropic) | ~$0.30 – $1.00 |
| GPT-4o (OpenAI) | ~$0.50 – $1.50 |

Costs scale with frame count and video length.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ffmpeg: command not found` | Install ffmpeg (see Prerequisites) |
| `ANTHROPIC_API_KEY not set` | Add key to `.env` or export in shell |
| Unicode filename error | Tool handles this automatically via symlink |
| `openpyxl not installed` | Run `pip install openpyxl` for Excel support |
| Too few test cases generated | Lower `--sample-interval` to send more frames |

---

## License

MIT
