from tools import profit_rtd_rc54_5_4_orchestrated_session_runner as mod


def run():
    original_preflight = mod.check_market_activity
    original_session = mod.run_warmed_session
    try:
        mod.check_market_activity = lambda **kwargs: {
            'status': 'MARKET_ACTIVITY_NOT_READY', 'active': False, 'reasons': ['NO_NEW_M1_CANDLE_PROGRESS'],
            'observational_only': True, 'predictive_claim_allowed': False,
            'score_influence_allowed': False, 'decision_influence_allowed': False, 'order_execution_allowed': False,
        }
        called = {'session': 0}
        def fake_session(*args, **kwargs):
            called['session'] += 1
            return {'status': 'COMPLETED'}
        mod.run_warmed_session = fake_session
        r = mod.run_orchestrated_session('WINV26')
        assert r['status'] == 'ABORTED_MARKET_ACTIVITY_NOT_READY'
        assert r['session_started'] is False
        assert called['session'] == 0

        mod.check_market_activity = lambda **kwargs: {
            'status': 'MARKET_ACTIVITY_READY', 'active': True, 'reasons': [],
            'observational_only': True, 'predictive_claim_allowed': False,
            'score_influence_allowed': False, 'decision_influence_allowed': False, 'order_execution_allowed': False,
        }
        mod.run_warmed_session = lambda *args, **kwargs: {
            'status': 'COMPLETED', 'reasons': [], 'output_path': 'session.json'
        }
        r = mod.run_orchestrated_session('WINV26')
        assert r['status'] == 'SESSION_COMPLETED'
        assert r['session_started'] is True
        assert r['session']['output_path'] == 'session.json'
        assert r['score_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False
    finally:
        mod.check_market_activity = original_preflight
        mod.run_warmed_session = original_session

    print('PROFIT_RTD_RC54_5_4=OK')


if __name__ == '__main__':
    run()
