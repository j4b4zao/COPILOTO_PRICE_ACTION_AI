import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_7_selection_manifest import manifest
from tools.profit_rtd_rc54_8_oos_candidate_validator import audit_from_manifest
from tools.profit_rtd_rc54_session_integrity import seal_session_payload


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'


def make_session(path, *, start, prices):
    samples = []
    for i, price in enumerate(prices):
        samples.append({
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': float(price),
            'structure': {'trend': 'DOWN'},
            'price_action': {'bias': 'SELL'},
            'alignment': 'NEUTRAL',
            'trade_context_ready': True,
        })
    payload = seal_session_payload({
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'data_ready': True,
        'observational_only': True,
        'samples': samples,
    })
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def run():
    frozen = manifest()
    cutoff = datetime.fromisoformat(frozen['selection_cutoff'])

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p1 = td / 'holdout_1.json'
        p2 = td / 'holdout_2.json'
        prices = list(range(200, 179, -1))
        make_session(p1, start=cutoff + timedelta(minutes=1), prices=prices)
        make_session(p2, start=cutoff + timedelta(minutes=2), prices=prices)

        r = audit_from_manifest(CANDIDATE, frozen, [p1, p2], min_occurrences=30, min_sessions=2)
        assert r['selection_cutoff'] == cutoff.isoformat()
        assert r['selection_manifest_schema'] == frozen['schema']
        assert r['selection_manifest_sha256'] == frozen['manifest_sha256']
        assert r['session_integrity_required'] is True
        assert all(row.get('session_id') for row in r['session_rows'])
        assert all(row.get('evidence_sha256') for row in r['session_rows'])
        assert r['coverage_met'] is True

        tampered = dict(frozen)
        tampered['selection_cutoff'] = '2026-08-31T00:00:00'
        try:
            audit_from_manifest(CANDIDATE, tampered, [p1, p2])
        except ValueError as exc:
            assert 'NON_CANONICAL' in str(exc)
        else:
            raise AssertionError('tampered cutoff must be rejected')

        try:
            audit_from_manifest('CONTEXT_BUY_MICRO_NEUTRAL', frozen, [p1, p2])
        except ValueError as exc:
            assert 'CANDIDATE_FROM_SELECTION_MANIFEST' in str(exc)
        else:
            raise AssertionError('non-survivor candidate must be rejected')

    print('PROFIT_RTD_RC54_8_SELECTION_MANIFEST_GATE=OK')


if __name__ == '__main__':
    run()
