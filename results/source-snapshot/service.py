"""Stable root-facing services; no HTTP or browser dependencies."""
from .core import search, validate


def solve(payload: dict) -> dict:
    scenario, algorithm, trace_limit = validate(payload)
    return search(scenario, algorithm, trace_limit)


def compare(payload: dict) -> dict:
    scenario, _, trace_limit = validate(payload, comparison=True)
    results = [search(scenario, name, trace_limit) for name in ("dijkstra", "astar")]
    agree = (results[0]["reachable"], results[0]["cost"]) == (results[1]["reachable"], results[1]["cost"])
    if not agree:
        raise RuntimeError("Shortest-path algorithms disagreed on the validated scenario.")
    return {"schema_version": 1, "results": results, "costs_agree": True}


def presets() -> dict:
    """Return fresh editable synthetic scenarios on each call."""
    campus = [[1] * 18 for _ in range(12)]
    for r in range(1, 11):
        for c in (4, 9, 14):
            if (r, c) not in ((3, 4), (8, 9), (5, 14)):
                campus[r][c] = 0
    for c in range(5, 14):
        campus[6][c] = 5
    return {"schema_version": 1, "kind": "original_synthetic_maps", "scenarios": [
        {"id": "campus", "name": "Campus-style passages", "grid": campus, "start": [1, 1], "goal": [10, 16]},
        {"id": "weighted-detour", "name": "Cheaper detour", "grid": [[1,9,9,9,1],[1,1,1,1,1]], "start": [0,0], "goal": [0,4]},
        {"id": "unreachable", "name": "Closed passage", "grid": [[1,1,0,1,1],[1,1,0,1,1],[1,1,0,1,1]], "start": [1,0], "goal": [1,4]},
        {"id": "open", "name": "Open courtyard", "grid": [[1]*16 for _ in range(10)], "start": [1,1], "goal": [8,14]},
    ]}
