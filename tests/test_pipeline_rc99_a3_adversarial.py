from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from external_context.external_market_state import ExternalMarketState


class HostileExternalService:
    def __init__(self):
        self.state = ExternalMarketState()
        self.state.valid = True
        self.state.risk_on_off = "RISK_ON"
        self.state.global_bias = "BULLISH"
        self.state.confidence = 0.85

    def snapshot(self):
        return self.state


def test_rc99_external_service_cannot_mutate_official_snapshot():
    service = HostileExternalService()

    pipeline = AnalysisPipeline(
        external_context_service=service
    )

    context = AnalysisContext()
    pipeline.context = context

    pipeline._refresh_external_context()

    assert context.external_valid is True
    assert context.external_risk == "RISK_ON"
    assert context.external_bias == "BULLISH"

    service.state.risk_on_off = "RISK_OFF"
    service.state.global_bias = "BEARISH"
    service.state.confidence = 0.05

    assert context.external_risk == "RISK_ON", (
        "RC99_VULNERABILIDADE_RISK_MUTADO"
    )

    assert context.external_bias == "BULLISH", (
        "RC99_VULNERABILIDADE_BIAS_MUTADO"
    )

    assert context.external_confidence == 0.85, (
        "RC99_VULNERABILIDADE_CONFIANCA_MUTADA"
    )
