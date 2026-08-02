"""CLI: score every generation for a recording against a hand-labeled ground truth file."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.scorer import structural_accuracy
from eval.store import EvalResult, connect, get_generations_for_recording, insert_eval_result

DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "db" / "eval.db")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score generations for a recording against ground truth.")
    parser.add_argument("recording_id", help="recordings.id to score")
    parser.add_argument("ground_truth", help="Path to a ground truth JSON file (see eval/ground_truth/)")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    ground_truth = json.loads(Path(args.ground_truth).read_text())
    actions = ground_truth["actions"]

    conn = connect(args.db)
    try:
        generations = get_generations_for_recording(conn, args.recording_id)
        if not generations:
            print(f"No generations found for recording {args.recording_id}")
            sys.exit(1)

        print(f"{'Model':<10}{'structural_accuracy':<22}")
        for generation in generations:
            score = structural_accuracy(generation["generated_output"], actions)
            insert_eval_result(
                conn,
                EvalResult(id=str(uuid.uuid4()), generation_id=generation["id"], structural_accuracy=score),
            )
            print(f"{generation['model']:<10}{score:<22.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
