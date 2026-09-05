import contextlib
import io
import tempfile

from tools import profit_rtd_rc54_5_4_orchestrated_session_runner as mod


def run():
    output = io.StringIO()
    stream = mod._ConciseProgress(output, every=50)
    stream.write('[VOLUME DEBUG] noisy\n')
    stream.write('[RC54.3.2 WARMUP] cycle=1/100 structure=UNKNOWN pa_bias=NONE history_ready=False trade_context_ready=False\n')
    stream.write('[RC54.3.2 WARMUP] cycle=2/100 structure=UNKNOWN pa_bias=NONE history_ready=False trade_context_ready=False\n')
    stream.write('[RC54.3.2 WARMUP] cycle=3/100 structure=SIDEWAYS pa_bias=NONE history_ready=True trade_context_ready=False\n')
    stream.write('[RC54.3.2 WARMUP] cycle=50/100 structure=SIDEWAYS pa_bias=NONE history_ready=True trade_context_ready=False\n')
    stream.write('[RC54.3.2 WARMUP] cycle=51/100 error=RuntimeError:test\n')
    stream.flush()
    concise = output.getvalue()
    assert '[VOLUME DEBUG]' not in concise
    assert 'cycle=1/100' in concise
    assert 'cycle=2/100' not in concise
    assert 'cycle=3/100' in concise
    assert 'cycle=50/100' in concise
    assert 'error=RuntimeError:test' in concise

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
        tmp_path = tempfile.mkdtemp()
        with mod._runner_lock('WINV26', lock_dir=tmp_path):
            locked = mod.run_orchestrated_session('WINV26', lock_dir=tmp_path)
        assert locked['status'] == 'ABORTED_RUNNER_ALREADY_ACTIVE'
        assert locked['preflight']['status'] == 'RUNNER_ALREADY_ACTIVE'
        assert locked['warmup_started'] is False
        assert locked['session_started'] is False
        assert locked['score_influence_allowed'] is False
        assert locked['order_execution_allowed'] is False

        r = mod.run_orchestrated_session('WINV26')
        assert r['status'] == 'ABORTED_MARKET_ACTIVITY_NOT_READY'
        assert r['session_started'] is False
        assert r['incremental_identifiability_by_context'] == {}
        assert r['incrementally_identifiable_contexts'] == []
        assert called['session'] == 0

        aborted_output = io.StringIO()
        with contextlib.redirect_stdout(aborted_output):
            aborted_exit_code = mod.main(['WINV26', '--preflight-cycles', '90'])
        aborted_rendered = aborted_output.getvalue()
        assert aborted_exit_code == 2
        assert 'PROFIT_RTD_RC54_5_4=ABORTED_MARKET_ACTIVITY_NOT_READY' in aborted_rendered
        assert 'warmup_started=False' in aborted_rendered
        assert 'session_started=False' in aborted_rendered
        assert called['session'] == 0

        mod.check_market_activity = lambda **kwargs: {
            'status': 'MARKET_ACTIVITY_READY', 'active': True, 'reasons': [],
            'observational_only': True, 'predictive_claim_allowed': False,
            'score_influence_allowed': False, 'decision_influence_allowed': False, 'order_execution_allowed': False,
        }
        captured = {}
        def ready_session(*args, **kwargs):
            captured.update(kwargs)
            return {
                'status': 'COMPLETED', 'data_ready': True, 'trade_context_ready': True,
                'reasons': [], 'output_path': 'session.json',
                'samples': [
                    {'context_ready': True, 'structure': {'trend': 'UP'}, 'price_action': {'bias': 'BUY'}, 'alignment': 'NEUTRAL'},
                    {'context_ready': True, 'structure': {'trend': 'UP'}, 'price_action': {'bias': 'BUY'}, 'alignment': 'BULLISH_ALIGNED'},
                ],
            }
        mod.run_warmed_session = ready_session
        r = mod.run_orchestrated_session('WINV26', require_trade_context_at_start=True)
        assert r['status'] == 'SESSION_COMPLETED'
        assert r['session_started'] is True
        assert r['session']['output_path'] == 'session.json'
        assert captured['require_trade_context_at_start'] is True
        assert r['incrementally_identifiable_contexts'] == ['BUY']
        assert r['incremental_identifiability_by_context']['BUY']['distinct_micro_bucket_count'] == 2
        assert r['score_influence_allowed'] is False
        assert r['risk_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False

        cli_output = io.StringIO()
        with contextlib.redirect_stdout(cli_output):
            exit_code = mod.main([
                'WINV26', '--preflight-cycles', '90', '--cycles', '600',
                '--max-warmup-cycles', '1800', '--require-trade-context-at-start',
                '--concise-output', '--progress-every', '50',
            ])
        rendered = cli_output.getvalue()
        assert exit_code == 0
        assert 'PROFIT_RTD_RC54_5_4=SESSION_COMPLETED' in rendered
        assert 'session_data_ready=True' in rendered
        assert 'session_trade_context_ready=True' in rendered
        assert 'incrementally_identifiable_contexts=["BUY"]' in rendered
        assert 'incremental_identifiability_by_context=' in rendered
        assert 'risk_influence_allowed=False' in rendered
        assert 'order_execution_allowed=False' in rendered

        mod.run_warmed_session = lambda *args, **kwargs: {
            'status': 'ABORTED_CONTEXT_NOT_READY', 'reasons': ['WARM_TRADE_CONTEXT_NOT_READY']
        }
        r = mod.run_orchestrated_session('WINV26', require_trade_context_at_start=True)
        assert r['status'] == 'SESSION_ABORTED_AFTER_PREFLIGHT'
        assert r['warmup_started'] is True
        assert r['session_started'] is False

        warmup_abort_output = io.StringIO()
        with contextlib.redirect_stdout(warmup_abort_output):
            warmup_abort_exit_code = mod.main([
                'WINV26', '--require-trade-context-at-start', '--max-warmup-cycles', '1800',
            ])
        warmup_abort_rendered = warmup_abort_output.getvalue()
        assert warmup_abort_exit_code == 2
        assert 'PROFIT_RTD_RC54_5_4=SESSION_ABORTED_AFTER_PREFLIGHT' in warmup_abort_rendered
        assert 'warmup_started=True' in warmup_abort_rendered
        assert 'session_started=False' in warmup_abort_rendered
        assert 'session_status=ABORTED_CONTEXT_NOT_READY' in warmup_abort_rendered
        assert 'session_reasons=WARM_TRADE_CONTEXT_NOT_READY' in warmup_abort_rendered
    finally:
        mod.check_market_activity = original_preflight
        mod.run_warmed_session = original_session

    print('PROFIT_RTD_RC54_5_4=OK')


if __name__ == '__main__':
    run()
