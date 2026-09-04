from tools.profit_rtd_book_extended_oos_validation_protocol import protocol


def main():
    result = protocol('WINV26')
    assert result['status'] == 'EXTENDED_OOS_VALIDATION_PROTOCOL_READY'
    assert result['cycles_per_session'] == 600
    assert result['interval_seconds'] == 0.25
    assert result['minimum_independent_sessions'] == 3
    assert result['frozen_pattern_thresholds'] is True
    assert result['frozen_predictive_stability_thresholds'] is True
    assert 'profit_rtd_book_reconciliation WINV26 --cycles 600' in result['collection_command']
    assert result['post_collection_sequence'] == [
        'SESSION_INTEGRITY_GATE',
        'OOS_PATTERN_AUDITOR_RC53_6',
        'PREDICTIVE_STABILITY_GATE_RC53_7',
    ]
    assert result['observational_only'] is True
    assert result['predictive_claim_allowed'] is False
    assert result['score_influence_allowed'] is False
    assert result['decision_influence_allowed'] is False
    assert result['order_execution_allowed'] is False
    print('PROFIT_RTD_RC53_8=OK')


if __name__ == '__main__':
    main()
