"""
research/price_action/brooks/failed_breakout.py

BROOKS_FAILED_BREAKOUT_V1

Formalizacao observacional de uma hipotese de failed breakout inspirada em
Al Brooks. Este modulo pertence somente a camada de pesquisa.

A sequencia observacional minima e:

    breakout explicito -> falha explicita atraves do nivel -> resposta oposta

IMPORTANTE
---------
- nao gera ordens;
- nao altera Score, Risk, Decision ou Alert;
- nao faz claim preditivo;
- nao infere falha por retorno futuro: ela precisa ser produzida explicitamente.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SETUP_NAME = "BROOKS_FAILED_BREAKOUT_V1"


@dataclass(frozen=True, slots=True)
class FailedBreakoutObservation:
    breakout_direction: str = "NONE"
    breakout_detected: bool = False
    failure_detected: bool = False
    failure_direction: str = "NONE"
    opposite_response_detected: bool = False
    structural_invalidation: bool = False
    candle_id: str | None = None


@dataclass(slots=True)
class FailedBreakoutResearchResult:
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


class BrooksFailedBreakoutResearch:
    NAME = SETUP_NAME
    VERSION = "V1-RESEARCH-ONLY"

    @staticmethod
    def _normalize_direction(value: str) -> str:
        value = str(value or "NONE").strip().upper()
        if value in {"BUY", "UP", "BULL", "BULLISH"}:
            return "BUY"
        if value in {"SELL", "DOWN", "BEAR", "BEARISH"}:
            return "SELL"
        return "NONE"

    def evaluate(self, observation: FailedBreakoutObservation) -> FailedBreakoutResearchResult:
        result = FailedBreakoutResearchResult(candle_id=observation.candle_id)

        breakout_direction = self._normalize_direction(observation.breakout_direction)
        failure_direction = self._normalize_direction(observation.failure_direction)

        if breakout_direction == "NONE":
            result.reasons.append("BREAKOUT_DIRECTION_NOT_ELIGIBLE")
            return result

        expected_response = "SELL" if breakout_direction == "BUY" else "BUY"
        result.direction = expected_response

        if observation.structural_invalidation:
            result.invalidated = True
            result.reasons.append("FAILED_BREAKOUT_STRUCTURE_INVALIDATED")
            return result

        missing: list[str] = []
        if not observation.breakout_detected:
            missing.append("BREAKOUT_NOT_CONFIRMED")
        if not observation.failure_detected:
            missing.append("BREAKOUT_FAILURE_NOT_CONFIRMED")
        if failure_direction != expected_response:
            missing.append("FAILURE_DIRECTION_NOT_OPPOSITE_BREAKOUT")
        if not observation.opposite_response_detected:
            missing.append("OPPOSITE_RESPONSE_NOT_CONFIRMED")

        if missing:
            result.reasons.extend(missing)
            return result

        result.sequence_complete = True
        result.matched = True
        result.reasons.append("FAILED_BREAKOUT_SEQUENCE_OBSERVED")
        return result
