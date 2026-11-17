"""RC9.8-A3 — testes adversariais offline da camada TraderPsychology.

Nao altera codigo de producao. Antes da correcao, testes de mutacao
podem falhar intencionalmente: isto documenta a vulnerabilidade.
"""
import pytest

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.event_types import EventType
from psychology.trader_psychology_state import TraderPsychologyState


RECORDER_NAMES = (
    "book_diagnostics_replay", "score_regime_mtf_ab",
    "score_external_context_ab", "score_order_flow_ab",
    "score_order_flow_structure_ab", "score_book_depth_ab",
    "score_microstructure_eligibility_ab", "microstructure_confluence_replay",
    "microstructure_eligibility_replay",
)


class _Engine:
    ENABLED = True

    def executar(self, context):
        context.score.total = 91.0
        context.risk.valid = True
        context.risk.approved = True
        context.risk.entry_price = 100.0
        context.decision.valid = True
        context.decision.action = "BUY"
        context.alert.valid = True
        context.alert.action = "BUY"


class _Provider:
    def __init__(self, callback=None):
        self.callback = callback

    def snapshot(self, context):
        if self.callback is not None:
            self.callback(context)
        return TraderPsychologyState(trades_today=2)


class _Bridge:
    def __init__(self, callback=None):
        self.callback = callback

    def attach(self, context, result):
        if self.callback is not None:
            self.callback(context)
        context.trader_psychology = result


class _Bus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def _pipeline(provider=None, bridge=None, bus=None):
    pipeline = AnalysisPipeline(
        psychology_state_provider=provider,
        psychology_context_bridge=bridge,
        event_bus=bus,
    )
    pipeline.engines = [_Engine()]
    for name in RECORDER_NAMES:
        getattr(pipeline, name).record = lambda context: None
    return pipeline


def _assert_operational_unchanged(context):
    assert context.score.total == 91.0, "RC98_SCORE_MUTADO"
    assert context.risk.valid is True, "RC98_RISCO_INVALIDADO"
    assert context.risk.approved is True, "RC98_APROVACAO_MUTADA"
    assert context.risk.entry_price == 100.0, "RC98_PRECO_MUTADO"
    assert context.decision.valid is True, "RC98_DECISAO_INVALIDADA"
    assert context.decision.action == "BUY", "RC98_DECISAO_MUTADA"
    assert context.alert.valid is True, "RC98_ALERTA_INVALIDADO"
    assert context.alert.action == "BUY", "RC98_ALERTA_MUTADO"


def _mutate_decision(context):
    context.decision.action = "SELL"
    context.alert.action = "SELL"


def _mutate_risk(context):
    context.risk.valid = False
    context.risk.approved = False
    context.risk.entry_price = 999.0


def _mutate_then_raise(context):
    _mutate_decision(context)
    _mutate_risk(context)
    raise RuntimeError("RC98_HOSTILE_PSYCHOLOGY")


@pytest.mark.parametrize("mutation", [_mutate_decision, _mutate_risk], ids=["decision", "risk"])
def test_rc98_provider_cannot_mutate_official_results(mutation):
    context = _pipeline(provider=_Provider(mutation)).executar(AnalysisContext())
    _assert_operational_unchanged(context)


def test_rc98_provider_exception_after_mutation_cannot_corrupt_results():
    context = _pipeline(provider=_Provider(_mutate_then_raise)).executar(AnalysisContext())
    _assert_operational_unchanged(context)
    assert context.trader_psychology is None


@pytest.mark.parametrize("mutation", [_mutate_decision, _mutate_risk], ids=["decision", "risk"])
def test_rc98_bridge_cannot_mutate_official_results(mutation):
    context = _pipeline(
        provider=_Provider(), bridge=_Bridge(mutation)
    ).executar(AnalysisContext())
    _assert_operational_unchanged(context)


def test_rc98_bridge_exception_after_mutation_cannot_corrupt_results():
    context = _pipeline(
        provider=_Provider(), bridge=_Bridge(_mutate_then_raise)
    ).executar(AnalysisContext())
    _assert_operational_unchanged(context)
    assert context.trader_psychology is None


def test_rc98_loop_completed_cannot_publish_corrupted_operational_results():
    bus = _Bus()
    context = _pipeline(
        provider=_Provider(_mutate_decision), bus=bus
    ).executar(AnalysisContext())
    _assert_operational_unchanged(context)
    events = [e for e in bus.events if e.type == EventType.LOOP_COMPLETED]
    assert len(events) == 1
    assert events[0].data is not context
    _assert_operational_unchanged(events[0].data)


def test_rc98_healthy_provider_preserves_decision_and_attaches_psychology():
    context = _pipeline(provider=_Provider()).executar(AnalysisContext())
    _assert_operational_unchanged(context)
    assert context.trader_psychology is not None


def test_rc98_unavailable_provider_preserves_operational_results():
    def unavailable(context):
        raise RuntimeError("RC98_PROVIDER_UNAVAILABLE")

    context = _pipeline(provider=_Provider(unavailable)).executar(AnalysisContext())
    _assert_operational_unchanged(context)
    assert context.trader_psychology is None
