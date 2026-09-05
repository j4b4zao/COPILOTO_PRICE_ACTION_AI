"""BROOKS_MAJOR_TREND_REVERSAL_V1 - classificador observacional de pesquisa.

Formaliza somente uma sequencia minima suportada pelos sinais ja produzidos pelo
PriceAction: tendencia previa, barra de reversao contra a tendencia, mudanca
estrutural explicita e resposta na nova direcao.

Nao gera ordens e nao influencia Score, Risk, Decision, Alert ou execucao.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SETUP_NAME = "BROOKS_MAJOR_TREND_REVERSAL_V1"


@dataclass(frozen=True, slots=True)
class MajorTrendReversalObservation:
    prior_trend: str = "NONE"
    reversal_candidate: bool = False
    reversal_direction: str = "NONE"
    reversal_quality: str = "NONE"
    reversal_context: str = "NEUTRAL"
    structural_change: bool = False
    structural_change_direction: str = "NONE"
    response_detected: bool = False
    structural_invalidation: bool = False
    candle_id: str | None = None


@dataclass(slots=True)
class MajorTrendReversalResearchResult:
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


class BrooksMajorTrendReversalResearch:
    NAME = SETUP_NAME
    VERSION = "V1-RESEARCH-ONLY"
    ACCEPTED_QUALITIES = {"MODERATE", "STRONG"}

    @staticmethod
    def _direction(value: str) -> str:
        value = str(value or "NONE").strip().upper()
        if value in {"BUY", "UP", "BULL", "BULLISH"}:
            return "BUY"
        if value in {"SELL", "DOWN", "BEAR", "BEARISH"}:
            return "SELL"
        return "NONE"

    def evaluate(self, obs: MajorTrendReversalObservation) -> MajorTrendReversalResearchResult:
        result = MajorTrendReversalResearchResult(candle_id=obs.candle_id)
        trend = self._direction(obs.prior_trend)
        reversal = self._direction(obs.reversal_direction)
        structural = self._direction(obs.structural_change_direction)
        quality = str(obs.reversal_quality or "NONE").upper()
        context = str(obs.reversal_context or "NEUTRAL").upper()

        if trend == "NONE":
            result.reasons.append("PRIOR_TREND_NOT_ELIGIBLE")
            return result

        expected = "SELL" if trend == "BUY" else "BUY"
        result.direction = expected
        result.context_valid = context == "COUNTER_TREND"

        if obs.structural_invalidation:
            result.invalidated = True
            result.reasons.append("MAJOR_TREND_REVERSAL_INVALIDATED")
            return result

        missing = []
        if not obs.reversal_candidate:
            missing.append("REVERSAL_CANDIDATE_NOT_CONFIRMED")
        if reversal != expected:
            missing.append("REVERSAL_DIRECTION_NOT_COUNTER_TREND")
        if quality not in self.ACCEPTED_QUALITIES:
            missing.append("REVERSAL_QUALITY_NOT_ELIGIBLE")
        if context != "COUNTER_TREND":
            missing.append("REVERSAL_CONTEXT_NOT_COUNTER_TREND")
        if not obs.structural_change:
            missing.append("STRUCTURAL_CHANGE_NOT_CONFIRMED")
        if structural != expected:
            missing.append("STRUCTURAL_CHANGE_DIRECTION_NOT_ALIGNED")
        if not obs.response_detected:
            missing.append("REVERSAL_RESPONSE_NOT_CONFIRMED")

        if missing:
            result.reasons.extend(missing)
            return result

        result.sequence_complete = True
        result.matched = True
        result.reasons.append("MAJOR_TREND_REVERSAL_SEQUENCE_OBSERVED")
        return result
