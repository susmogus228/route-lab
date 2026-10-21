"""Release-facing behavior and recorded measurement reconciliation."""
import csv
import hashlib
import json

import pytest


def test_benchmark_records_raw_runs_and_reproducible_maps(tmp_path):
    from route_lab.benchmark import run_benchmark
    result = run_benchmark(tmp_path, sizes=(4,), seeds=(11,), repeats=5)
    assert result['kind'] == 'recorded_benchmark'
    assert len(result['rows']) == 6
    assert len(result['measurements']) == 30
    assert len(result['source_sha256']) == 64
    assert result['configuration']['trace_limit'] == 0
    for row in result['rows']:
        assert len(row['raw_ms']) == 5
        assert row['min_ms'] <= row['median_ms'] <= row['max_ms']
        assert row['raw_ms'] == [x['runtime_ms'] for x in result['measurements'] if x['case_id']==row['case_id'] and x['algorithm']==row['algorithm']]
        data = (tmp_path/'scenarios'/f"{row['case_id']}.json").read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['scenario_sha256']
    assert json.loads((tmp_path/'benchmark.json').read_text()) == result
    assert len(list(csv.DictReader((tmp_path/'benchmark.csv').open()))) == 6
    assert '<svg' in (tmp_path/'benchmark.svg').read_text()


def test_cli_actual_route_and_csv_export(tmp_path, capsys):
    from route_lab.cli import main
    scenario = {'grid':[[1,9,9,9,1],[1,1,1,1,1]],'start':[0,0],'goal':[0,4]}
    source = tmp_path/'map.json'
    source.write_text(json.dumps(scenario))
    report, path_csv = tmp_path/'result.json', tmp_path/'path.csv'
    assert main(['solve','--input',str(source),'--algorithm','dijkstra','--output',str(report),'--path-csv',str(path_csv)]) == 0
    result = json.loads(report.read_text())
    assert result['cost'] == 6
    rows = list(csv.DictReader(path_csv.open()))
    assert len(rows) == 7 and rows[-1]['cumulative_cost'] == '6'
    assert rows[0]['cumulative_cost'] == '0'
    assert json.loads(capsys.readouterr().out)['cost'] == 6
    original = source.read_bytes()
    assert main(['solve','--input',str(source),'--output',str(source)]) == 2
    assert source.read_bytes() == original


@pytest.mark.parametrize('text', ['{"grid":[],"grid":[[1]]}', '{"grid":[[NaN]],"start":[0,0],"goal":[0,0]}'])
def test_json_duplicate_keys_and_nonfinite_are_rejected(text):
    from route_lab.cli import strict_json_loads
    with pytest.raises(ValueError):
        strict_json_loads(text)


def test_compare_rejects_algorithm_key():
    from route_lab.core import ValidationError
    from route_lab.service import compare
    with pytest.raises(ValidationError):
        compare({'grid':[[1]],'start':[0,0],'goal':[0,0],'algorithm':'astar'})
