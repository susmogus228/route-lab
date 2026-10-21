"""Strict grid modeling and deterministic heap-based shortest paths."""
from dataclasses import dataclass
import heapq
import itertools
from time import perf_counter_ns

MAX_DIMENSION = 128
MAX_TRACE = 2048
NEIGHBORS = ((-1, 0), (0, 1), (1, 0), (0, -1))


class ValidationError(ValueError):
    """An actionable field-specific request validation error."""
    def __init__(self, message: str, field: str = "request"):
        super().__init__(message)
        self.field = field


@dataclass(frozen=True)
class Scenario:
    grid: tuple[tuple[int, ...], ...]
    start: tuple[int, int]
    goal: tuple[int, int]
    minimum_cost: int


def validate(payload: dict, *, comparison: bool = False) -> tuple[Scenario, str, int]:
    if not isinstance(payload, dict):
        raise ValidationError("Request must be a JSON object.")
    allowed = {"grid", "start", "goal", "trace_limit"}
    if not comparison:
        allowed.add("algorithm")
    unknown = set(payload) - allowed
    if unknown:
        raise ValidationError("Unknown request field.", str(sorted(unknown, key=str)[0]))
    for key in ("grid", "start", "goal"):
        if key not in payload:
            raise ValidationError(f"Missing required field: {key}.", key)
    grid = payload["grid"]
    if not isinstance(grid, list) or not 1 <= len(grid) <= MAX_DIMENSION:
        raise ValidationError("Grid must have 1 through 128 rows.", "grid")
    width = None
    positive = []
    for r, row in enumerate(grid):
        if not isinstance(row, list) or not 1 <= len(row) <= MAX_DIMENSION:
            raise ValidationError("Each grid row must have 1 through 128 columns.", f"grid[{r}]")
        if width is None:
            width = len(row)
        if len(row) != width:
            raise ValidationError("Grid rows must have the same length.", f"grid[{r}]")
        for c, value in enumerate(row):
            if type(value) is not int or not 0 <= value <= 9:
                raise ValidationError("Cell cost must be an integer from 0 through 9; 0 is a wall.", f"grid[{r}][{c}]")
            if value:
                positive.append(value)
    endpoints = []
    for key in ("start", "goal"):
        point = payload[key]
        if not isinstance(point, list) or len(point) != 2 or any(type(x) is not int for x in point):
            raise ValidationError("Coordinate must be [row, column] with two integers.", key)
        r, c = point
        if not 0 <= r < len(grid) or not 0 <= c < width:
            raise ValidationError("Coordinate lies outside the grid.", key)
        if not grid[r][c]:
            raise ValidationError("Coordinate must be on a walkable cell.", key)
        endpoints.append((r, c))
    algorithm = payload.get("algorithm", "astar")
    if not isinstance(algorithm, str) or algorithm not in ("dijkstra", "astar"):
        raise ValidationError("Algorithm must be astar or dijkstra.", "algorithm")
    trace_limit = payload.get("trace_limit", 512)
    if type(trace_limit) is not int or not 0 <= trace_limit <= MAX_TRACE:
        raise ValidationError("Trace limit must be an integer from 0 through 2048.", "trace_limit")
    return Scenario(tuple(tuple(row) for row in grid), *endpoints, min(positive)), algorithm, trace_limit


def heuristic(node: tuple[int, int], goal: tuple[int, int], minimum_cost: int) -> int:
    """Consistent lower bound for orthogonal moves with destination costs."""
    return (abs(node[0] - goal[0]) + abs(node[1] - goal[1])) * minimum_cost


def search(scenario: Scenario, algorithm: str, trace_limit: int = 512) -> dict:
    """Search a validated immutable scenario; trace limits never stop search.

    Tie order is (f, h, insertion serial). Neighbors are up, right, down,
    left. Dijkstra uses h=0. heap_peak includes stale queue entries.
    """
    started = perf_counter_ns()
    grid, start, goal = scenario.grid, scenario.start, scenario.goal
    rows, cols = len(grid), len(grid[0])
    serial = itertools.count()
    initial_h = heuristic(start, goal, scenario.minimum_cost) if algorithm == "astar" else 0
    heap = [(initial_h, initial_h, next(serial), 0, start)]
    distances = {start: 0}
    previous = {}
    settled = set()
    trace = []
    expanded, heap_peak = 0, 1
    while heap:
        f, h, _, g, node = heapq.heappop(heap)
        if node in settled or g != distances.get(node):
            continue
        settled.add(node)
        expanded += 1
        if len(trace) < trace_limit:
            trace.append({"node": list(node), "g": g, "h": h, "f": f})
        if node == goal:
            break
        r, c = node
        for dr, dc in NEIGHBORS:
            rr, cc = r + dr, c + dc
            neighbor = (rr, cc)
            if not 0 <= rr < rows or not 0 <= cc < cols or not grid[rr][cc] or neighbor in settled:
                continue
            candidate = g + grid[rr][cc]
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = node
                next_h = heuristic(neighbor, goal, scenario.minimum_cost) if algorithm == "astar" else 0
                heapq.heappush(heap, (candidate + next_h, next_h, next(serial), candidate, neighbor))
        heap_peak = max(heap_peak, len(heap))
    reachable = goal in settled
    path = []
    if reachable:
        node = goal
        while node != start:
            path.append(list(node))
            node = previous[node]
        path.append(list(start))
        path.reverse()
    elapsed_ms = (perf_counter_ns() - started) / 1_000_000
    return {
        "schema_version": 1,
        "algorithm": algorithm,
        "reachable": reachable,
        "cost": distances[goal] if reachable else None,
        "cost_unit": "abstract_entry_cost",
        "path": path,
        "steps": len(path) - 1 if reachable else None,
        "expanded": expanded,
        "heap_peak": heap_peak,
        "runtime_ms": elapsed_ms,
        "trace": trace,
        "trace_truncated": expanded > len(trace),
        "heuristic": "manhattan_times_min_entry_cost" if algorithm == "astar" else "zero",
    }
