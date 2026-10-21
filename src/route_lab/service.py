"""Stable root-facing services; no HTTP or browser dependencies."""
from .core import search, validate
from .analysis import closures, threshold


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
        {"id": "city-blocks", "name": "City blocks",
         "description": "Synthetic street grid with building blocks and several intersections. Every move enters one adjacent cell.",
         "takeaway": "Several equal-cost routes can be optimal; a different path alone does not mean one algorithm is more accurate.",
         "grid": [[1,1,1,1,1,1,1,1,1,1,1],
                  [1,0,0,1,0,0,1,0,0,0,1],
                  [1,0,0,1,0,0,1,0,0,0,1],
                  [1,1,1,1,1,1,1,1,1,1,1],
                  [1,0,0,1,0,0,1,0,0,0,1],
                  [1,0,0,1,0,0,1,0,0,0,1],
                  [1,1,1,1,1,1,1,1,1,1,1]], "start": [0,0], "goal": [6,10]},
        {"id": "rush-hour", "name": "Rush hour",
         "description": "Two parallel synthetic streets. Raise the entry cost of the three highlighted cells to model a congestion penalty.",
         "takeaway": "The direct route costs 4 at level 1; at level 2 the six-step bypass is cheaper than the original route's cost of 7.",
         "grid": [[1,1,1,1,1],[1,1,1,1,1]], "start": [0,0], "goal": [0,4],
         "traffic_cells": [[0,1],[0,2],[0,3]]},
        {"id": "roadworks", "name": "Roadworks",
         "description": "A closed section interrupts the central street. Upper and lower streets provide two possible detours.",
         "takeaway": "A closure can preserve connectivity while increasing the number of steps. Test another closure to find fragile detours.",
         "grid": [[0,0,0,0,0,0,0,0,0],
                  [1,1,1,1,1,1,1,1,1],
                  [1,0,0,0,0,0,0,0,1],
                  [1,1,1,1,0,0,1,1,1],
                  [1,0,0,0,0,0,0,0,1],
                  [1,1,1,1,1,1,1,1,1],
                  [0,0,0,0,0,0,0,0,0]], "start": [3,0], "goal": [3,8]},
        {"id": "main-road-bypass", "name": "Main road vs bypass",
         "description": "The short upper street has high entry penalties. The longer lower bypass has unit-cost cells.",
         "takeaway": "The optimal weighted route minimizes total entry cost, which can require more steps than the geometric shortest path.",
         "grid": [[1,4,4,4,4,4,4,4,1],
                  [1,0,0,0,0,0,0,0,1],
                  [1,1,1,1,1,1,1,1,1]], "start": [0,0], "goal": [0,8],
         "traffic_cells": [[0,1],[0,2],[0,3],[0,4],[0,5],[0,6],[0,7]]},
        {"id": "bridge-bottleneck", "name": "Bridge bottleneck",
         "description": "Two open districts are connected by one bridge across a blocked column. The bridge is a synthetic passage, not a geographic road.",
         "takeaway": "An optimal route can still be fragile: closing the only bridge disconnects the endpoints. Opening a second crossing can restore redundancy.",
         "grid": [[1,1,1,1,1,0,1,1,1,1,1],
                  [1,1,1,1,1,0,1,1,1,1,1],
                  [1,1,1,1,1,0,1,1,1,1,1],
                  [1,1,1,1,1,1,1,1,1,1,1],
                  [1,1,1,1,1,0,1,1,1,1,1],
                  [1,1,1,1,1,0,1,1,1,1,1],
                  [1,1,1,1,1,0,1,1,1,1,1]], "start": [3,1], "goal": [3,9]},
        {"id": "disconnected-district", "name": "Disconnected district",
         "description": "A continuous barrier separates two synthetic districts. Both endpoints are valid, but there is no crossing.",
         "takeaway": "An unreachable result is meaningful. Closing more cells cannot create a new critical failure when the endpoints were already disconnected.",
         "grid": [[1,1,1,1,0,1,1,1,1],
                  [1,0,0,1,0,1,0,0,1],
                  [1,1,1,1,0,1,1,1,1],
                  [1,0,0,1,0,1,0,0,1],
                  [1,1,1,1,0,1,1,1,1],
                  [1,1,1,1,0,1,1,1,1]], "start": [2,1], "goal": [2,7]},
    ]}
