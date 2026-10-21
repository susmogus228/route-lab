"""Independent behavioral checks for weighted-grid search."""
import itertools
import random

import pytest


def solve(payload):
    from route_lab.service import solve as implementation
    return implementation(payload)


def oracle(grid, start, goal):
    """Bellman-Ford oracle, independent of production graph/cost helpers."""
    rows, cols = len(grid), len(grid[0])
    nodes = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c]]
    distances = {node: float('inf') for node in nodes}
    distances[tuple(start)] = 0
    for _ in range(len(nodes) - 1):
        changed = False
        for r, c in nodes:
            for rr, cc in nodes:
                if abs(r - rr) + abs(c - cc) == 1:
                    candidate = distances[(r, c)] + grid[rr][cc]
                    if candidate < distances[(rr, cc)]:
                        distances[(rr, cc)] = candidate
                        changed = True
        if not changed:
            break
    result = distances[tuple(goal)]
    return None if result == float('inf') else result


def assert_path(result, grid, start, goal, expected):
    assert result['cost'] == expected
    assert result['reachable'] == (expected is not None)
    assert result['cost_unit'] == 'abstract_entry_cost'
    assert result['runtime_ms'] >= 0
    if expected is None:
        assert result['path'] == []
        assert result['steps'] is None
        return
    path = result['path']
    assert path[0] == list(start) and path[-1] == list(goal)
    assert len(set(map(tuple, path))) == len(path)
    assert all(grid[r][c] > 0 for r, c in path)
    assert all(abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1 for a, b in zip(path, path[1:]))
    assert sum(grid[r][c] for r, c in path[1:]) == expected
    assert result['steps'] == len(path)-1


@pytest.mark.parametrize('algorithm', ['dijkstra', 'astar'])
@pytest.mark.parametrize('grid,start,goal,expected', [
    ([[1]], [0,0], [0,0], 0),
    ([[1,9]], [0,0], [0,1], 9),
    ([[1,9]], [0,1], [0,0], 1),
    ([[1,0,1]], [0,0], [0,2], None),
    ([[1,9,9,9,1],[1,1,1,1,1]], [0,0], [0,4], 6),
    ([[3,3,3],[3,3,3]], [0,0], [1,2], 9),
])
def test_required_fixtures(algorithm, grid, start, goal, expected):
    result = solve(dict(grid=grid, start=start, goal=goal, algorithm=algorithm))
    assert_path(result, grid, start, goal, expected)
    assert 1 <= result['expanded'] <= sum(bool(v) for row in grid for v in row)


def test_exhaustive_two_by_two_grids_against_independent_oracle():
    cases = 0
    for values in itertools.product(range(3), repeat=4):
        grid = [list(values[:2]), list(values[2:])]
        nodes = [(r,c) for r in range(2) for c in range(2) if grid[r][c]]
        for start in nodes:
            for goal in nodes:
                expected = oracle(grid, start, goal)
                for algorithm in ('dijkstra', 'astar'):
                    result = solve(dict(grid=grid, start=list(start), goal=list(goal), algorithm=algorithm, trace_limit=0))
                    assert_path(result, grid, start, goal, expected)
                cases += 1
    assert cases == 648


def test_seeded_random_grids_against_independent_oracle():
    rng = random.Random(20261019)
    for _ in range(60):
        rows, cols = rng.randint(2,7), rng.randint(2,7)
        grid = [[0 if rng.random()<.3 else rng.randint(1,9) for _ in range(cols)] for _ in range(rows)]
        grid[0][0] = grid[-1][-1] = 1
        expected = oracle(grid, [0,0], [rows-1,cols-1])
        for algorithm in ('dijkstra','astar'):
            result = solve(dict(grid=grid,start=[0,0],goal=[rows-1,cols-1],algorithm=algorithm))
            assert_path(result,grid,[0,0],[rows-1,cols-1],expected)


def test_trace_recording_does_not_limit_search_and_is_deterministic():
    payload = dict(grid=[[1]*8 for _ in range(8)], start=[0,0],goal=[7,7],algorithm='dijkstra')
    full = solve({**payload,'trace_limit':2048})
    assert len(full['trace']) == full['expanded'] == 64
    assert not full['trace_truncated']
    for limit in (0,1,4):
        result = solve({**payload,'trace_limit':limit})
        assert result['cost'] == full['cost'] and result['path'] == full['path']
        assert result['expanded'] == full['expanded']
        assert len(result['trace']) == limit and result['trace_truncated']
        assert result['trace'] == full['trace'][:limit]
    again = solve(payload)
    assert again['trace'] == full['trace']
    assert set(full['trace'][0]) == {'node','g','h','f'}


@pytest.mark.parametrize('override', [
    {'grid':[]}, {'grid':[[]]}, {'grid':[[1],[1,2]]}, {'grid':[[True]]},
    {'grid':[[1.0]]}, {'grid':[['1']]}, {'grid':[[10]]}, {'grid':[[-1]]},
    {'grid':[[None]]}, {'grid':[[float('nan')]]}, {'grid':[[1]*129]},
    {'grid':[[1]]*129}, {'start':[False,0]}, {'start':[-1,0]},
    {'start':[0]}, {'start':[0,0,0]}, {'start':[0,1]},
    {'goal':[1,0]}, {'algorithm':'bfs'}, {'algorithm':True},
    {'trace_limit':True}, {'trace_limit':-1}, {'trace_limit':2049},
    {'trace_limit':1.0}, {'surprise':True}, {'grid':[[0]]},
])
def test_strict_validation(override):
    from route_lab.core import ValidationError
    payload = {'grid':[[1]],'start':[0,0],'goal':[0,0],**override}
    with pytest.raises(ValidationError) as exc:
        solve(payload)
    assert exc.value.field and str(exc.value)


@pytest.mark.parametrize('payload', [None,[],{}, {'grid':[[1]],'start':[0,0]}])
def test_missing_or_non_object_request(payload):
    from route_lab.core import ValidationError
    with pytest.raises(ValidationError):
        solve(payload)


def test_compare_and_presets_are_reusable_and_do_not_mutate_inputs():
    from route_lab.service import compare, presets
    import copy
    scenarios = presets()['scenarios']
    assert len(scenarios) >= 3
    for scenario in scenarios:
        payload = {k:scenario[k] for k in ('grid','start','goal')}
        original = copy.deepcopy(payload)
        result = compare(payload)
        assert result['costs_agree']
        assert [r['algorithm'] for r in result['results']] == ['dijkstra','astar']
        assert payload == original
    scenarios[0]['grid'][0][0] = 99
    assert presets()['scenarios'][0]['grid'][0][0] != 99


def test_manhattan_bound_is_consistent():
    from route_lab.core import heuristic
    grid = [[3,7,2],[0,4,9],[2,2,2]]
    goal = (2,2)
    for r,row in enumerate(grid):
        for c,value in enumerate(row):
            if value:
                h = heuristic((r,c),goal,2)
                assert h <= oracle(grid,[r,c],list(goal))
                for dr,dc in ((-1,0),(0,1),(1,0),(0,-1)):
                    rr,cc=r+dr,c+dc
                    if 0<=rr<3 and 0<=cc<3 and grid[rr][cc]:
                        assert h <= grid[rr][cc]+heuristic((rr,cc),goal,2)
