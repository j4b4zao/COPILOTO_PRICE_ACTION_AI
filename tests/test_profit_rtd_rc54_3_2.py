from types import SimpleNamespace

from tools.profit_rtd_rc54_3_2_warm_history_gate import context_ready, warm_history
from tools import profit_rtd_rc54_3_2_warmed_session as session_mod


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


def _test_readiness_separation():
    original_warm = session_mod.warm_history
    original_context_ready = session_mod.context_ready
    original_snapshot = session_mod.snapshot_context
    original_delta = session_mod.ProfitDeltaQualityValidator
    original_book_diag = session_mod.BookDepthSourceDiagnostics
    original_book_validator = session_mod.BookDepthQualityValidator
    original_builder = session_mod.OrderFlowObservationalContextBuilder

    class SessionCollector:
        def __init__(self):
            self.items = [
                SimpleNamespace(last_price=100.0, ready=True, book_depth=SimpleNamespace()),
                SimpleNamespace(last_price=101.0, ready=False, book_depth=SimpleNamespace()),
            ]
            self.index = 0
            self.order_flow = SimpleNamespace()

        def get_data(self):
            item = self.items[self.index]
            self.index += 1
            return item

    class NoopDiag:
        def observe(self, _value):
            return {}

    class NoopValidator:
        def evaluate(self, *args, **kwargs):
            return {}

    class NoopBuilder:
        def build(self, **kwargs):
            return SimpleNamespace()

    collector = SessionCollector()
    try:
        session_mod.warm_history = lambda *args, **kwargs: {
            'ready': True,
            'status': 'WARM_HISTORY_READY',
            'warmup_cycles': 1,
            'collector': collector,
            'pipeline': FakePipeline(),
            'context': collector.items[0],
        }
        session_mod.context_ready = lambda context: bool(context.ready)
        session_mod.snapshot_context = lambda context, _micro: {
            'alignment': 'NEUTRAL',
            'last_price': context.last_price,
            'structure': {'trend': 'SIDEWAYS'},
            'price_action': {'bias': 'NONE'},
        }
        session_mod.ProfitDeltaQualityValidator = NoopValidator
        session_mod.BookDepthSourceDiagnostics = NoopDiag
        session_mod.BookDepthQualityValidator = NoopValidator
        session_mod.OrderFlowObservationalContextBuilder = NoopBuilder

        r = session_mod.run_warmed_session(
            'WINV26',
            cycles=2,
            interval=0,
            output_dir='data/test_rc54_8',
        )
        assert r['status'] == 'COMPLETED'
        assert r['data_ready'] is True
        assert r['context_not_ready_samples'] == 1
        assert r['trade_context_ready_samples'] == 1
        assert r['trade_context_ready_at_end'] is False
        assert 'CONTEXT_READINESS_DROPPED_DURING_SESSION' in r['trade_context_reasons']
        assert 'CONTEXT_READINESS_DROPPED_DURING_SESSION' not in r['reasons']
        assert r['score_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False
    finally:
        session_mod.warm_history = original_warm
        session_mod.context_ready = original_context_ready
        session_mod.snapshot_context = original_snapshot
        session_mod.ProfitDeltaQualityValidator = original_delta
        session_mod.BookDepthSourceDiagnostics = original_book_diag
        session_mod.BookDepthQualityValidator = original_book_validator
        session_mod.OrderFlowObservationalContextBuilder = original_builder


def run():
    assert context_ready(_ctx()) is False
    assert context_ready(_ctx('SIDEWAYS', True, 'BUY')) is True
    assert context_ready(_ctx('UP', True, 'SELL')) is True

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

    _test_readiness_separation()

    print('PROFIT_RTD_RC54_3_2=OK')


if __name__ == '__main__':
    run()
