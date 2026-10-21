"""Exact, bounded sensitivity experiments on synthetic weighted grids.

All costs count entry into destination cells. The starting cell is free.
These experiments have no geographic, traffic prediction, or time-unit model.
"""
from .core import Scenario, ValidationError, search, validate

MAX_ANALYSIS_CELLS = 256
MAX_TRAFFIC_CELLS = 32


def _validated(payload: dict, *, traffic: bool = False) -> Scenario:
    if not isinstance(payload, dict):
        raise ValidationError("Request must be a JSON object.")
    allowed = {"grid", "start", "goal"} | ({"cells"} if traffic else set())
    unknown = set(payload) - allowed
    if unknown:
        raise ValidationError("Unknown request field.", str(sorted(unknown, key=str)[0]))
    scenario, _, _ = validate({key: value for key, value in payload.items() if key != "cells"})
    if len(scenario.grid) * len(scenario.grid[0]) > MAX_ANALYSIS_CELLS:
        raise ValidationError(
            "Bounded analysis supports at most 256 total grid cells, including walls. "
            "Use a smaller map for this experiment.", "grid")
    return scenario


def _traffic_cells(payload: dict, scenario: Scenario) -> list[list[int]]:
    if "cells" not in payload:
        raise ValidationError("Missing required field: cells.", "cells")
    cells = payload["cells"]
    if not isinstance(cells, list) or not 1 <= len(cells) <= MAX_TRAFFIC_CELLS:
        raise ValidationError("Select 1 through 32 unique traffic cells.", "cells")
    selected = []
    seen = set()
    for index, point in enumerate(cells):
        field = f"cells[{index}]"
        if not isinstance(point, list) or len(point) != 2 or any(type(value) is not int for value in point):
            raise ValidationError("Coordinate must be [row, column] with two integers.", field)
        r, c = point
        if not 0 <= r < len(scenario.grid) or not 0 <= c < len(scenario.grid[0]):
            raise ValidationError("Traffic cell lies outside the grid.", field)
        if not scenario.grid[r][c]:
            raise ValidationError("Traffic cells must be walkable.", field)
        cell = (r, c)
        if cell in (scenario.start, scenario.goal):
            raise ValidationError("Traffic cells cannot include the start or goal.", field)
        if cell in seen:
            raise ValidationError("Traffic cells must be unique.", field)
        seen.add(cell)
        selected.append([r, c])
    return selected


def _changed(scenario: Scenario, grid: list[list[int]]) -> Scenario:
    """Revalidate to recompute the heuristic's minimum entry cost after edits."""
    result, _, _ = validate({"grid": grid, "start": list(scenario.start), "goal": list(scenario.goal)})
    return result


def threshold(payload: dict) -> dict:
    """Sweep a selected zone's common entry cost; ties never count as a switch.

The reference route is the deterministic optimal A* route with the zone set
to 1. A switch means that *this route* becomes strictly more expensive than
the current optimum, not that a search happens to choose a different tie.
An unreachable baseline has no reference and reference_optimal is False.
"""
    scenario = _validated(payload, traffic=True)
    cells = _traffic_cells(payload, scenario)
    levels = []
    reference = []
    first_switch = None
    for entry_cost in range(1, 10):
        grid = [list(row) for row in scenario.grid]
        for r, c in cells:
            grid[r][c] = entry_cost
        result = search(_changed(scenario, grid), "astar", 0)
        if entry_cost == 1:
            reference = [point[:] for point in result["path"]]
        reference_cost = sum(grid[r][c] for r, c in reference[1:]) if reference else None
        reference_optimal = reference_cost is not None and reference_cost == result["cost"]
        if first_switch is None and reference_cost is not None and result["cost"] < reference_cost:
            first_switch = entry_cost
        levels.append({
            "entry_cost": entry_cost,
            "reachable": result["reachable"],
            "cost": result["cost"],
            "steps": result["steps"],
            "path": result["path"],
            "reference_cost": reference_cost,
            "reference_optimal": reference_optimal,
        })
    return {"schema_version": 1, "cost_unit": "abstract_entry_cost", "cells": cells,
            "reference_path": reference, "first_switch_cost": first_switch, "levels": levels}


def closures(payload: dict) -> dict:
    """Close each traversable non-endpoint independently, then solve exactly."""
    scenario = _validated(payload)
    baseline = search(scenario, "astar", 0)
    cases, critical_cells, deltas = [], [], []
    for r, row in enumerate(scenario.grid):
        for c, weight in enumerate(row):
            if not weight or (r, c) in (scenario.start, scenario.goal):
                continue
            grid = [list(original) for original in scenario.grid]
            grid[r][c] = 0
            result = search(_changed(scenario, grid), "astar", 0)
            critical = baseline["reachable"] and not result["reachable"]
            delta = result["cost"] - baseline["cost"] if result["reachable"] and baseline["reachable"] else None
            if delta is not None:
                if delta < 0:
                    raise RuntimeError("Closing a cell unexpectedly reduced the optimal route cost.")
                deltas.append(delta)
            cell = [r, c]
            if critical:
                critical_cells.append(cell)
            cases.append({"cell": cell, "reachable": result["reachable"], "cost": result["cost"],
                          "steps": result["steps"], "delta": delta, "critical": critical})
    return {"schema_version": 1, "cost_unit": "abstract_entry_cost", "baseline": baseline,
            "tested_count": len(cases), "critical_count": len(critical_cells),
            "critical_cells": critical_cells, "worst_delta": max(deltas) if deltas else None,
            "cells": cases}
