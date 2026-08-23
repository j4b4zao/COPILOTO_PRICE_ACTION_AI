from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from external_context.external_market_state import ExternalMarketState


class _Service:
    def __init__(self, state=None, error=None):
        self.state = state
        self.error = error
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.state


def _state(risk="RISK_ON", bias="BULLISH", confidence=0.75):
    state = ExternalMarketState()
    state.valid = True
    state.risk_on_off = risk
    state.global_bias = bias
    state.confidence = confidence
    state.timestamp = "2026-08-23T14:00:00-04:00"
    return state


def test_analysis_context_defaults_external_bridge_to_neutral():
    context = AnalysisContext()
    assert context.external_valid is False
    assert context.external_risk == "NEUTRAL"
    assert context.external_bias == "NEUTRAL"
    assert context.external_confidence == 0.0


def test_analysis_context_exposes_external_snapshot_without_duplication():
    context = AnalysisContext()
    context.external_market = _state("RISK_OFF", "BEARISH", 1.0)
    assert context.external_valid is True
    assert context.external_risk == "RISK_OFF"
    assert context.external_bias == "BEARISH"
    assert context.external_confidence == 1.0


def test_invalid_external_snapshot_never_exposes_confidence():
    context = AnalysisContext()
    context.external_market.confidence = 0.9
    assert context.external_confidence == 0.0


def test_clear_results_preserves_external_snapshot():
    context = AnalysisContext()
    state = _state()
    context.external_market = state
    context.clear_results()
    assert context.external_market is state
    assert context.external_risk == "RISK_ON"


def test_reset_clears_external_snapshot():
    context = AnalysisContext()
    context.external_market = _state()
    context.reset()
    assert context.external_valid is False
    assert context.external_risk == "NEUTRAL"
    assert context.external_confidence == 0.0


def test_pipeline_rejects_external_service_without_snapshot():
    try:
        AnalysisPipeline(external_context_service=object())
    except TypeError as exc:
        assert "snapshot" in str(exc)
    else:
        raise AssertionError("TypeError esperado")


def test_pipeline_refreshes_external_context_from_service():
    state = _state("RISK_OFF", "BEARISH", 0.75)
    service = _Service(state=state)
    pipeline = AnalysisPipeline(external_context_service=service)
    context = AnalysisContext()
    pipeline.context = context
    pipeline._refresh_external_context()
    assert service.calls == 1
    assert context.external_market is state
    assert context.external_risk == "RISK_OFF"


def test_pipeline_without_service_preserves_existing_external_state():
    pipeline = AnalysisPipeline()
    context = AnalysisContext()
    state = _state()
    context.external_market = state
    pipeline.context = context
    pipeline._refresh_external_context()
    assert context.external_market is state


def test_external_service_failure_is_fail_safe():
    service = _Service(error=RuntimeError("offline"))
    pipeline = AnalysisPipeline(external_context_service=service)
    context = AnalysisContext()
    context.external_market = _state()
    pipeline.context = context
    pipeline._refresh_external_context()
    assert context.external_valid is False
    assert context.external_risk == "NEUTRAL"
    assert context.external_confidence == 0.0
    assert any("RuntimeError" in reason for reason in context.external_market.reasons)


def test_invalid_service_return_is_fail_safe_and_non_operational():
    service = _Service(state={"risk": "RISK_ON"})
    pipeline = AnalysisPipeline(external_context_service=service)
    context = AnalysisContext()
    pipeline.context = context
    before_direction = context.decision.direction
    pipeline._refresh_external_context()
    assert context.external_valid is False
    assert context.decision.direction == before_direction
    assert any("estado inválido" in reason for reason in context.external_market.reasons)
