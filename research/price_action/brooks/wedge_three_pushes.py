"""BROOKS_WEDGE_THREE_PUSHES_V1 - detector/classificador observacional de pesquisa.

O detector opera somente sobre candles fechados e identifica tres pushes por
extremos locais na mesma direcao. O classificador exige depois uma reversao
explicita contra os pushes e confirmacao estrutural/resposta. Nada aqui altera
o nucleo operacional.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SETUP_NAME = "BROOKS_WEDGE_THREE_PUSHES_V1"


@dataclass(frozen=True, slots=True)
class ThreePushesDetection:
    detected: bool = False
    push_direction: str = "NONE"
    push_indices: tuple[int, int, int] | tuple = ()
    push_prices: tuple[float, float, float] | tuple = ()
    narrowing: bool = False


class BrooksThreePushesDetector:
    """Detecta tres pushes usando somente candles fechados."""

    @staticmethod
    def _local_high(candles, i):
        return candles[i].high > candles[i - 1].high and candles[i].high >= candles[i + 1].high

    @staticmethod
    def _local_low(candles, i):
        return candles[i].low < candles[i - 1].low and candles[i].low <= candles[i + 1].low

    @classmethod
    def analyze(cls, candles):
        closed = list(candles[:-1])
        if len(closed) < 7:
            return ThreePushesDetection()

        highs = [(i, float(closed[i].high)) for i in range(1, len(closed) - 1) if cls._local_high(closed, i)]
        lows = [(i, float(closed[i].low)) for i in range(1, len(closed) - 1) if cls._local_low(closed, i)]

        up = cls._three_pushes(highs, "UP")
        down = cls._three_pushes(lows, "DOWN")

        if up.detected and down.detected:
            if up.push_indices[-1] > down.push_indices[-1]:
                return up
            if down.push_indices[-1] > up.push_indices[-1]:
                return down
            return ThreePushesDetection()
        if up.detected:
            return up
        if down.detected:
            return down
        return ThreePushesDetection()

    @staticmethod
    def _three_pushes(points, direction):
        if len(points) < 3:
            return ThreePushesDetection()
        selected = points[-3:]
        indices = tuple(item[0] for item in selected)
        prices = tuple(item[1] for item in selected)

        if direction == "UP":
            monotonic = prices[0] < prices[1] < prices[2]
            d1 = prices[1] - prices[0]
            d2 = prices[2] - prices[1]
        else:
            monotonic = prices[0] > prices[1] > prices[2]
            d1 = prices[0] - prices[1]
            d2 = prices[1] - prices[2]

        if not monotonic:
            return ThreePushesDetection()
        return ThreePushesDetection(
            detected=True,
            push_direction=direction,
            push_indices=indices,
            push_prices=prices,
            narrowing=(d2 <= d1),
        )


@dataclass(frozen=True, slots=True)
class WedgeThreePushesObservation:
    three_pushes_detected: bool = False
    push_direction: str = "NONE"
    reversal_candidate: bool = False
    reversal_direction: str = "NONE"
    reversal_quality: str = "NONE"
    structural_change: bool = False
    structural_change_direction: str = "NONE"
    response_detected: bool = False
    structural_invalidation: bool = False
    candle_id: str | None = None


@dataclass(slots=True)
class WedgeThreePushesResearchResult:
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


class BrooksWedgeThreePushesResearch:
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

    def evaluate(self, obs: WedgeThreePushesObservation) -> WedgeThreePushesResearchResult:
        result = WedgeThreePushesResearchResult(candle_id=obs.candle_id)
        push = self._direction(obs.push_direction)
        reversal = self._direction(obs.reversal_direction)
        structural = self._direction(obs.structural_change_direction)
        quality = str(obs.reversal_quality or "NONE").upper()

        if push == "NONE":
            result.reasons.append("PUSH_DIRECTION_NOT_ELIGIBLE")
            return result
        expected = "SELL" if push == "BUY" else "BUY"
        result.direction = expected

        if obs.structural_invalidation:
            result.invalidated = True
            result.reasons.append("WEDGE_THREE_PUSHES_INVALIDATED")
            return result

        missing = []
        if not obs.three_pushes_detected:
            missing.append("THREE_PUSHES_NOT_CONFIRMED")
        if not obs.reversal_candidate:
            missing.append("REVERSAL_CANDIDATE_NOT_CONFIRMED")
        if reversal != expected:
            missing.append("REVERSAL_DIRECTION_NOT_OPPOSITE_PUSHES")
        if quality not in self.ACCEPTED_QUALITIES:
            missing.append("REVERSAL_QUALITY_NOT_ELIGIBLE")
        if not obs.structural_change:
            missing.append("STRUCTURAL_CHANGE_NOT_CONFIRMED")
        if structural != expected:
            missing.append("STRUCTURAL_CHANGE_DIRECTION_NOT_ALIGNED")
        if not obs.response_detected:
            missing.append("REVERSAL_RESPONSE_NOT_CONFIRMED")

        if missing:
            result.reasons.extend(missing)
            return result

        result.matched = True
        result.sequence_complete = True
        result.reasons.append("WEDGE_THREE_PUSHES_SEQUENCE_OBSERVED")
        return result
