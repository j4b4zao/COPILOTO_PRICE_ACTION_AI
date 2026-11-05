"""Private offline comparison against an independently retained pipe record.

This is content fidelity, not authentication, crash durability or authorization.
No trading or native process modules are imported.
"""
import hashlib
import json


def _unique_pairs(pairs):
    value = {}
    for key,item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key')
        value[key] = item
    return value


def _invalid_constant(value):
    raise ValueError('Nonfinite JSON constant: '+value)


def compare(raw, expected):
    """Reject absent/malformed/changed evidence; never infer cleanup from a file."""
    if raw is None:
        return dict(accepted=False,reason='JOURNAL_MISSING',sha256=None,size=0)
    if not isinstance(raw, bytes):
        return dict(accepted=False,reason='INVALID_INPUT_TYPE',sha256=None,size=0)
    digest = hashlib.sha256(raw).hexdigest()
    result = dict(accepted=False,reason='INVALID_JSON',sha256=digest,size=len(raw))
    try:
        actual = json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
        if not isinstance(actual,dict):
            return result
        # Serialization distinguishes bool from int, unlike Python dict equality.
        canonical = lambda value: json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
        if canonical(actual) != canonical(expected):
            result['reason'] = 'CONTENT_MISMATCH'
            return result
    except (ValueError,UnicodeError,TypeError,RecursionError):
        return result
    restrictions = dict(f3='OPEN',offline=True,simulation_only=True,
                        real_operations_authorized=False,runtime_modified=False,
                        production_api_changed=False,constructor_evidence_is_private=True,
                        full_subtree_exit_requires_outer_safety_proof=True)
    if any(type(actual.get(k)) is not type(v) or actual[k] != v for k,v in restrictions.items()):
        result['reason'] = 'INVALID_SCOPE'
        return result
    if (actual.get('schema') != 'A14_7_STARTUP_RECORD'
            or actual.get('subject_cleanup_scope') != 'INNER_JOB_AND_DIRECT_LAUNCH_PROCESS_ONLY'):
        result['reason'] = 'INVALID_SCOPE'
        return result
    if 'certification' in actual and actual['certification'] is not False:
        result['reason'] = 'INVALID_SCOPE'
        return result
    result.update(accepted=True,reason='CONTENT_MATCH')
    return result
