from types import SimpleNamespace
import tempfile

from tools import profit_rtd_rc54_3_2_warmed_session as session_mod
from tools.profit_rtd_rc54_3_2_warm_history_gate import context_ready, history_ready, warm_history
from tools.profit_rtd_rc54_3_2_warmed_session import data_ready, technical_reasons


class FakeCollector:
    def __init__(self, contexts):
        self.contexts = list(contexts)
        self.index = 0

    def get_data(self):
        if self.index >= len(self.contexts):
            return None
        value = self.contexts[self.index]
        self.index += 1
        return value


class FakePipeline:
    def executar(self, context):
        return context


def _ctx(structure_trend='UNKNOWN', structure_valid=False, bias='NONE', candle_count=8):
    return SimpleNamespace(
        structure=SimpleNamespace(trend=structure_trend, valid=structure_valid),
        price_action=SimpleNamespace(bias=bias),
        market=SimpleNamespace(candle_count=candle_count),
    )


def run():
    assert context_ready(_ctx()) is False
    assert context_ready(_ctx('SIDEWAYS', True, 'BUY')) is True
    assert context_ready(_ctx('UP', True, 'SELL')) is True
    assert history_ready(_ctx('SIDEWAYS', True, 'NONE')) is True
    assert context_ready(_ctx('SIDEWAYS', True, 'NONE')) is False

    cold = FakeCollector([None, _ctx(), _ctx('UNKNOWN', False, 'NONE')])
    r = warm_history(
        'WINV26',
        interval=0,
        max_warmup_cycles=3,
        collector=cold,
        pipeline=FakePipeline(),
    )
    assert r['ready'] is False
    assert r['status'] == 'WARM_HISTORY_NOT_READY'
    assert r['warmup_cycles'] == 3

    ready_context = _ctx('SIDEWAYS', True, 'BUY', 12)
    warm = FakeCollector([None, _ctx(), ready_context, _ctx('UP', True, 'BUY')])
    r = warm_history(
        'WINV26',
        interval=0,
        max_warmup_cycles=10,
        collector=warm,
        pipeline=FakePipeline(),
    )
    assert r['ready'] is True
    assert r['status'] == 'WARM_HISTORY_READY'
    assert r['warmup_cycles'] == 3
    assert r['context'] is ready_context
    assert r['collector'] is warm
    assert r['structure_trend'] == 'SIDEWAYS'
    assert r['pa_bias'] == 'BUY'

    lateral = FakeCollector([_ctx('SIDEWAYS', True, 'NONE', 12)])
    r = warm_history(
        'WINV26', interval=0, max_warmup_cycles=1,
        collector=lateral, pipeline=FakePipeline(),
    )
    assert r['ready'] is True
    assert r['trade_context_ready'] is False

    lateral_required = FakeCollector([_ctx('SIDEWAYS', True, 'NONE', 12)])
    r = warm_history(
        'WINV26', interval=0, max_warmup_cycles=1,
        require_trade_context=True,
        collector=lateral_required, pipeline=FakePipeline(),
    )
    assert r['ready'] is False
    assert r['status'] == 'WARM_TRADE_CONTEXT_NOT_READY'
    assert r['trade_context_ready'] is False

    coverage_gate = FakeCollector([
        _ctx('SIDEWAYS', True, 'NONE', 12),
        _ctx('DOWN', True, 'SELL', 12),
    ])
    r = warm_history(
        'WINV26', interval=0, max_warmup_cycles=2,
        require_trade_context=True,
        collector=coverage_gate, pipeline=FakePipeline(),
    )
    assert r['ready'] is True
    assert r['warmup_cycles'] == 2
    assert r['structure_trend'] == 'DOWN'
    assert r['trade_context_ready'] is True
    assert r['trade_context_required'] is True

    sideways = {'last_price': 178585.0, 'delta_status': 'VALID'}
    assert data_ready(sideways) is True
    assert data_ready({'last_price': 178585.0, 'delta_status': 'LOW_ACTIVITY'}) is True
    reasons = technical_reasons(
        complete=True,
        collection_errors=0,
        missing_price_count=0,
        samples=[sideways],
        delta_failure_samples=0,
    )
    assert reasons == []
    assert 'CONTEXT_READINESS_DROPPED_DURING_SESSION' not in reasons

    assert data_ready({'last_price': 178585.0, 'delta_status': 'INVALID'}) is False
    reasons = technical_reasons(
        complete=True,
        collection_errors=1,
        missing_price_count=0,
        samples=[sideways],
        delta_failure_samples=1,
    )
    assert reasons == ['COLLECTION_ERRORS_PRESENT', 'DELTA_NOT_READY_OR_INVALID']

    reasons = technical_reasons(
        complete=True, collection_errors=0, missing_price_count=0,
        samples=[{'last_price': 178585.0, 'delta_status': 'INITIALIZING'}],
        delta_failure_samples=0,
    )
    assert reasons == []

    originals = {
        name: getattr(session_mod, name)
        for name in ('warm_history', 'snapshot_context', 'ProfitDeltaQualityValidator',
                     'BookDepthSourceDiagnostics', 'BookDepthQualityValidator',
                     'OrderFlowObservationalContextBuilder')
    }
    try:
        context = _ctx('SIDEWAYS', True, 'NONE', 12)
        context.book_depth = object()
        collector = FakeCollector([context])
        collector.order_flow = object()
        session_mod.warm_history = lambda *args, **kwargs: {
            'ready': True, 'status': 'WARM_HISTORY_READY', 'warmup_cycles': 1,
            'context': context, 'collector': collector, 'pipeline': FakePipeline(),
        }
        session_mod.snapshot_context = lambda *_: {
            'last_price': 178585.0, 'delta_status': 'VALID',
            'structure': {'trend': 'SIDEWAYS'}, 'price_action': {'bias': 'NONE'},
            'alignment': 'NEUTRAL',
        }
        noop = type('Noop', (), {'observe': lambda self, *_: object(), 'evaluate': lambda self, *_: object()})
        session_mod.ProfitDeltaQualityValidator = noop
        session_mod.BookDepthSourceDiagnostics = noop
        session_mod.BookDepthQualityValidator = noop
        session_mod.OrderFlowObservationalContextBuilder = type('Builder', (), {'build': lambda self, **_: object()})
        with tempfile.TemporaryDirectory() as td:
            result = session_mod.run_warmed_session('WINV26', cycles=1, interval=0, output_dir=td)
        assert result['status'] == 'COMPLETED'
        assert result['reasons'] == []
        assert result['data_ready'] is True
        assert result['trade_context_ready_at_start'] is True
        assert result['context_ready_at_start'] is True
        assert result['trade_context_ready'] is False
        assert result['context_not_ready_samples'] == 1
        assert result['observational_only'] is True
        assert result['score_influence_allowed'] is False
        assert result['risk_influence_allowed'] is False
        assert result['decision_influence_allowed'] is False
        assert result['order_execution_allowed'] is False
    finally:
        for name, value in originals.items():
            setattr(session_mod, name, value)

    print('PROFIT_RTD_RC54_3_2=OK')


if __name__ == '__main__':
    run()
