"""Bounded sensitivity analysis checked against independent small-grid oracles."""
from copy import deepcopy
import random

import pytest

from route_lab.core import ValidationError
from route_lab.service import closures, threshold


def oracle(grid, start, goal):
    """Bellman-Ford using explicit orthogonal edges, independent of core helpers."""
    nodes = [(r, c) for r, row in enumerate(grid) for c, value in enumerate(row) if value]
    distances = {node: float('inf') for node in nodes}
    distances[tuple(start)] = 0
    edges = [(a, b, grid[b[0]][b[1]]) for a in nodes for b in nodes
             if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
    for _ in range(len(nodes) - 1):
        changed = False
        for a, b, weight in edges:
            candidate = distances[a] + weight
            if candidate < distances[b]:
                distances[b] = candidate
                changed = True
        if not changed:
            break
    cost = distances[tuple(goal)]
    return None if cost == float('inf') else cost


def connected(grid, start, goal):
    """Flood fill independently determines critical closures."""
    seen, pending = {tuple(start)}, [tuple(start)]
    while pending:
        r, c = pending.pop()
        for rr, cc in ((r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)):
            if (0 <= rr < len(grid) and 0 <= cc < len(grid[0])
                    and grid[rr][cc] and (rr, cc) not in seen):
                seen.add((rr, cc))
                pending.append((rr, cc))
    return tuple(goal) in seen


def check_path(path, grid, start, goal, expected):
    if expected is None:
        assert path == []
        return
    assert path[0] == start and path[-1] == goal
    assert len(set(map(tuple, path))) == len(path)
    assert all(grid[r][c] > 0 for r, c in path)
    assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:]))
    assert sum(grid[r][c] for r, c in path[1:]) == expected


def test_threshold_rush_hour_switch_and_reference_reconciliation():
    payload = dict(grid=[[1] * 5, [1] * 5], start=[0, 0], goal=[0, 4],
                   cells=[[0, 1], [0, 2], [0, 3]])
    before = deepcopy(payload)
    result = threshold(payload)
    assert payload == before
    assert result['schema_version'] == 1 and result['cost_unit'] == 'abstract_entry_cost'
    assert result['cells'] == payload['cells']
    assert result['first_switch_cost'] == 2
    assert result['levels'][0]['cost'] == 4 and result['levels'][1]['cost'] == 6
    assert len(result['levels']) == 9
    reference = result['reference_path']
    check_path(reference, payload['grid'], payload['start'], payload['goal'], 4)
    for cost, level in enumerate(result['levels'], 1):
        grid = deepcopy(payload['grid'])
        for r, c in payload['cells']:
            grid[r][c] = cost
        expected = oracle(grid, payload['start'], payload['goal'])
        assert level['entry_cost'] == cost
        assert level['cost'] == expected and level['reachable'] == (expected is not None)
        check_path(level['path'], grid, payload['start'], payload['goal'], expected)
        assert level['steps'] == len(level['path']) - 1
        reference_cost = sum(grid[r][c] for r, c in reference[1:])
        assert level['reference_cost'] == reference_cost
        assert level['reference_optimal'] == (reference_cost == expected)


def test_equal_cost_alternative_is_not_a_switch():
    result = threshold(dict(grid=[[1, 1, 1], [1, 1, 1]], start=[0, 0], goal=[0, 2], cells=[[0, 1]]))
    assert result['levels'][2]['reference_cost'] == result['levels'][2]['cost'] == 4
    assert result['levels'][2]['reference_optimal']
    assert result['first_switch_cost'] == 4


def test_unreachable_threshold_has_no_reference_or_switch():
    result = threshold(dict(grid=[[1, 1, 0, 1]], start=[0, 0], goal=[0, 3], cells=[[0, 1]]))
    assert result['reference_path'] == [] and result['first_switch_cost'] is None
    for level in result['levels']:
        assert level['path'] == [] and level['cost'] is None and level['steps'] is None
        assert level['reference_cost'] is None and not level['reference_optimal']


def test_unused_traffic_zone_has_no_switch():
    result = threshold(dict(grid=[[1, 1, 1], [1, 1, 1]], start=[0, 0], goal=[0, 2], cells=[[1, 1]]))
    assert result['first_switch_cost'] is None
    assert all(level['reference_optimal'] and level['cost'] == 2 for level in result['levels'])


def test_equal_endpoints_have_zero_cost_and_cannot_be_closed():
    payload = dict(grid=[[1, 1], [1, 1]], start=[0, 0], goal=[0, 0])
    sweep = threshold({**payload, 'cells': [[0, 1]]})
    assert sweep['reference_path'] == [[0, 0]] and sweep['first_switch_cost'] is None
    assert all(level['cost'] == level['reference_cost'] == 0 and level['reference_optimal']
               and level['steps'] == 0 for level in sweep['levels'])
    result = closures(payload)
    assert result['tested_count'] == 3 and result['critical_count'] == 0 and result['worst_delta'] == 0
    assert all(item['cell'] != [0, 0] and item['cost'] == 0 for item in result['cells'])


def test_seeded_random_thresholds_reconcile_every_level_and_reference():
    rng = random.Random(20261021)
    for _ in range(20):
        grid = [[0 if rng.random() < .2 else rng.randint(1, 9) for _ in range(4)] for _ in range(3)]
        grid[0][0] = grid[2][3] = grid[0][1] = 1
        candidates = [[r, c] for r, row in enumerate(grid) for c, weight in enumerate(row)
                      if weight and [r, c] not in ([0, 0], [2, 3])]
        cells = rng.sample(candidates, min(3, len(candidates)))
        payload = dict(grid=grid, start=[0, 0], goal=[2, 3], cells=cells)
        original = deepcopy(payload)
        result = threshold(payload)
        assert payload == original
        first_switch = None
        for level in result['levels']:
            changed = deepcopy(grid)
            for r, c in cells:
                changed[r][c] = level['entry_cost']
            expected = oracle(changed, payload['start'], payload['goal'])
            assert level['cost'] == expected
            check_path(level['path'], changed, payload['start'], payload['goal'], expected)
            reference_cost = (sum(changed[r][c] for r, c in result['reference_path'][1:])
                              if result['reference_path'] else None)
            assert level['reference_cost'] == reference_cost
            assert level['reference_optimal'] == (expected is not None and reference_cost == expected)
            if first_switch is None and expected is not None and reference_cost > expected:
                first_switch = level['entry_cost']
        assert result['first_switch_cost'] == first_switch


@pytest.mark.parametrize('cells', [None, [], [[0, 1], [0, 1]], [[True, 1]], [[0.0, 1]],
                                       [[0, 1.0]], [[0]], [[0, 1, 2]], [[-1, 1]], [[2, 1]],
                                       [[0, 4]], [[0, 0]], [[0, 3]], [[1, 1]], '0,1'])
def test_threshold_rejects_bad_cells(cells):
    payload = dict(grid=[[1, 1, 1, 1], [1, 0, 1, 1]], start=[0, 0], goal=[0, 3], cells=cells)
    with pytest.raises(ValidationError) as error:
        threshold(payload)
    assert error.value.field.startswith('cells')


def test_threshold_cells_are_required_and_bounded():
    with pytest.raises(ValidationError) as error:
        threshold(dict(grid=[[1, 1]], start=[0, 0], goal=[0, 1]))
    assert error.value.field == 'cells'
    with pytest.raises(ValidationError):
        threshold(dict(grid=[[1] * 35], start=[0, 0], goal=[0, 34], cells=[[0, c] for c in range(1, 34)]))
    with pytest.raises(ValidationError):
        threshold(dict(grid=[[1]], start=[0, 0], goal=[0, 0], cells=[[0, 0]]))


@pytest.mark.parametrize('function,extra', [(threshold, {'cells': [[0, 1]]}), (closures, {})])
@pytest.mark.parametrize('unknown', ['algorithm', 'trace_limit', 'unexpected'])
def test_analysis_rejects_unknown_keys(function, extra, unknown):
    with pytest.raises(ValidationError) as error:
        function(dict(grid=[[1, 1, 1]], start=[0, 0], goal=[0, 2], **extra, **{unknown: 1}))
    assert error.value.field == unknown


@pytest.mark.parametrize('function,extra', [(threshold, {'cells': [[0, 1]]}), (closures, {})])
@pytest.mark.parametrize('bad', [None, [], {}, {'grid': [[True]], 'start': [0, 0], 'goal': [0, 0]}])
def test_analysis_uses_strict_core_validation(function, extra, bad):
    payload = {**bad, **extra} if isinstance(bad, dict) else bad
    with pytest.raises(ValidationError):
        function(payload)


@pytest.mark.parametrize('function,extra', [(threshold, {'cells': [[0, 1]]}), (closures, {})])
def test_analysis_limit_counts_walls_as_well_as_walkable_cells(function, extra):
    grid = [[0] * 17 for _ in range(16)]
    grid[0][:3] = [1, 1, 1]
    with pytest.raises(ValidationError) as error:
        function(dict(grid=grid, start=[0, 0], goal=[0, 2], **extra))
    assert error.value.field == 'grid' and '256' in str(error.value)


def test_exactly_256_total_cells_are_accepted():
    grid = [[0] * 16 for _ in range(16)]
    grid[0][:3] = [1, 1, 1]
    assert closures(dict(grid=grid, start=[0, 0], goal=[0, 2]))['tested_count'] == 1
    assert threshold(dict(grid=grid, start=[0, 0], goal=[0, 2], cells=[[0, 1]]))['first_switch_cost'] is None


def test_maximum_traffic_zone_and_equal_endpoint_closure_count():
    assert len(threshold(dict(grid=[[1] * 34], start=[0, 0], goal=[0, 33],
                              cells=[[0, c] for c in range(1, 33)]))['cells']) == 32
    result = closures(dict(grid=[[1] * 16 for _ in range(16)], start=[0, 0], goal=[0, 0]))
    assert result['tested_count'] == 255 and result['worst_delta'] == 0


def test_closures_are_independent_exclude_endpoints_and_preserve_inputs():
    payload = dict(grid=[[1, 1, 1], [1, 1, 1]], start=[0, 0], goal=[0, 2])
    before = deepcopy(payload)
    result = closures(payload)
    assert payload == before
    assert result['schema_version'] == 1 and result['cost_unit'] == 'abstract_entry_cost'
    assert result['baseline']['cost'] == 2 and result['baseline']['trace'] == []
    assert result['tested_count'] == 4 and result['critical_count'] == 0
    assert result['critical_cells'] == [] and result['worst_delta'] == 2
    costs = {tuple(item['cell']): item['cost'] for item in result['cells']}
    assert costs == {(0, 1): 4, (1, 0): 2, (1, 1): 2, (1, 2): 2}


def test_closures_on_bridge_unreachable_and_singleton():
    bridge = closures(dict(grid=[[1, 1, 1, 1]], start=[0, 0], goal=[0, 3]))
    assert bridge['critical_cells'] == [[0, 1], [0, 2]] and bridge['critical_count'] == 2
    assert bridge['worst_delta'] is None
    assert all(item['critical'] and item['delta'] is None for item in bridge['cells'])
    disconnected = closures(dict(grid=[[1, 1, 0, 1, 1]], start=[0, 0], goal=[0, 4]))
    assert not disconnected['baseline']['reachable'] and disconnected['critical_count'] == 0
    assert disconnected['worst_delta'] is None
    assert all(not item['critical'] and item['delta'] is None for item in disconnected['cells'])
    singleton = closures(dict(grid=[[1]], start=[0, 0], goal=[0, 0]))
    assert singleton['baseline']['cost'] == 0
    assert singleton['tested_count'] == 0 and singleton['cells'] == [] and singleton['worst_delta'] is None


def test_seeded_random_closures_against_cost_and_connectivity_oracles():
    rng = random.Random(20261020)
    for _ in range(25):
        rows, cols = rng.randint(2, 4), rng.randint(2, 4)
        grid = [[0 if rng.random() < .3 else rng.randint(1, 9) for _ in range(cols)] for _ in range(rows)]
        grid[0][0] = grid[-1][-1] = 1
        start, goal = [0, 0], [rows - 1, cols - 1]
        result = closures(dict(grid=grid, start=start, goal=goal))
        baseline = oracle(grid, start, goal)
        assert result['baseline']['cost'] == baseline
        expected_cells = [[r, c] for r, row in enumerate(grid) for c, weight in enumerate(row)
                          if weight and [r, c] not in (start, goal)]
        assert [item['cell'] for item in result['cells']] == expected_cells
        assert result['tested_count'] == len(expected_cells)
        deltas, critical = [], []
        for item in result['cells']:
            changed = deepcopy(grid)
            r, c = item['cell']
            changed[r][c] = 0
            expected = oracle(changed, start, goal)
            assert item['cost'] == expected and item['reachable'] == connected(changed, start, goal)
            is_critical = baseline is not None and expected is None
            assert item['critical'] == is_critical
            if is_critical:
                critical.append(item['cell'])
            delta = expected - baseline if expected is not None and baseline is not None else None
            assert item['delta'] == delta
            if delta is not None:
                assert delta >= 0
                deltas.append(delta)
        assert result['critical_cells'] == critical and result['critical_count'] == len(critical)
        assert result['worst_delta'] == (max(deltas) if deltas else None)
