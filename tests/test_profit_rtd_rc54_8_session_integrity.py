import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_7_selection_manifest import manifest
from tools.profit_rtd_rc54_8_oos_candidate_validator import audit_from_manifest
from tools.profit_rtd_rc54_session_integrity import seal_session_payload, validate_session_integrity


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'


def make_payload(*, start, session_id=None):
    samples = []
    for i, price in enumerate(range(200, 179, -1)):
        samples.append({
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': float(price),
            'structure': {'trend': 'DOWN'},
            'price_action': {'bias': 'SELL'},
            'alignment': 'NEUTRAL',
            'trade_context_ready': True,
        })
    return seal_session_payload({
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'symbol': 'WINV26',
        'data_ready': True,
        'observational_only': True,
        'samples': samples,
    }, session_id=session_id)


def write(path, payload):
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def run():
    frozen = manifest()
    cutoff = datetime.fromisoformat(frozen['selection_cutoff'])

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p1 = td / 's1.json'
        p2 = td / 's2.json'
        one = make_payload(start=cutoff + timedelta(minutes=1), session_id='session-one')
        two = make_payload(start=cutoff + timedelta(minutes=2), session_id='session-two')
        write(p1, one)
        write(p2, two)

        assert validate_session_integrity(one)['session_id'] == 'session-one'
        result = audit_from_manifest(CANDIDATE, frozen, [p1, p2], min_occurrences=30, min_sessions=2)
        assert result['session_integrity_required'] is True
        assert result['coverage_met'] is True

        tampered = dict(one)
        tampered['samples'] = [dict(sample) for sample in one['samples']]
        tampered['samples'][0]['last_price'] = 999999.0
        bad = td / 'tampered.json'
        write(bad, tampered)
        try:
            audit_from_manifest(CANDIDATE, frozen, [bad])
        except ValueError as exc:
            assert 'TAMPERED_SESSION_EVIDENCE' in str(exc)
        else:
            raise AssertionError('tampered evidence must be rejected')

        duplicate_id = make_payload(start=cutoff + timedelta(minutes=3), session_id='session-one')
        p3 = td / 'duplicate_id.json'
        write(p3, duplicate_id)
        try:
            audit_from_manifest(CANDIDATE, frozen, [p1, p3])
        except ValueError as exc:
            assert 'UNIQUE_PERSISTED_SESSION_IDS' in str(exc)
        else:
            raise AssertionError('duplicate persisted session id must be rejected')

        copied = td / 'copied.json'
        write(copied, one)
        try:
            audit_from_manifest(CANDIDATE, frozen, [p1, copied])
        except ValueError as exc:
            assert ('UNIQUE_PERSISTED_SESSION_IDS' in str(exc) or
                    'UNIQUE_SESSION_EVIDENCE_HASHES' in str(exc))
        else:
            raise AssertionError('copied session evidence must be rejected')

    print('PROFIT_RTD_RC54_8_SESSION_INTEGRITY=OK')


if __name__ == '__main__':
    run()
