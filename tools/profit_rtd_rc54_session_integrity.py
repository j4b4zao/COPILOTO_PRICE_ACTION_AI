from __future__ import annotations

import hashlib
import json
import uuid


SESSION_INTEGRITY_SCHEMA = 'RC54_SESSION_INTEGRITY_V1'


def _canonical_payload(payload):
    canonical = dict(payload)
    canonical.pop('evidence_sha256', None)
    canonical.pop('output_path', None)
    return canonical


def canonical_bytes(payload):
    return json.dumps(
        _canonical_payload(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')


def evidence_sha256(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def seal_session_payload(payload, *, session_id=None):
    sealed = dict(payload)
    sealed['session_integrity_schema'] = SESSION_INTEGRITY_SCHEMA
    sealed['session_id'] = str(session_id or uuid.uuid4().hex)
    sealed['evidence_sha256'] = evidence_sha256(sealed)
    return sealed


def validate_session_integrity(payload):
    if payload.get('session_integrity_schema') != SESSION_INTEGRITY_SCHEMA:
        raise ValueError('RC54_8_REQUIRES_SESSION_INTEGRITY_SCHEMA')
    session_id = str(payload.get('session_id') or '').strip()
    if not session_id:
        raise ValueError('RC54_8_REQUIRES_SESSION_ID')
    recorded = str(payload.get('evidence_sha256') or '').strip().lower()
    if len(recorded) != 64:
        raise ValueError('RC54_8_REQUIRES_EVIDENCE_SHA256')
    expected = evidence_sha256(payload)
    if recorded != expected:
        raise ValueError('RC54_8_REJECTS_TAMPERED_SESSION_EVIDENCE')
    return {
        'session_integrity_schema': SESSION_INTEGRITY_SCHEMA,
        'session_id': session_id,
        'evidence_sha256': recorded,
    }
