from tools.profit_rtd_rc54_7_selection_manifest import (
    ROBUSTNESS_CANDIDATES,
    SELECTION_CUTOFF,
    manifest,
    validate_manifest,
)


def run():
    m = manifest()
    assert m['schema'] == 'RC54_7_SELECTION_MANIFEST_V1'
    assert m['selection_cutoff'] == SELECTION_CUTOFF
    assert tuple(m['robustness_candidates']) == ROBUSTNESS_CANDIDATES
    assert len(m['manifest_sha256']) == 64
    assert validate_manifest(m) == m

    tampered = dict(m)
    tampered['selection_cutoff'] = '2026-08-31T00:00:00'
    try:
        validate_manifest(tampered)
    except ValueError as exc:
        assert 'NON_CANONICAL' in str(exc)
    else:
        raise AssertionError('tampered manifest must be rejected')

    bad_hash = dict(m)
    bad_hash['manifest_sha256'] = '0' * 64
    try:
        validate_manifest(bad_hash)
    except ValueError as exc:
        assert 'HASH_MISMATCH' in str(exc)
    else:
        raise AssertionError('bad manifest hash must be rejected')

    print('PROFIT_RTD_RC54_7_SELECTION_MANIFEST=OK')


if __name__ == '__main__':
    run()
