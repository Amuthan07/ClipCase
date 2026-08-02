-- ClipCase eval/production schema (SQLite v1, Postgres-compatible).
-- See clipcaseArchitecturePipeline.md section 3 for design rationale.

CREATE TABLE IF NOT EXISTS recordings (
  id TEXT PRIMARY KEY,
  source_path TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'video',   -- 'video' | 'dom_capture' (web-only)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Offline benchmark runs only (Phase 1/4). Never populated by real user traffic.
CREATE TABLE IF NOT EXISTS generations (
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

CREATE TABLE IF NOT EXISTS eval_results (
  id TEXT PRIMARY KEY,
  generation_id TEXT REFERENCES generations(id),
  initial_pass BOOLEAN,             -- dom_capture: passed at generation time (t=0, not "stable")
  structural_accuracy REAL,         -- video, offline benchmark only: doc completeness vs ground truth
  error_message TEXT,
  run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Longitudinal: repeated runs of the same generated script over time. This is where "stability" actually lives.
CREATE TABLE IF NOT EXISTS stability_runs (
  id TEXT PRIMARY KEY,
  generation_id TEXT REFERENCES generations(id),
  passed BOOLEAN NOT NULL,
  run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- selector_stability_score = derived: passed_count / total_count in stability_runs, over a trailing window

-- Real user traffic. Single production model per mode, no ground truth, self-reported confidence.
CREATE TABLE IF NOT EXISTS production_requests (
  id TEXT PRIMARY KEY,
  mode TEXT NOT NULL DEFAULT 'video',   -- 'video' | 'dom_capture', once Phase 4 benchmarks a dom_capture default
  model TEXT NOT NULL,              -- the one benchmarked-best default model for this mode
  confidence_score REAL,            -- reference-free, self-assessed by the model in the same call
  latency_ms INTEGER,
  cost_usd REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS self_heal_events (
  id TEXT PRIMARY KEY,
  test_file TEXT NOT NULL,
  original_selector TEXT NOT NULL,
  proposed_selector TEXT,
  verified BOOLEAN,
  pr_url TEXT,
  status TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
