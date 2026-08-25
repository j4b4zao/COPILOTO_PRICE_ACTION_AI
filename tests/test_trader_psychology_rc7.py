"""Testes offline da integração Pipeline + Psicologia RC7."""

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.event_types import EventType
from psychology import (
    TraderPsychologyContextBridge,
    TraderPsychologyRuntime,
    TraderPsychologyState,
)


RECORDER_NAMES = (
    "book_diagnostics_replay",
    "score_regime_mtf_ab",
    "score_external_context_ab",
    "score_order_flow_ab",
    "score_order_flow_structure_ab",
    "score_book_depth_ab",
    "score_microstructure_eligibility_ab",
    "microstructure_confluence_replay",
    "microstructure_eligibility_replay",
)


class OperationalEngine:
    ENABLED = True

    def __init__(self, trace):
        self.trace = trace

    def executar(self, context):
        self.trace.append("decision")
        context.score.total = 91.0
        context.score.grade = "A"
        context.decision.direction = "BUY"


class Recorder:
    def __init__(self, trace, name):
        self.trace = trace
        self.name = name

    def record(self, context):
        assert context.trader_psychology is None
        self.trace.append(self.name)


class StateProvider:
    def __init__(self, trace, state=None):
        self.trace = trace
        self.state = state or TraderPsychologyState(trades_today=6)

    def snapshot(self, context):
        assert context.score.total == 91.0
        assert context.decision.direction == "BUY"
        self.trace.append("provider")
        return self.state


class EventBus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


class RaisesProvider:
    def snapshot(self, context):
        raise RuntimeError("telemetria indisponível")


class InvalidProvider:
    def snapshot(self, context):
        return {"trades_today": 99}


class RaisesRuntime:
    def process(self, state):
        raise RuntimeError("runtime indisponível")


class RaisesBridge:
    def attach(self, context, result):
        raise RuntimeError("bridge indisponível")


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def build_pipeline(
    *,
    provider=None,
    runtime=None,
    bridge=None,
    event_bus=None,
):
    trace = []
    pipeline = object.__new__(AnalysisPipeline)
    pipeline.event_bus = event_bus
    pipeline.external_context_service = None
    pipeline.book_depth_service = None
    pipeline.psychology_state_provider = provider
    pipeline.psychology_runtime = runtime or TraderPsychologyRuntime()
    pipeline.psychology_context_bridge = (
        bridge or TraderPsychologyContextBridge()
    )
    pipeline.context = AnalysisContext()
    pipeline.engines = [OperationalEngine(trace)]
    for name in RECORDER_NAMES:
        setattr(pipeline, name, Recorder(trace, name))
    return pipeline, trace


def teste_sem_provider_pipeline_permanece_desativado():
    pipeline, _ = build_pipeline()
    context = pipeline.executar(AnalysisContext())
    assert context.trader_psychology is None


def teste_pipeline_anexa_snapshot_psicologico():
    trace = []
    provider = StateProvider(
        trace,
        TraderPsychologyState(consecutive_losses=3),
    )
    pipeline, pipeline_trace = build_pipeline(provider=provider)
    provider.trace = pipeline_trace
    context = pipeline.executar(AnalysisContext())
    assert context.trader_psychology is not None
    assert context.trader_psychology.status == "ATTENTION"


def teste_provider_executa_depois_do_decision_engine():
    pipeline, trace = build_pipeline()
    pipeline.psychology_state_provider = StateProvider(trace)
    pipeline.executar(AnalysisContext())
    assert trace.index("decision") < trace.index("provider")


def teste_provider_executa_depois_de_todos_os_replays():
    pipeline, trace = build_pipeline()
    pipeline.psychology_state_provider = StateProvider(trace)
    pipeline.executar(AnalysisContext())
    assert trace[-1] == "provider"
    assert all(trace.index(name) < trace.index("provider") for name in RECORDER_NAMES)


def teste_integracao_preserva_score_e_decision():
    pipeline, trace = build_pipeline()
    pipeline.psychology_state_provider = StateProvider(trace)
    context = pipeline.executar(AnalysisContext())
    assert context.score.total == 91.0
    assert context.score.grade == "A"
    assert context.decision.direction == "BUY"


def teste_integracao_preserva_identidades_operacionais():
    context = AnalysisContext()
    identities = {
        name: id(getattr(context, name))
        for name in ("strategy", "score", "risk", "decision", "alert")
    }
    pipeline, trace = build_pipeline()
    pipeline.psychology_state_provider = StateProvider(trace)
    returned = pipeline.executar(context)
    assert all(
        id(getattr(returned, name)) == identity
        for name, identity in identities.items()
    )


def teste_falha_do_provider_e_isolada():
    pipeline, _ = build_pipeline(provider=RaisesProvider())
    context = pipeline.executar(AnalysisContext())
    assert context.trader_psychology is None
    assert context.score.total == 91.0
    assert context.decision.direction == "BUY"


def teste_estado_invalido_e_ignorado():
    pipeline, _ = build_pipeline(provider=InvalidProvider())
    context = pipeline.executar(AnalysisContext())
    assert context.trader_psychology is None
    assert context.score.total == 91.0


def teste_falha_do_runtime_e_isolada():
    pipeline, _ = build_pipeline(
        provider=StateProvider([]),
        runtime=RaisesRuntime(),
    )
    context = pipeline.executar(AnalysisContext())
    assert context.trader_psychology is None
    assert context.decision.direction == "BUY"


def teste_falha_da_bridge_e_isolada():
    pipeline, _ = build_pipeline(
        provider=StateProvider([]),
        bridge=RaisesBridge(),
    )
    context = pipeline.executar(AnalysisContext())
    assert context.trader_psychology is None
    assert context.score.total == 91.0


def teste_loop_completed_recebe_snapshot_pronto():
    bus = EventBus()
    pipeline, trace = build_pipeline(event_bus=bus)
    pipeline.psychology_state_provider = StateProvider(trace)
    context = pipeline.executar(AnalysisContext())
    loop_events = [
        event for event in bus.events
        if event.type == EventType.LOOP_COMPLETED
    ]
    assert len(loop_events) == 1
    assert loop_events[0].data is context
    assert loop_events[0].data.trader_psychology is not None


def teste_configuracoes_incompativeis_sao_rejeitadas():
    raises(
        TypeError,
        lambda: AnalysisPipeline(psychology_state_provider=object()),
    )
    raises(
        TypeError,
        lambda: AnalysisPipeline(psychology_runtime=object()),
    )
    raises(
        TypeError,
        lambda: AnalysisPipeline(psychology_context_bridge=object()),
    )


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC7 APROVADO")


if __name__ == "__main__":
    main()
