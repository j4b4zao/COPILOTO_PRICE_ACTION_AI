"""
research/price_action/brooks/trend_pullback.py

BROOKS_TREND_PULLBACK_V1

Formalizacao observacional de uma hipotese de Price Action inspirada no
conceito de pullback em tendencia descrito por Al Brooks.

IMPORTANTE
---------
Este modulo pertence exclusivamente a camada de pesquisa.
Ele NAO gera ordem, NAO altera score e NAO influencia Risk, Decision ou Alert.

A responsabilidade deste arquivo e somente classificar fatos ja observados:

    tendencia -> pullback inicial -> retomada

A leitura de maturidade do pullback pode ser alimentada por uma camada
separada, como FirstPullbackSequenceDynamics, mas este classificador nao
importa nem executa qualquer engine operacional.
"""

from dataclasses import dataclass, field

from enums.trend import Trend


SETUP_NAME = "BROOKS_TREND_PULLBACK_V1"


@dataclass(frozen=True, slots=True)
class TrendPullbackObservation:
    """Fatos descritivos usados pela hipotese de pesquisa."""

    trend: Trend
    pullback_detected: bool = False
    pullback_direction: str = "NONE"
    pullback_stage: str = "NO_SEQUENCE"
    pullback_stage_index: int = 0
    continuation_bias: bool = False
    reversal_risk: bool = False
    resumption_detected: bool = False
    structural_invalidation: bool = False
    trading_range_transition: bool = False
    candle_id: str | None = None


@dataclass(slots=True)
class TrendPullbackResearchResult:
    """Resultado exclusivamente observacional."""

    setup_name: str = SETUP_NAME
    matched: bool = False
    direction: str = "NONE"
    context_valid: bool = False
    sequence_complete: bool = False
    invalidated: bool = False
    candle_id: str | None = None
    reasons: list[str] = field(default_factory=list)

    research_only: bool = True
    observational_only: bool = True
    predictive_claim_allowed: bool = False
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    alert_influence_allowed: bool = False
    order_execution_allowed: bool = False


class BrooksTrendPullbackResearch:
    """Classificador puro da hipotese BROOKS_TREND_PULLBACK_V1."""

    NAME = SETUP_NAME
    VERSION = "V1-RESEARCH-ONLY"

    EARLY_PULLBACK_MAX_STAGE = 3

    @staticmethod
    def _normalize_direction(value: str) -> str:
        normalized = str(value or "NONE").strip().upper()
        if normalized in {"BUY", "UP", "BULL", "BULLISH"}:
            return "BUY"
        if normalized in {"SELL", "DOWN", "BEAR", "BEARISH"}:
            return "SELL"
        return "NONE"

    def evaluate(
        self,
        observation: TrendPullbackObservation,
    ) -> TrendPullbackResearchResult:
        result = TrendPullbackResearchResult(
            candle_id=observation.candle_id,
        )

        if observation.trend == Trend.UP:
            expected_direction = "BUY"
            expected_pullback_direction = "SELL"
        elif observation.trend == Trend.DOWN:
            expected_direction = "SELL"
            expected_pullback_direction = "BUY"
        else:
            result.reasons.append("TREND_CONTEXT_NOT_ELIGIBLE")
            return result

        result.context_valid = True
        result.direction = expected_direction

        if observation.structural_invalidation:
            result.invalidated = True
            result.reasons.append("TREND_STRUCTURE_INVALIDATED")
            return result

        if observation.trading_range_transition:
            result.invalidated = True
            result.reasons.append("TRADING_RANGE_TRANSITION")
            return result

        if observation.reversal_risk:
            result.invalidated = True
            result.reasons.append("PULLBACK_MATURITY_REVERSAL_RISK")
            return result

        pullback_direction = self._normalize_direction(
            observation.pullback_direction
        )

        missing_steps: list[str] = []

        if not observation.pullback_detected:
            missing_steps.append("PULLBACK_NOT_CONFIRMED")

        if pullback_direction != expected_pullback_direction:
            missing_steps.append("PULLBACK_DIRECTION_NOT_COUNTER_TREND")

        if not (1 <= int(observation.pullback_stage_index) <= self.EARLY_PULLBACK_MAX_STAGE):
            missing_steps.append("PULLBACK_STAGE_NOT_EARLY")

        if not observation.continuation_bias:
            missing_steps.append("CONTINUATION_BIAS_NOT_PRESENT")

        if not observation.resumption_detected:
            missing_steps.append("RESUMPTION_NOT_CONFIRMED")

        if missing_steps:
            result.reasons.extend(missing_steps)
            return result

        result.sequence_complete = True
        result.matched = True
        result.reasons.append("TREND_PULLBACK_SEQUENCE_OBSERVED")

        return result
