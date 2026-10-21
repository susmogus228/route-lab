"""A historical run must retain its exact source evidence after an update."""
import hashlib
from pathlib import Path
import runpy

import pytest


def checker():
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/verify_results.py'))
    assert 'verify_source_files' in namespace, 'Historical benchmark source verification is missing'
    return namespace['verify_source_files']


def fixture(tmp_path):
    repository = tmp_path / 'repository'
    source = repository / 'src/route_lab'
    source.mkdir(parents=True)
    results = tmp_path / 'results'
    results.mkdir()
    original = b'original recorded source\n'
    (source / 'service.py').write_bytes(original)
    return repository, source, results, original, {'service.py': hashlib.sha256(original).hexdigest()}


def test_current_sources_without_snapshot(tmp_path):
    repository, _, results, _, digests = fixture(tmp_path)
    result = checker()(repository, results, digests)
    assert result['current_source_matches'] is True
    assert result['changed_files'] == []


def test_historical_snapshot_reports_current_drift(tmp_path):
    repository, source, results, original, digests = fixture(tmp_path)
    snapshot = results / 'source-snapshot'
    snapshot.mkdir()
    (snapshot / 'service.py').write_bytes(original)
    (source / 'service.py').write_bytes(b'updated service\n')
    result = checker()(repository, results, digests)
    assert result['recorded_source_verified'] is True
    assert result['current_source_matches'] is False
    assert result['changed_files'] == ['service.py']
    assert result['snapshot_files'] == ['service.py']


def test_unrecorded_drift_is_rejected(tmp_path):
    repository, source, results, _, digests = fixture(tmp_path)
    (source / 'service.py').write_bytes(b'updated without evidence\n')
    with pytest.raises(AssertionError, match='service.py'):
        checker()(repository, results, digests)


def test_corrupted_snapshot_is_rejected_even_when_current_matches(tmp_path):
    repository, _, results, _, digests = fixture(tmp_path)
    snapshot = results / 'source-snapshot'
    snapshot.mkdir()
    (snapshot / 'service.py').write_bytes(b'tampered evidence\n')
    with pytest.raises(AssertionError, match='service.py'):
        checker()(repository, results, digests)
