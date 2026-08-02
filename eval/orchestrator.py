"""Fans a recording out to all three model clients concurrently (offline benchmark only, mode='video')."""

from __future__ import annotations

import asyncio
import sqlite3
import uuid

from eval.models import claude_client, gemini_client, gpt4o_client
from eval.store import Generation, insert_generation, insert_recording

CLIENTS = {
    "claude": claude_client,
    "gpt-4o": gpt4o_client,
    "gemini": gemini_client,
}


async def _generate(model_name: str, client, frames: list[str], principles: str, api_key: str) -> Generation:
    result = await asyncio.to_thread(client.generate, frames, principles, api_key)
    return Generation(
        id=str(uuid.uuid4()),
        recording_id="",  # filled in by run_benchmark once the recording row exists
        mode="video",
        model=model_name,
        generated_output=result["generated_output"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        latency_ms=result["latency_ms"],
        cost_usd=result["cost_usd"],
    )


async def run_benchmark(
    conn: sqlite3.Connection,
    source_path: str,
    frames: list[str],
    principles: str,
    api_keys: dict[str, str],
) -> list[Generation]:
    """Run all three models concurrently against one recording's frames, persisting each result.

    api_keys maps model name ('claude', 'gpt-4o', 'gemini') to its API key. Models without a
    configured key are skipped rather than failing the whole batch.
    """
    recording = insert_recording(conn, source_path=source_path, mode="video")

    active = {name: client for name, client in CLIENTS.items() if name in api_keys}
    tasks = [
        _generate(name, client, frames, principles, api_keys[name]) for name, client in active.items()
    ]
    generations = await asyncio.gather(*tasks, return_exceptions=True)

    saved: list[Generation] = []
    for name, generation in zip(active.keys(), generations):
        if isinstance(generation, Exception):
            print(f"  [{name}] generation failed: {generation}")
            continue
        generation = Generation(**{**generation.__dict__, "recording_id": recording.id})
        saved.append(insert_generation(conn, generation))

    return saved
