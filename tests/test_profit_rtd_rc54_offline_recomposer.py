import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_offline_recomposer import main, recompose


def make_session(path, start, *, ready=True, data_ready=True, prices=None):
    prices = prices or [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111]
    samples = []
    for i, price in enumerate(prices):
        samples.append({
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': float(price),
            'trade_context_ready': ready,
            'context_ready': ready,
            'structure': {'trend': 'UP' if ready else 'SIDEWAYS'},
            'price_action': {'bias': 'BUY' if ready else 'NONE'},
            'alignment': 'NEUTRAL',
        })
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'data_ready': data_ready,
        'price_capture': True,
        'observational_only': True,
        'collection_errors': 0,
        'delta_failure_samples': 0,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def run():
    base = datetime.fromisoformat('2026-08-28T09:00:00')
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean = []
        for i in range(3):
            path = td / f'clean_{i}.json'
            make_session(path, base + timedelta(hours=i), ready=(i == 0))
            clean.append(path)

        result = recompose(clean)
        assert result['manifest_valid'] is True
        assert len(result['accepted_selection_paths']) == 3
        assert result['inventory_summary'] == {
            'discovered_sessions': 3,
            'accepted_selection_sessions': 3,
            'accepted_oos_sessions': 0,
            'rejected_sessions': 0,
            'rejection_reasons': {},
        }
        lateral_path = str(clean[1].resolve())
        assert lateral_path in result['accepted_selection_paths']
        assert result['context_reports'][lateral_path]['ready_samples'] == 0
        assert result['context_reports'][lateral_path]['buckets'] == {}
        assert result['robustness']['robustness_candidates'] == []
        assert result['robustness']['robustness_candidates'] == []
        assert result['observational_only'] is True
        assert result['score_influence_allowed'] is False
        assert result['risk_influence_allowed'] is False
        assert result['decision_influence_allowed'] is False
        assert result['order_execution_allowed'] is False

        duplicate = td / 'duplicate.json'
        duplicate.write_bytes(clean[0].read_bytes())
        result = recompose([clean[0], duplicate])
        assert result['manifest_valid'] is False
        assert result['manifest'][1]['reasons'] == ['DUPLICATE_CONTENT']

        overlapping = td / 'overlapping.json'
        make_session(overlapping, base + timedelta(seconds=5))
        result = recompose([overlapping, clean[0]])
        assert result['manifest_valid'] is False
        by_path = {row['path']: row for row in result['manifest']}
        rejected_overlap = by_path[str(overlapping.resolve())]
        assert rejected_overlap['eligible'] is False
        assert rejected_overlap['reasons'] == ['TEMPORAL_OVERLAP']
        assert rejected_overlap['overlaps_with'] == str(clean[0].resolve())
        assert result['inventory_summary']['rejection_reasons'] == {
            'TEMPORAL_OVERLAP': 1,
        }

        invalid = td / 'invalid.json'
        make_session(invalid, base + timedelta(hours=4), data_ready=False)
        result = recompose([invalid])
        assert result['manifest_valid'] is False
        assert 'DATA_READY_NOT_TRUE' in result['manifest'][0]['reasons']

        contradictory = td / 'contradictory.json'
        make_session(contradictory, base + timedelta(hours=4, minutes=30), data_ready=True)
        payload = json.loads(contradictory.read_text(encoding='utf-8'))
        payload['collection_errors'] = 1
        contradictory.write_text(json.dumps(payload), encoding='utf-8')
        result = recompose([contradictory])
        assert result['manifest_valid'] is False
        assert 'COLLECTION_ERRORS_PRESENT' in result['manifest'][0]['reasons']

        unordered = td / 'unordered.json'
        make_session(unordered, base + timedelta(hours=5))
        payload = json.loads(unordered.read_text(encoding='utf-8'))
        payload['samples'][2]['timestamp'] = payload['samples'][1]['timestamp']
        unordered.write_text(json.dumps(payload), encoding='utf-8')
        result = recompose([unordered])
        assert result['manifest_valid'] is False
        assert 'SAMPLE_TIMESTAMPS_NOT_STRICTLY_INCREASING' in result['manifest'][0]['reasons']

        holdout = td / 'holdout.json'
        make_session(holdout, base + timedelta(minutes=30))
        result = recompose([clean[0]], holdout_paths=[holdout], selection_cutoff=(base + timedelta(hours=1)).isoformat())
        assert result['manifest_valid'] is False
        assert 'OOS_NOT_STRICTLY_AFTER_CUTOFF' in result['manifest'][1]['reasons']

        try:
            recompose([clean[0]], holdout_paths=[holdout])
        except ValueError as exc:
            assert 'RC54_RECOMPOSER_REQUIRES_FROZEN_SELECTION_CUTOFF_FOR_OOS' in str(exc)
        else:
            raise AssertionError('OOS without a frozen cutoff must be rejected')

        overlap_cutoff = (base + timedelta(minutes=30)).isoformat()
        result = recompose([clean[0]], holdout_paths=[clean[0]], selection_cutoff=overlap_cutoff)
        assert result['manifest_valid'] is False
        assert 'DUPLICATE_PATH' in result['manifest'][1]['reasons']

        valid_holdout = td / 'valid_holdout.json'
        make_session(valid_holdout, base + timedelta(hours=8))
        try:
            recompose(
                clean,
                holdout_paths=[valid_holdout],
                candidate='CONTEXT_BUY_MICRO_NEUTRAL',
                selection_cutoff=(base + timedelta(hours=7)).isoformat(),
            )
        except ValueError as exc:
            assert 'RC54_RECOMPOSER_CANDIDATE_NOT_ROBUST_IN_SELECTION' in str(exc)
        else:
            raise AssertionError('non-robust candidate must not enter RC54.8')

        inventory = recompose([clean[0], invalid], inventory_mode=True)
        assert inventory['schema_version'] == 'RC54_OFFLINE_RECOMPOSITION_V1'
        assert inventory['manifest_valid'] is False
        assert inventory['verdict'] == 'INVENTORY_RECOMPOSED_WITH_EXCLUSIONS'
        assert inventory['inventory_summary']['discovered_sessions'] == 2
        assert inventory['inventory_summary']['rejected_sessions'] == 1
        assert inventory['inventory_summary']['rejection_reasons'] == {'DATA_READY_NOT_TRUE': 1}

        discover_dir = td / 'discover'
        discover_dir.mkdir()
        make_session(discover_dir / 'profit_rtd_rc54_3_2_clean.json', base)
        make_session(discover_dir / 'profit_rtd_rc54_3_2_invalid.json', base + timedelta(hours=1), data_ready=False)
        output = td / 'discovered.json'
        assert main(['--discover-dir', str(discover_dir), '--output', str(output)]) == 0
        discovered = json.loads(output.read_text(encoding='utf-8'))
        assert discovered['inventory_mode'] is True
        assert len(discovered['accepted_selection_paths']) == 1
        assert discovered['inventory_summary']['discovered_sessions'] == 2
        assert discovered['inventory_summary']['accepted_selection_sessions'] == 1
        assert discovered['inventory_summary']['rejected_sessions'] == 1

    print('PROFIT_RTD_RC54_OFFLINE_RECOMPOSER=OK')


if __name__ == '__main__':
    run()
