"""RC9.6-A3 — testes adversariais de integridade (offline, sem ordens).

Estes testes expressam contratos de seguranca desejados. Falhas sao evidencias
para investigacao, nao autorizacao para corrigir producao automaticamente.
"""

import pytest

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.event_bus import EventBus
from core.event_types import EventType
from risk.risk_manager import RiskManager


class _Engine:
    ENABLED = True

    def __init__(self, callback):
        self.callback = callback

    def executar(self, context):
        self.callback(context)
        return context


def _pipeline(event_bus=None):
    pipeline = AnalysisPipeline(event_bus=event_bus)
    # Nao executar recorders, psicologia ou conectores reais nestes testes.
    for name in (
        'book_diagnostics_replay', 'score_regime_mtf_ab',
        'score_external_context_ab', 'score_order_flow_ab',
        'score_order_flow_structure_ab', 'score_book_depth_ab',
        'score_microstructure_eligibility_ab', 'microstructure_confluence_replay',
        'microstructure_eligibility_replay',
    ):
        setattr(getattr(pipeline, name), 'record', lambda context: None)
    pipeline._refresh_trader_psychology = lambda: None
    return pipeline


def test_rc96_control_clean_cycle_without_engines():
    pipeline = _pipeline()
    pipeline.engines = []
    context = AnalysisContext()
    context.decision.valid = True
    context.decision.action = 'BUY'
    context.alert.valid = True
    context.alert.action = 'BUY'
    assert pipeline.executar(context) is context
    assert context.decision.valid is False
    assert context.alert.valid is False


def test_rc96_event_listener_cannot_modify_risk_seen_by_next_engine():
    bus = EventBus()
    pipeline = _pipeline(event_bus=bus)
    risk_engine = RiskManager()

    def produce_risk(context):
        context.risk.valid = True
        context.risk.approved = True
        context.risk.entry_price = 100.0

    risk_engine.executar = produce_risk
    observed = []
    probe = _Engine(lambda context: observed.append(context.risk.entry_price))
    pipeline.engines = [risk_engine, probe]

    def hostile_listener(event):
        event.data.risk.entry_price = 999.0

    bus.subscribe(EventType.RISK_UPDATED, hostile_listener)
    pipeline.executar(AnalysisContext())
    assert observed == [100.0], 'EVENTBUS_MUTOU_RISCO_ENTRE_ENGINES'


def test_rc96_engine_exception_leaves_no_valid_decision_or_alert():
    pipeline = _pipeline()

    def failing_engine(context):
        context.decision.valid = True
        context.decision.action = 'BUY'
        context.alert.valid = True
        context.alert.action = 'BUY'
        raise RuntimeError('RC96_FALHA_CONTROLADA')

    pipeline.engines = [_Engine(failing_engine)]
    context = AnalysisContext()
    try:
        pipeline.executar(context)
    except RuntimeError as exc:
        assert str(exc) == 'RC96_FALHA_CONTROLADA'
    # A politica de propagacao da excecao e livre; o estado nao pode aprovar.
    assert context.decision.valid is False, 'DECISAO_PARCIAL_PERMANECE_VALIDA'
    assert context.alert.valid is False, 'ALERTA_PARCIAL_PERMANECE_VALIDO'


def test_rc96_loop_completed_listener_cannot_forge_approved_alert():
    bus = EventBus()
    pipeline = _pipeline(event_bus=bus)
    pipeline.engines = []

    def hostile_listener(event):
        event.data.decision.valid = True
        event.data.decision.action = 'BUY'
        event.data.alert.valid = True
        event.data.alert.action = 'BUY'

    bus.subscribe(EventType.LOOP_COMPLETED, hostile_listener)
    context = pipeline.executar(AnalysisContext())
    assert context.decision.valid is False, 'LOOP_LISTENER_FORJOU_DECISAO'
    assert context.alert.valid is False, 'LOOP_LISTENER_FORJOU_ALERTA'
