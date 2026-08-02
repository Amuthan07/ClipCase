"""SQLite persistence for the offline eval benchmark and the production request path."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


@dataclass(frozen=True)
class Recording:
    id: str
    source_path: str
    mode: str = "video"


@dataclass(frozen=True)
class Generation:
    id: str
    recording_id: str
    model: str
    generated_output: str
    mode: str = "video"
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None


@dataclass(frozen=True)
class EvalResult:
    id: str
    generation_id: str
    structural_accuracy: float | None = None
    initial_pass: bool | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ProductionRequest:
    id: str
    model: str
    mode: str = "video"
    confidence_score: float | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
    finally:
        conn.close()


def insert_recording(conn: sqlite3.Connection, source_path: str, mode: str = "video") -> Recording:
    recording = Recording(id=str(uuid.uuid4()), source_path=source_path, mode=mode)
    conn.execute(
        "INSERT INTO recordings (id, source_path, mode) VALUES (?, ?, ?)",
        (recording.id, recording.source_path, recording.mode),
    )
    conn.commit()
    return recording


def insert_generation(conn: sqlite3.Connection, generation: Generation) -> Generation:
    conn.execute(
        """
        INSERT INTO generations
            (id, recording_id, mode, model, generated_output,
             prompt_tokens, completion_tokens, latency_ms, cost_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            generation.id,
            generation.recording_id,
            generation.mode,
            generation.model,
            generation.generated_output,
            generation.prompt_tokens,
            generation.completion_tokens,
            generation.latency_ms,
            generation.cost_usd,
        ),
    )
    conn.commit()
    return generation


def insert_eval_result(conn: sqlite3.Connection, result: EvalResult) -> EvalResult:
    conn.execute(
        """
        INSERT INTO eval_results
            (id, generation_id, initial_pass, structural_accuracy, error_message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            result.id,
            result.generation_id,
            result.initial_pass,
            result.structural_accuracy,
            result.error_message,
        ),
    )
    conn.commit()
    return result


def insert_production_request(conn: sqlite3.Connection, request: ProductionRequest) -> ProductionRequest:
    conn.execute(
        """
        INSERT INTO production_requests
            (id, mode, model, confidence_score, latency_ms, cost_usd)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            request.id,
            request.mode,
            request.model,
            request.confidence_score,
            request.latency_ms,
            request.cost_usd,
        ),
    )
    conn.commit()
    return request


def get_generations_for_recording(conn: sqlite3.Connection, recording_id: str) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM generations WHERE recording_id = ? ORDER BY created_at", (recording_id,)
    )
    return cur.fetchall()


def get_eval_results_for_generation(conn: sqlite3.Connection, generation_id: str) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM eval_results WHERE generation_id = ? ORDER BY run_at", (generation_id,)
    )
    return cur.fetchall()
