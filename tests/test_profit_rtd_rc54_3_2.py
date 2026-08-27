from types import SimpleNamespace

from tools.profit_rtd_rc54_3_2_warm_history_gate import context_ready, warm_history


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

    print('PROFIT_RTD_RC54_3_2=OK')


if __name__ == '__main__':
    run()
