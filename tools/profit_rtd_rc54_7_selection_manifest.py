from __future__ import annotations

import hashlib
import json


SCHEMA = 'RC54_7_SELECTION_MANIFEST_V1'
SELECTION_PHASE = 'RC54.7'
VALIDATION_PHASE = 'RC54.8'
SELECTION_CUTOFF = '2026-09-01T00:00:00'
ROBUSTNESS_CANDIDATES = (
    'CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY',
    'CONTEXT_SELL_MICRO_NEUTRAL',
)
SELECTION_THRESHOLDS = {
    'min_sessions': 3,
    'min_occurrences_per_session': 5,
    'min_vote_sessions': 3,
    'min_consistent_horizons': 2,
    'consistency_rate': 2 / 3,
}


def canonical_payload():
    return {
        'schema': SCHEMA,
        'selection_phase': SELECTION_PHASE,
        'validation_phase': VALIDATION_PHASE,
        'selection_cutoff': SELECTION_CUTOFF,
        'robustness_candidates': list(ROBUSTNESS_CANDIDATES),
        'selection_thresholds': dict(SELECTION_THRESHOLDS),
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def canonical_json(payload=None):
    payload = canonical_payload() if payload is None else payload
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def manifest_hash(payload=None):
    return hashlib.sha256(canonical_json(payload).encode('utf-8')).hexdigest()


def manifest():
    payload = canonical_payload()
    return {
        **payload,
        'manifest_sha256': manifest_hash(payload),
    }


def validate_manifest(payload):
    if not isinstance(payload, dict):
        raise ValueError('RC54_8_REQUIRES_SELECTION_MANIFEST')

    supplied_hash = str(payload.get('manifest_sha256') or '').strip().lower()
    body = {k: v for k, v in payload.items() if k != 'manifest_sha256'}
    if body != canonical_payload():
        raise ValueError('RC54_8_REJECTS_NON_CANONICAL_SELECTION_MANIFEST')
    if supplied_hash != manifest_hash(body):
        raise ValueError('RC54_8_REJECTS_SELECTION_MANIFEST_HASH_MISMATCH')
    return manifest()


if __name__ == '__main__':
    print(canonical_json(manifest()))
