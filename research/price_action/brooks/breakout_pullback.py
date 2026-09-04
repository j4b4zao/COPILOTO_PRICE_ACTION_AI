"""
research/price_action/brooks/breakout_pullback.py

BROOKS_BREAKOUT_PULLBACK_V1

Formalizacao observacional de uma hipotese de Price Action inspirada no
conceito de breakout pullback descrito por Al Brooks.

IMPORTANTE
---------
Este modulo pertence exclusivamente a camada de pesquisa.
Ele NAO gera ordem, NAO altera score e NAO influencia Risk, Decision ou Alert.

A responsabilidade deste arquivo e somente classificar uma sequencia ja
observada pelos demais componentes do projeto:

    tendencia -> breakout -> pullback -> rejeicao -> retomada

Nenhum detector operacional e chamado aqui. Os fatos entram como dados.
"""

from dataclasses import dataclass, field

from enums.trend import Trend


SETUP_NAME = "BROOKS_BREAKOUT_PULLBACK_V1"


@dataclass(frozen=True, slots=True)
class BreakoutPullbackObservation:
    """Fatos observados usados pela hipotese de pesquisa.

    Todos os campos sao descritivos. O objeto nao deve executar logica de
    mercado nem consultar engines operacionais.
    """

    trend: Trend
    breakout_direction: str = "NONE"
    breakout_detected: bool = False
    pullback_detected: bool = False
    rejection_detected: bool = False
    resumption_detected: bool = False
    structural_level_lost: bool = False
    candle_id: str | None = None


@dataclass(slots=True)
class BreakoutPullbackResearchResult:
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


class BrooksBreakoutPullbackResearch:
    """Classificador puro da hipotese BROOKS_BREAKOUT_PULLBACK_V1."""

    NAME = SETUP_NAME
    VERSION = "V1-RESEARCH-ONLY"

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
        observation: BreakoutPullbackObservation,
    ) -> BreakoutPullbackResearchResult:
        result = BreakoutPullbackResearchResult(
            candle_id=observation.candle_id,
        )

        breakout_direction = self._normalize_direction(
            observation.breakout_direction
        )

        expected_direction = "NONE"

        if observation.trend == Trend.UP:
            expected_direction = "BUY"
        elif observation.trend == Trend.DOWN:
            expected_direction = "SELL"
        else:
            result.reasons.append(
                "TREND_CONTEXT_NOT_ELIGIBLE"
            )
            return result

        if breakout_direction != expected_direction:
            result.reasons.append(
                "BREAKOUT_DIRECTION_NOT_ALIGNED_WITH_TREND"
            )
            return result

        result.context_valid = True
        result.direction = expected_direction

        if observation.structural_level_lost:
            result.invalidated = True
            result.reasons.append(
                "BREAKOUT_STRUCTURE_INVALIDATED"
            )
            return result

        missing_steps: list[str] = []

        if not observation.breakout_detected:
            missing_steps.append("BREAKOUT_NOT_CONFIRMED")

        if not observation.pullback_detected:
            missing_steps.append("PULLBACK_NOT_CONFIRMED")

        if not observation.rejection_detected:
            missing_steps.append("REJECTION_NOT_CONFIRMED")

        if not observation.resumption_detected:
            missing_steps.append("RESUMPTION_NOT_CONFIRMED")

        if missing_steps:
            result.reasons.extend(missing_steps)
            return result

        result.sequence_complete = True
        result.matched = True
        result.reasons.append(
            "BREAKOUT_PULLBACK_SEQUENCE_OBSERVED"
        )

        return result
