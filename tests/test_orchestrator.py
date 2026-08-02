import types

import pytest

from eval import orchestrator
from eval.store import connect, init_db


def _fake_client(output: str, latency_ms: int = 100):
    def generate(frames, principles, api_key):
        return {
            "generated_output": output,
            "prompt_tokens": None,
            "completion_tokens": None,
            "latency_ms": latency_ms,
            "cost_usd": None,
        }

    return types.SimpleNamespace(generate=generate)


def _failing_client():
    def generate(frames, principles, api_key):
        raise RuntimeError("API down")

    return types.SimpleNamespace(generate=generate)


@pytest.fixture
def conn(tmp_path):
    db_path = str(tmp_path / "eval.db")
    init_db(db_path)
    connection = connect(db_path)
    yield connection
    connection.close()


async def test_fans_out_to_all_configured_models(conn, monkeypatch):
    monkeypatch.setitem(orchestrator.CLIENTS, "claude", _fake_client("claude doc"))
    monkeypatch.setitem(orchestrator.CLIENTS, "gpt-4o", _fake_client("gpt doc"))
    monkeypatch.setitem(orchestrator.CLIENTS, "gemini", _fake_client("gemini doc"))

    saved = await orchestrator.run_benchmark(
        conn,
        source_path="demo.mov",
        frames=["f1.png"],
        principles="principles",
        api_keys={"claude": "k1", "gpt-4o": "k2", "gemini": "k3"},
    )

    assert {g.model for g in saved} == {"claude", "gpt-4o", "gemini"}
    assert all(g.recording_id for g in saved)


async def test_skips_models_without_api_key(conn, monkeypatch):
    monkeypatch.setitem(orchestrator.CLIENTS, "claude", _fake_client("claude doc"))
    monkeypatch.setitem(orchestrator.CLIENTS, "gpt-4o", _fake_client("gpt doc"))
    monkeypatch.setitem(orchestrator.CLIENTS, "gemini", _fake_client("gemini doc"))

    saved = await orchestrator.run_benchmark(
        conn,
        source_path="demo.mov",
        frames=["f1.png"],
        principles="principles",
        api_keys={"claude": "k1"},
    )

    assert {g.model for g in saved} == {"claude"}


async def test_one_model_failing_does_not_block_others(conn, monkeypatch):
    monkeypatch.setitem(orchestrator.CLIENTS, "claude", _fake_client("claude doc"))
    monkeypatch.setitem(orchestrator.CLIENTS, "gpt-4o", _failing_client())

    saved = await orchestrator.run_benchmark(
        conn,
        source_path="demo.mov",
        frames=["f1.png"],
        principles="principles",
        api_keys={"claude": "k1", "gpt-4o": "k2"},
    )

    assert {g.model for g in saved} == {"claude"}
