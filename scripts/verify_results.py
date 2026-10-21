"""Reconcile supplied measurements, map bytes and algorithm source hashes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET


def verify_source_files(repository, results, source_files):
    """Verify recorded bytes and report current drift without rewriting history."""
    changed, snapshots = [], []
    for filename, digest in source_files.items():
        assert Path(filename).name == filename and filename.endswith('.py')
        current = repository / 'src' / 'route_lab' / filename
        current_matches = current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == digest
        if not current_matches:
            changed.append(filename)
        snapshot = results / 'source-snapshot' / filename
        if snapshot.is_file():
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == digest, filename
            snapshots.append(filename)
        else:
            assert current_matches, f'{filename}: current source differs and no recorded snapshot exists'
    return {'recorded_source_verified': True, 'current_source_matches': not changed,
            'changed_files': changed, 'snapshot_files': snapshots}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',type=Path,default=Path('results'))
    args=parser.parse_args()
    repository=Path(__file__).resolve().parents[1]
    results=args.results.resolve()
    document=json.loads((results/'benchmark.json').read_text(encoding='utf-8'))
    canonical=lambda x:(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    assert hashlib.sha256(canonical(document['configuration'])).hexdigest()==document['protocol_sha256']
    assert hashlib.sha256(canonical(document['source_files'])).hexdigest()==document['source_sha256']
    source_report = verify_source_files(repository, results, document['source_files'])
    expected_cases=len(document['configuration']['families'])*len(document['configuration']['sizes'])*len(document['configuration']['seeds'])
    assert len(document['rows'])==expected_cases*2
    assert len(document['measurements'])==expected_cases*2*document['configuration']['repeats']
    groups={}
    for row in document['rows']:
        case_id=row['case_id']
        assert Path(case_id).name==case_id
        raw=[m['runtime_ms'] for m in document['measurements'] if m['case_id']==case_id and m['algorithm']==row['algorithm']]
        assert raw==row['raw_ms'] and len(raw)==document['configuration']['repeats']
        assert row['median_ms']==statistics.median(raw)
        assert row['min_ms']==min(raw) and row['max_ms']==max(raw)
        scenario_bytes=(results/'scenarios'/f'{case_id}.json').read_bytes()
        assert hashlib.sha256(scenario_bytes).hexdigest()==row['scenario_sha256']
        payload=json.loads(scenario_bytes)
        assert row['blocked_cells']==sum(v==0 for line in payload['grid'] for v in line)
        assert sum(row['cost_histogram'].values())==row['size']**2
        groups.setdefault(case_id,[]).append(row)
    for pair in groups.values():
        assert len(pair)==2 and pair[0]['reachable']==pair[1]['reachable'] and pair[0]['cost']==pair[1]['cost']
    with (results/'benchmark.csv').open(encoding='utf-8',newline='') as stream:
        assert len(list(csv.DictReader(stream)))==len(document['rows'])
    with (results/'benchmark-raw.csv').open(encoding='utf-8',newline='') as stream:
        assert len(list(csv.DictReader(stream)))==len(document['measurements'])
    root=ET.parse(results/'benchmark.svg').getroot()
    assert root.tag=='{http://www.w3.org/2000/svg}svg'
    print(json.dumps({'verified':True,'scenarios':expected_cases,'summary_rows':len(document['rows']),'timed_runs':len(document['measurements']),'source_sha256':document['source_sha256'], 'source_verification': source_report}))


if __name__=='__main__':
    main()
