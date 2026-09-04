from tools.profit_rtd_book_oos_regime_coverage_ledger import analyze


def main():
    result = analyze([])
    assert result['status'] == 'MORE_OOS_REGIME_DIVERSITY_REQUIRED'
    assert 'NO_CLEAN_OOS_SESSIONS' in result['reasons']
    assert 'POSITIVE_REGIME_COVERAGE_MISSING' in result['reasons']
    assert result['observational_only'] is True
    assert result['predictive_claim_allowed'] is False
    assert result['score_influence_allowed'] is False
    assert result['decision_influence_allowed'] is False
    assert result['order_execution_allowed'] is False
    print('PROFIT_RTD_RC53_2=OK')


if __name__ == '__main__':
    main()
