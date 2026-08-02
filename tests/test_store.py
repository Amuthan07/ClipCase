import pytest

from eval.store import (
    EvalResult,
    Generation,
    ProductionRequest,
    connect,
    get_eval_results_for_generation,
    get_generations_for_recording,
    init_db,
    insert_eval_result,
    insert_generation,
    insert_production_request,
    insert_recording,
)


@pytest.fixture
def conn(tmp_path):
    db_path = str(tmp_path / "eval.db")
    init_db(db_path)
    connection = connect(db_path)
    yield connection
    connection.close()


def test_insert_and_read_recording(conn):
    recording = insert_recording(conn, source_path="clips/demo.mov")
    assert recording.mode == "video"

    row = conn.execute("SELECT * FROM recordings WHERE id = ?", (recording.id,)).fetchone()
    assert row["source_path"] == "clips/demo.mov"


def test_insert_generation_links_to_recording(conn):
    recording = insert_recording(conn, source_path="clips/demo.mov")
    generation = Generation(
        id="gen-1",
        recording_id=recording.id,
        model="claude",
        generated_output="| Test Case ID | ... |",
        latency_ms=1200,
    )
    insert_generation(conn, generation)

    rows = get_generations_for_recording(conn, recording.id)
    assert len(rows) == 1
    assert rows[0]["model"] == "claude"
    assert rows[0]["latency_ms"] == 1200


def test_insert_eval_result_links_to_generation(conn):
    recording = insert_recording(conn, source_path="clips/demo.mov")
    generation = Generation(
        id="gen-1", recording_id=recording.id, model="gpt-4o", generated_output="doc"
    )
    insert_generation(conn, generation)

    result = EvalResult(id="res-1", generation_id="gen-1", structural_accuracy=0.8)
    insert_eval_result(conn, result)

    rows = get_eval_results_for_generation(conn, "gen-1")
    assert len(rows) == 1
    assert rows[0]["structural_accuracy"] == 0.8


def test_insert_production_request(conn):
    request = ProductionRequest(
        id="prod-1", model="gemini", confidence_score=0.9, latency_ms=800, cost_usd=0.01
    )
    insert_production_request(conn, request)

    row = conn.execute("SELECT * FROM production_requests WHERE id = ?", ("prod-1",)).fetchone()
    assert row["model"] == "gemini"
    assert row["confidence_score"] == 0.9
    assert row["mode"] == "video"


def test_generations_scoped_to_recording(conn):
    recording_a = insert_recording(conn, source_path="a.mov")
    recording_b = insert_recording(conn, source_path="b.mov")
    insert_generation(
        conn, Generation(id="gen-a", recording_id=recording_a.id, model="claude", generated_output="a")
    )
    insert_generation(
        conn, Generation(id="gen-b", recording_id=recording_b.id, model="claude", generated_output="b")
    )

    assert len(get_generations_for_recording(conn, recording_a.id)) == 1
    assert len(get_generations_for_recording(conn, recording_b.id)) == 1
