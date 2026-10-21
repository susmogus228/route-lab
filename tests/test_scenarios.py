"""Every original synthetic example must reconcile with both exact solvers."""
from copy import deepcopy
import json
from pathlib import Path

from route_lab.service import closures, compare, presets, threshold


NEW_IDS = ['city-blocks', 'rush-hour', 'roadworks', 'main-road-bypass',
           'bridge-bottleneck', 'disconnected-district']


def independent_cost(grid, start, goal):
    nodes = [(r, c) for r, row in enumerate(grid) for c, value in enumerate(row) if value]
    distances = {node: float('inf') for node in nodes}
    distances[tuple(start)] = 0
    for _ in range(len(nodes) - 1):
        changed = False
        for r, c in nodes:
            for rr, cc in ((r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)):
                if (rr, cc) not in distances:
                    continue
                candidate = distances[(r, c)] + grid[rr][cc]
                if candidate < distances[(rr, cc)]:
                    distances[(rr, cc)] = candidate
                    changed = True
        if not changed:
            break
    value = distances[tuple(goal)]
    return None if value == float('inf') else value


def test_presets_preserve_original_order_and_add_six_explained_examples():
    result = presets()
    scenarios = result['scenarios']
    assert [item['id'] for item in scenarios] == ['campus', 'weighted-detour', 'unreachable', 'open', *NEW_IDS]
    assert scenarios[1]['grid'] == [[1, 9, 9, 9, 1], [1, 1, 1, 1, 1]]
    assert scenarios[2]['grid'] == [[1, 1, 0, 1, 1]] * 3
    assert scenarios[3]['grid'] == [[1] * 16 for _ in range(10)]
    for item in scenarios[4:]:
        assert item['description'] and item['takeaway']
        assert len(item['grid']) <= 12 and len(item['grid'][0]) <= 18
        assert len(item['grid']) * len(item['grid'][0]) <= 216
    scenarios[4]['grid'][0][0] = 99
    assert presets()['scenarios'][4]['grid'][0][0] != 99


def test_all_scenario_paths_reconcile_with_independent_cost_and_each_other():
    for item in presets()['scenarios']:
        payload = {key: item[key] for key in ('grid', 'start', 'goal')}
        before = deepcopy(payload)
        expected = independent_cost(**payload)
        results = compare({**payload, 'trace_limit': 0})['results']
        assert payload == before
        for result in results:
            assert result['cost'] == expected, item['id']
            assert result['reachable'] == (expected is not None)
            path = result['path']
            if expected is None:
                assert path == [] and result['steps'] is None
            else:
                assert path[0] == item['start'] and path[-1] == item['goal']
                assert all(payload['grid'][r][c] > 0 for r, c in path)
                assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:]))
                assert sum(payload['grid'][r][c] for r, c in path[1:]) == expected
                assert result['steps'] == len(path) - 1


def test_scenario_claims_have_measured_examples():
    scenarios = {item['id']: item for item in presets()['scenarios']}
    rush = scenarios['rush-hour']
    result = threshold({key: rush[key] for key in ('grid', 'start', 'goal')} | {'cells': rush['traffic_cells']})
    assert result['first_switch_cost'] == 2
    assert result['levels'][0]['cost'] == 4 and result['levels'][1]['cost'] == 6
    bridge = scenarios['bridge-bottleneck']
    result = closures({key: bridge[key] for key in ('grid', 'start', 'goal')})
    assert result['critical_count'] == 3 and [3, 5] in result['critical_cells']
    second_crossing = {key: deepcopy(bridge[key]) for key in ('grid', 'start', 'goal')}
    second_crossing['grid'][2][5] = 1
    assert closures(second_crossing)['critical_count'] == 0
    roadworks = scenarios['roadworks']
    detour = compare({key: roadworks[key] for key in ('grid', 'start', 'goal')})['results'][0]
    assert detour['cost'] == detour['steps'] == 12
    assert detour['steps'] > abs(roadworks['goal'][1] - roadworks['start'][1])
    bypass = scenarios['main-road-bypass']
    cheaper = compare({key: bypass[key] for key in ('grid', 'start', 'goal')})['results'][0]
    assert cheaper['cost'] == cheaper['steps'] == 12
    assert cheaper['cost'] < sum(bypass['grid'][0][1:])
    assert cheaper['steps'] > 8
    disconnected = scenarios['disconnected-district']
    assert not compare({key: disconnected[key] for key in ('grid', 'start', 'goal')})['results'][0]['reachable']


def test_new_json_examples_are_solve_ready_and_match_preset_source():
    scenarios = {item['id']: item for item in presets()['scenarios']}
    root = Path(__file__).resolve().parents[1]
    for scenario_id in NEW_IDS:
        payload = json.loads((root / 'examples' / f'{scenario_id}.json').read_text(encoding='utf-8'))
        assert set(payload) == {'grid', 'start', 'goal'}
        assert payload == {key: scenarios[scenario_id][key] for key in ('grid', 'start', 'goal')}
        assert compare(payload)['costs_agree']
