"""Structural accuracy: does a generated doc mention every ground-truth action, in order?

Offline benchmark only — scores against a hand-labeled ground truth set. Never runs against
real user traffic, which has no ground truth to compare to.
"""

from __future__ import annotations


def structural_accuracy(generated_doc: str, ground_truth_actions: list[str]) -> float:
    """Return the fraction of ground_truth_actions found in generated_doc, in order.

    Matching is case-insensitive substring search, scanning forward from the position of the
    previous match so out-of-order or missing actions aren't credited.
    """
    if not ground_truth_actions:
        return 0.0

    haystack = generated_doc.lower()
    cursor = 0
    matched = 0

    for action in ground_truth_actions:
        needle = action.lower().strip()
        if not needle:
            continue
        pos = haystack.find(needle, cursor)
        if pos == -1:
            continue
        matched += 1
        cursor = pos + len(needle)

    return matched / len(ground_truth_actions)
