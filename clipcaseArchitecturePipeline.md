# ClipCase pipeline architecture — eval dashboard + DOM-aware capture + self-healing agent

Solution architecture for ClipCase's evaluation and self-healing roadmap, sequenced so every phase is buildable with what actually exists at that point — no phase assumes infrastructure from a later phase.

---

## 1. Design principles

- **Dual-mode product, not a pivot.** `video` mode (zero-friction, any screen recording, outputs MD/CSV/Excel) stays exactly as-is. `dom_capture` mode (record via ClipCase's own recorder, outputs runnable Playwright) is additive — an opt-in second path for users who want an executable, self-healing suite. Neither replaces the other.
- **`dom_capture` mode is web-only.** Playwright can only instrument browser pages — it cannot touch a native macOS app, a mobile app, or anything outside a browser context. `video` mode has no such restriction. This is a hard scope boundary on the new mode, not a detail — "record via ClipCase" only ever works for web apps.
- **Offline benchmarking and production scoring are two different systems, not one.** `structural_accuracy` (Phase 1) is scored against a hand-labeled ground truth set that only exists for a small offline benchmark. A real user's new recording has no ground truth. Production gets a separate, reference-free confidence signal — see Phase 2.
- **Single benchmarked-best model in production; 3-way fan-out is offline/opt-in only.** Fanning out to 3 models on every real request is 3x cost and latency for a signal most users won't act on differently. Phase 1's benchmark is what tells you which single model to default to. "Compare across models" stays available as an explicit, user-triggered feature — never the default request path.
- **codegen's captured trace is the source of truth for selectors, not something LLMs re-derive.** Once `dom_capture` exists, Playwright codegen already emits a deterministic, working script with real selectors the moment a user interacts with the page. Phase 4's LLMs enrich that trace (assertions, structure, naming, edge cases) — they do not independently regenerate selectors, which would reintroduce guessing risk with DOM context instead of pixels.
- **"Stability" is a longitudinal claim and must be measured longitudinally.** A script scored immediately after generation only proves it passes at t=0 — trivially true for nearly everything. Real selector stability is % still passing after N days/CI runs, tracked over time, not a single boolean at creation.
- **One pipeline, two consumers.** The eval pipeline (multi-model scoring) and the self-healing pipeline (broken test repair) share the same core primitives: generate → execute/score → verify → record. Self-healing is only reachable once `dom_capture` mode exists.
- **Human approval gate stays on for self-healing.** The agent proposes; a PR is the unit of trust. No silent auto-merge in v1. Internal-only (ClipCase's own test suite) before user-facing.
- **One schema, one dashboard, filterable by mode.** Mode-agnostic metrics (cost, latency, pass rate by model) compare fairly across modes; mode-specific quality metrics stay separate, nullable, never blended into one number.
- **Package structure changes before Playwright does.** ClipCase ships today as a single flat module (`clipcase.py`, entry point `clipcase:main`, no `clipcase/` package directory). Everything through Phase 2 can still live there. Converting to the `clipcase/` package layout in section 4 is a prerequisite for Phase 3, not a byproduct of it — do it as its own step, before DOM-aware capture lands.
- **Local-first, cloud-optional.** SQLite + local Grafana gets you a working system in days.

---

## 2. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | Python 3.11+, asyncio | Async fan-out to 3 APIs for offline benchmarking |
| LLM clients | Existing `analyze_with_anthropic` / `analyze_with_openai` / `analyze_with_gemini` in clipcase.py (lines 176-370) | Already built — wrap, don't reimplement |
| DOM-aware capture | Playwright codegen (adapted) | Wraps Playwright's own resilient, role/text-based selector generation |
| Test execution (dom_capture mode) | Playwright (Python) | Runs the generated scripts for real |
| Data store | SQLite (v1) then Postgres (later) | Zero setup; schema is Postgres-compatible from day one |
| Dashboard | Grafana + SQLite/Postgres data source | Mode-filtered via template variable |
| CI trigger | GitHub Actions | Already your CI |
| Self-healing agent | Claude API (tool use / agentic loop) | Diagnose, propose, verify loop with tool calls |
| PR creation | GitHub API (PyGithub or gh CLI) | Simple, no extra service needed |
| Packaging | `clipcase[playwright]` optional extra | Playwright pulls in browser binaries (100s of MB) via a separate `playwright install` step pip can't run automatically — video-mode-only users shouldn't pay that cost on `pip install clipcase` |

---

## 3. Data schema (SQLite/Postgres compatible)

```sql
CREATE TABLE recordings (
  id TEXT PRIMARY KEY,
  source_path TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'video',   -- 'video' | 'dom_capture' (web-only)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Offline benchmark runs only (Phase 1/4). Never populated by real user traffic.
CREATE TABLE generations (
  id TEXT PRIMARY KEY,
  recording_id TEXT REFERENCES recordings(id),
  mode TEXT NOT NULL DEFAULT 'video',
  model TEXT NOT NULL,
  generated_output TEXT NOT NULL,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  latency_ms INTEGER,
  cost_usd REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE eval_results (
  id TEXT PRIMARY KEY,
  generation_id TEXT REFERENCES generations(id),
  initial_pass BOOLEAN,             -- dom_capture: passed at generation time (t=0, not "stable")
  structural_accuracy REAL,         -- video, offline benchmark only: doc completeness vs ground truth
  error_message TEXT,
  run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Longitudinal: repeated runs of the same generated script over time. This is where "stability" actually lives.
CREATE TABLE stability_runs (
  id TEXT PRIMARY KEY,
  generation_id TEXT REFERENCES generations(id),
  passed BOOLEAN NOT NULL,
  run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- selector_stability_score = derived: passed_count / total_count in stability_runs, over a trailing window

-- Real user traffic. Single production model per mode, no ground truth, self-reported confidence.
CREATE TABLE production_requests (
  id TEXT PRIMARY KEY,
  mode TEXT NOT NULL DEFAULT 'video',   -- 'video' | 'dom_capture', once Phase 4 benchmarks a dom_capture default
  model TEXT NOT NULL,              -- the one benchmarked-best default model for this mode
  confidence_score REAL,            -- reference-free, self-assessed by the model in the same call
  latency_ms INTEGER,
  cost_usd REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE self_heal_events (
  id TEXT PRIMARY KEY,
  test_file TEXT NOT NULL,
  original_selector TEXT NOT NULL,
  proposed_selector TEXT,
  verified BOOLEAN,
  pr_url TEXT,
  status TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Repo structure

```
clipcase/
├── core/                    # existing recording -> MD/CSV/Excel logic (video mode)
│                             # analyze_with_anthropic/openai/gemini already live here
├── capture/
│   └── dom_recorder.py      # Phase 3: wraps Playwright codegen for dom_capture mode
├── eval/                     # OFFLINE BENCHMARKING ONLY - never called from production path
│   ├── orchestrator.py      # fan-out to 3 models, async, mode-aware
│   ├── models/               # thin wrappers around existing analyze_with_* functions
│   │   ├── claude_client.py
│   │   ├── gpt4o_client.py
│   │   └── gemini_client.py
│   ├── scorer.py            # structural_accuracy (video) - Phase 1
│   ├── executor.py          # runs Playwright output, initial_pass - Phase 4
│   ├── stability_tracker.py # repeated runs -> selector_stability_score - Phase 4/6
│   └── store.py             # DB read/write
├── production/                # PRODUCTION PATH - single default model per mode, cheap
│   └── confidence.py        # Phase 2 (video), extended Phase 4 (dom_capture): one model, one call, self-reported confidence_score
├── self_heal/               # Phase 5, dom_capture mode only
│   ├── diagnose.py
│   ├── propose.py
│   ├── verify.py
│   └── open_pr.py
├── dashboard/
│   └── grafana/              # provisioned dashboard JSON, mode template variable
├── db/
│   └── schema.sql
└── .github/workflows/
    ├── eval.yml
    ├── stability.yml         # scheduled re-runs feeding stability_runs
    └── self_heal.yml
```

---

## 5. Build order (each phase buildable with what exists at that point)

**Phase 1 - Offline eval benchmark on existing video mode (2-3 days), buildable today, no prerequisites**
1. db/schema.sql + eval/store.py.
2. eval/models/*_client.py - thin wrappers around the EXISTING analyze_with_anthropic / analyze_with_openai / analyze_with_gemini functions in clipcase.py (lines 176-370) - do not reimplement API calls.
3. eval/orchestrator.py - asyncio.gather() across the three clients, mode always 'video', offline benchmark set only.
4. eval/scorer.py - structural accuracy against a small hand-labeled ground truth set. No Playwright involved. This never runs against real user traffic.
5. Run against 5-10 sample recordings end to end.

**Phase 2 - Production confidence signal + dashboard (1-2 days)**
6. Pick the single best-performing model from Phase 1's benchmark results as the production default for `video` mode.
7. production/confidence.py - one model, one call, prompt it to self-assess confidence in its own output alongside the generated test case. No fan-out, no ground truth, minimal extra cost.
8. Point Grafana at the store. Mode-agnostic panels: cost, latency, benchmark quality by model (offline data only). Add a mode template variable for later.
9. "Compare across models" stays available as an explicit, user-triggered opt-in (reuses Phase 1's orchestrator) - never the default request path.

**Phase 3 - DOM-aware capture, dom_capture mode, web apps only**
10. Restructure the package: `clipcase.py` -> `clipcase/` (`core/`, `cli.py`, etc.), entry point becomes `clipcase = "clipcase.cli:main"`. Existing `clipcase video.mov` CLI contract must not change. Add `playwright` as an optional extra (`clipcase[playwright]`), not a base dependency.
11. capture/dom_recorder.py - adapt Playwright codegen so recording through ClipCase's own recorder captures the action stream plus real role/text-based selectors.
12. Surface this as an explicit second entry point - "record via ClipCase" - distinct from the existing "drop any recording" path, with a one-line note that it's web-only.
13. recordings.mode = 'dom_capture' starts getting written.

**Phase 4 - Playwright enrichment + initial pass scoring (codegen's trace is ground truth, LLMs enrich it)**
14. codegen's raw captured script (real selectors, already working) is the base artifact - not regenerated per model.
15. Model clients enrich that base script (assertions, structure, naming, edge-case variants). Multi-model comparison here measures enrichment quality, not selector accuracy.
16. eval/executor.py - runs the enriched script once, computes initial_pass (boolean, t=0 only - not stability).
17. eval/stability_tracker.py + .github/workflows/stability.yml - re-run generated scripts on a schedule, write to stability_runs. selector_stability_score is derived from this table, not from a single run.
18. Dashboard's dom_capture panels go live once enough stability_runs data exists to be meaningful.
19. Once benchmarking picks a winner, extend production/confidence.py to `dom_capture` mode too - same single-model, no-fan-out, self-reported-confidence pattern as Phase 2, just applied to enriched Playwright output instead of MD/CSV/Excel.

**Phase 5 - Self-healing agent, internal-only first (3-5 days, after Phase 4 is stable)**
20. self_heal/diagnose.py - parse a Playwright error from ClipCase's own CI + capture a DOM snapshot.
21. self_heal/propose.py - agentic call proposing 1-3 selector candidates.
22. self_heal/verify.py - reuses eval/executor.py to confirm the fix works before touching anything.
23. self_heal/open_pr.py - opens a PR, never auto-merges.
24. Wire into .github/workflows/self_heal.yml, triggered on ClipCase's own test failures - dogfooding first. User-facing self-healing is a distinct, larger-scope extension for later.

**Phase 6 - Polish (ongoing)**
- Add self_heal_events panel - time-to-fix, fix acceptance rate (same longitudinal shape as selector_stability_score).
- Expand both ground-truth sets as you go.

---

## 6. Prompt to hand to your coding agent (Phase 1, start here)

```
Build the offline eval benchmark for a project called ClipCase, following this architecture:

- Python 3.11+, asyncio for concurrency
- SQLite database using this schema: [paste schema from section 3]
- Repo structure: [paste structure from section 4]
- ClipCase already has analyze_with_anthropic, analyze_with_openai, and analyze_with_gemini functions in clipcase.py (lines 176-370) that call each model and return generated test case output. WRAP these existing functions, do not reimplement the API calls.
- ClipCase currently outputs Markdown, CSV, and Excel test case documents from screen recordings - there is no Playwright/runnable-script generation yet, so this phase does NOT involve executing anything, only scoring document quality.
- This is an OFFLINE BENCHMARKING system only. It runs against a small hand-labeled sample set, not real user traffic. Do not build any production request path in this phase.

Start with:
1. db/schema.sql and eval/store.py (SQLite read/write functions for recordings, generations, eval_results tables)
2. eval/models/claude_client.py, gpt4o_client.py, gemini_client.py - thin wrappers around the existing analyze_with_* functions, returning generated_output, prompt_tokens, completion_tokens, latency_ms, cost_usd
3. eval/orchestrator.py - takes a recording, fans out to all three model clients concurrently using asyncio.gather, writes results to the store with mode='video'
4. eval/scorer.py - takes a generated MD/CSV/Excel test case doc and a hand-labeled ground truth action list, returns a structural_accuracy score (0-1)

Write tests for each module. Use type hints throughout. Keep each file under 150 lines - split further if needed.
```

Phase 2's production confidence path is intentionally separate from this - come back for that prompt once Phase 1's benchmark tells you which model to default to.
