from tools.profit_rtd_book_oos_regime_coverage_ledger import _metadata_integrity


def main():
    clean = {
        'requested_cycles': 120,
        'completed_cycles': 120,
        'collection_errors': 0,
        'missing_price_count': 0,
        'price_capture': True,
    }
    bad = {
        'requested_cycles': 120,
        'completed_cycles': 119,
        'collection_errors': 1,
        'missing_price_count': 1,
        'price_capture': False,
    }

    clean_result = _metadata_integrity(clean, [{}] * 120, 0, 120)
    bad_result = _metadata_integrity(bad, [{}] * 119, 0, 119)

    assert clean_result['eligible'] is True
    assert clean_result['integrity_reasons'] == []
    assert bad_result['eligible'] is False
    assert 'INCOMPLETE_COLLECTION' in bad_result['integrity_reasons']
    assert 'COLLECTION_ERRORS_PRESENT' in bad_result['integrity_reasons']
    assert 'MISSING_SYNCHRONIZED_PRICE' in bad_result['integrity_reasons']
    assert 'PRICE_CAPTURE_NOT_COMPLETE' in bad_result['integrity_reasons']
    print('PROFIT_RTD_RC53_3=OK')


if __name__ == '__main__':
    main()
