"""RC7.11 legacy report audit: isolated, synthetic, no live market access."""
import json
from pathlib import Path

import pytest

from replay.historical_rtd_legacy_audit import audit_file


def sample(cycle, timestamp='2026-08-27T14:40:02.419'):
    return dict(cycle=cycle, timestamp=timestamp, delta_status='VALID',
                book_status='VALID', context_ready=True, recent_delta=1.0,
                dominance=0.5, persistence=0.5, acceleration=0.0,
                imbalance=0.1, spread=5.0, last_price=170000.0,
                confidence=0.6)


def report(samples, **changes):
    data = dict(symbol='WINV26', requested_cycles=5, samples=samples,
                observational_only=True, predictive_claim_allowed=False,
                score_influence_allowed=False, decision_influence_allowed=False,
                order_execution_allowed=False)
    data.update(changes)
    return data


def run(tmp_path, data):
    path = tmp_path / 'legacy.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    before = path.read_bytes()
    result = audit_file(path)
    assert path.read_bytes() == before
    assert not result.trading_allowed
    assert not result.raw_market_tape_verified
    assert not result.source_authenticity_verified
    return result


def test_valid_samples_are_partial_not_complete(tmp_path):
    r = run(tmp_path, report([sample(1), sample(2, '2026-08-27T14:40:03.419')]))
    assert r.classification == 'PARTIAL'
    assert r.coverage_ratio == 0.4


def test_cycle_jump_is_not_claimed_as_rtd_gap(tmp_path):
    r = run(tmp_path, report([sample(1), sample(4, '2026-08-27T14:40:03.419')]))
    assert r.cycle_jumps == 1 and r.missing_intermediate_cycles == 2
    assert r.classification == 'PARTIAL'


def test_reversed_cycle_invalid(tmp_path):
    r = run(tmp_path, report([sample(3), sample(2)]))
    assert r.classification == 'INVALID'


def test_reversed_time_invalid(tmp_path):
    r = run(tmp_path, report([sample(1, '2026-08-27T14:40:03'),
                              sample(2, '2026-08-27T14:40:02')]))
    assert r.classification == 'INVALID'


def test_unsafe_flags_invalid(tmp_path):
    r = run(tmp_path, report([sample(1), sample(2)], order_execution_allowed=True))
    assert r.classification == 'INVALID' and not r.safe_flags


def test_missing_flag_invalid(tmp_path):
    d = report([sample(1), sample(2)])
    del d['predictive_claim_allowed']
    assert run(tmp_path, d).classification == 'INVALID'


def test_nonfinite_number_invalid(tmp_path):
    s = sample(1)
    s['last_price'] = float('nan')
    assert run(tmp_path, report([s, sample(2)])).classification == 'INVALID'


def test_boolean_number_invalid(tmp_path):
    s = sample(1)
    s['confidence'] = True
    assert run(tmp_path, report([s, sample(2)])).classification == 'INVALID'


def test_empty_insufficient(tmp_path):
    assert run(tmp_path, report([])).classification == 'INSUFFICIENT'


def test_single_insufficient(tmp_path):
    assert run(tmp_path, report([sample(1)])).classification == 'INSUFFICIENT'


def test_bad_samples_structure_rejected(tmp_path):
    with pytest.raises(ValueError, match='LEGACY_SAMPLES_LIST_REQUIRED'):
        run(tmp_path, report(None))


def test_status_counts(tmp_path):
    a, b = sample(1), sample(2, '2026-08-27T14:40:03')
    b['book_status'] = 'INITIALIZING'
    b['context_ready'] = False
    r = run(tmp_path, report([a, b]))
    assert r.book_status == {'INITIALIZING': 1, 'VALID': 1}
    assert r.context_ready == {'False': 1, 'True': 1}
