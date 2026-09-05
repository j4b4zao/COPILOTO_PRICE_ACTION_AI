"""BROOKS_TRADING_RANGE_REVERSAL_V1 - classificador observacional de pesquisa.

Usa a semantica ja existente em TradingRangePlaybookDynamics: range valido,
localizacao LOW/HIGH, H2/L2 e risco de failed breakout. O classificador exige
um extremo de range elegivel e reversao explicita para dentro do range.

Nao altera Score, Risk, Decision, Alert ou execucao.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SETUP_NAME = "BROOKS_TRADING_RANGE_REVERSAL_V1"


@dataclass(frozen=True, slots=True)
class TradingRangeReversalObservation:
    range_valid: bool = False
    zone: str = "MIDDLE"
    setup_direction: str = "NONE"
    h2_near_low: bool = False
    l2_near_high: bool = False
    failed_breakout_risk: bool = False
    reversal_candidate: bool = False
    reversal_direction: str = "NONE"
    reversal_quality: str = "NONE"
    response_detected: bool = False
    range_invalidated: bool = False
    candle_id: str | None = None


@dataclass(slots=True)
class TradingRangeReversalResearchResult:
    setup_name: str = SETUP_NAME
    matched: bool = False
    direction: str = "NONE"
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


class BrooksTradingRangeReversalResearch:
    NAME = SETUP_NAME
    VERSION = "V1-RESEARCH-ONLY"
    ACCEPTED_QUALITIES = {"MODERATE", "STRONG"}

    @staticmethod
    def _direction(value):
        value = str(value or "NONE").strip().upper()
        if value in {"UP", "BUY", "BULL", "BULLISH"}:
            return "BUY"
        if value in {"DOWN", "SELL", "BEAR", "BEARISH"}:
            return "SELL"
        return "NONE"

    def evaluate(self, obs: TradingRangeReversalObservation) -> TradingRangeReversalResearchResult:
        result = TradingRangeReversalResearchResult(candle_id=obs.candle_id)
        zone = str(obs.zone or "MIDDLE").strip().upper()
        setup_direction = self._direction(obs.setup_direction)
        reversal_direction = self._direction(obs.reversal_direction)
        quality = str(obs.reversal_quality or "NONE").strip().upper()

        if obs.range_invalidated:
            result.invalidated = True
            result.reasons.append("TRADING_RANGE_INVALIDATED")
            return result

        if not obs.range_valid:
            result.reasons.append("TRADING_RANGE_NOT_CONFIRMED")
            return result

        if zone not in {"LOW", "HIGH"}:
            result.reasons.append("RANGE_EDGE_NOT_ELIGIBLE")
            return result

        expected = "BUY" if zone == "LOW" else "SELL"
        result.direction = expected

        missing = []
        edge_signal = obs.h2_near_low if expected == "BUY" else obs.l2_near_high
        if setup_direction not in {"NONE", expected}:
            missing.append("PLAYBOOK_DIRECTION_NOT_ALIGNED")
        if not (edge_signal or obs.failed_breakout_risk):
            missing.append("RANGE_EDGE_REVERSAL_SIGNAL_NOT_CONFIRMED")
        if not obs.reversal_candidate:
            missing.append("REVERSAL_CANDIDATE_NOT_CONFIRMED")
        if reversal_direction != expected:
            missing.append("REVERSAL_DIRECTION_NOT_INTO_RANGE")
        if quality not in self.ACCEPTED_QUALITIES:
            missing.append("REVERSAL_QUALITY_NOT_ELIGIBLE")
        if not obs.response_detected:
            missing.append("REVERSAL_RESPONSE_NOT_CONFIRMED")

        if missing:
            result.reasons.extend(missing)
            return result

        result.matched = True
        result.sequence_complete = True
        result.reasons.append("TRADING_RANGE_REVERSAL_SEQUENCE_OBSERVED")
        return result
