"""Contexto observacional consolidado de Order Flow (T&T + Book RTD)."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class OrderFlowObservationalContext:
    symbol: str = ""
    status: str = "NO_DATA"
    delta_status: str = "NO_DATA"
    book_status: str = "NO_DATA"
    recent_delta: float = 0.0
    recent_total_aggression: float = 0.0
    delta_dominance: float = 0.0
    delta_persistence: float = 0.0
    delta_acceleration: float = 0.0
    book_imbalance: float = 0.0
    book_spread: float = 0.0
    bid_levels: int = 0
    ask_levels: int = 0
    directional_alignment: str = "NEUTRAL"
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class OrderFlowObservationalContextBuilder:
    """Funde relatórios já validados de T&T/Delta e Book sem efeito operacional."""

    VERSION = "RC29-ORDER-FLOW-OBSERVATIONAL-CONTEXT"
    DELTA_ALIGN_THRESHOLD = 0.10
    BOOK_ALIGN_THRESHOLD = 0.10

    @classmethod
    def build(cls, *, delta_report=None, book_report=None, symbol: str = "") -> OrderFlowObservationalContext:
        delta_status = str(getattr(delta_report, "status", "NO_DATA") or "NO_DATA")
        book_status = str(getattr(book_report, "status", "NO_DATA") or "NO_DATA")

        recent_delta = float(getattr(delta_report, "recent_delta", 0.0) or 0.0)
        aggression = float(getattr(delta_report, "recent_total_aggression", 0.0) or 0.0)
        dominance = float(getattr(delta_report, "dominance", 0.0) or 0.0)
        persistence = float(getattr(delta_report, "persistence", 0.0) or 0.0)
        acceleration = float(getattr(delta_report, "acceleration", 0.0) or 0.0)

        imbalance = float(getattr(book_report, "imbalance", 0.0) or 0.0)
        spread = float(getattr(book_report, "spread", 0.0) or 0.0)
        bid_levels = int(getattr(book_report, "levels_bid", 0) or 0)
        ask_levels = int(getattr(book_report, "levels_ask", 0) or 0)

        reasons: list[str] = []
        delta_ready = delta_status in {"VALID", "LOW_ACTIVITY"}
        book_ready = book_status == "VALID"

        if not delta_ready:
            reasons.append(f"DELTA_{delta_status}")
        if not book_ready:
            reasons.append(f"BOOK_{book_status}")

        alignment = "NEUTRAL"
        delta_signal = 0
        if dominance >= cls.DELTA_ALIGN_THRESHOLD:
            delta_signal = 1
        elif dominance <= -cls.DELTA_ALIGN_THRESHOLD:
            delta_signal = -1

        book_signal = 0
        if imbalance >= cls.BOOK_ALIGN_THRESHOLD:
            book_signal = 1
        elif imbalance <= -cls.BOOK_ALIGN_THRESHOLD:
            book_signal = -1

        if delta_ready and book_ready:
            if delta_signal == 1 and book_signal == 1:
                alignment = "BULLISH_ALIGNED"
            elif delta_signal == -1 and book_signal == -1:
                alignment = "BEARISH_ALIGNED"
            elif delta_signal and book_signal and delta_signal != book_signal:
                alignment = "DIVERGENT"
                reasons.append("DELTA_BOOK_DIVERGENCE")
            else:
                alignment = "NEUTRAL"

        if delta_ready and book_ready:
            status = "READY"
        elif delta_status == "NO_DATA" and book_status == "NO_DATA":
            status = "NO_DATA"
        else:
            status = "DEGRADED"

        confidence = cls._confidence(
            delta_ready=delta_ready,
            book_ready=book_ready,
            dominance=dominance,
            persistence=persistence,
            imbalance=imbalance,
            alignment=alignment,
        )

        return OrderFlowObservationalContext(
            symbol=str(symbol or "").upper(),
            status=status,
            delta_status=delta_status,
            book_status=book_status,
            recent_delta=round(recent_delta, 4),
            recent_total_aggression=round(aggression, 4),
            delta_dominance=round(dominance, 4),
            delta_persistence=round(persistence, 4),
            delta_acceleration=round(acceleration, 4),
            book_imbalance=round(imbalance, 6),
            book_spread=round(spread, 10),
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            directional_alignment=alignment,
            confidence=confidence,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    @staticmethod
    def _confidence(*, delta_ready, book_ready, dominance, persistence, imbalance, alignment) -> float:
        if not (delta_ready and book_ready):
            return 0.0
        value = 0.35
        value += min(abs(dominance), 1.0) * 0.20
        value += min(abs(persistence), 1.0) * 0.15
        value += min(abs(imbalance), 1.0) * 0.15
        if alignment in {"BULLISH_ALIGNED", "BEARISH_ALIGNED"}:
            value += 0.15
        elif alignment == "DIVERGENT":
            value -= 0.15
        return round(max(0.0, min(value, 1.0)), 4)
