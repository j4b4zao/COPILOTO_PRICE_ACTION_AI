"""Shadow calibration observacional para Order Flow consolidado."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class OrderFlowShadowResult:
    official_alignment: str
    shadow_alignment: str
    changed: bool
    delta_threshold: float
    book_threshold: float
    recent_delta: float
    dominance: float
    imbalance: float
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class OrderFlowShadowCalibration:
    """Reclassifica apenas para estudo, sem alterar o contexto oficial."""

    VERSION = "RC35-ORDER-FLOW-SHADOW-DIRECTION-FIX"

    def __init__(self, *, delta_threshold: float = 0.35, book_threshold: float = 0.062149):
        if not 0 < float(delta_threshold) <= 1:
            raise ValueError("delta_threshold invalido")
        if not 0 < float(book_threshold) <= 1:
            raise ValueError("book_threshold invalido")
        self.delta_threshold = float(delta_threshold)
        self.book_threshold = float(book_threshold)

    def evaluate(self, context) -> OrderFlowShadowResult:
        recent_delta = float(getattr(context, "recent_delta", 0.0) or 0.0)
        dominance = abs(float(getattr(context, "delta_dominance", 0.0) or 0.0))
        imbalance = float(getattr(context, "book_imbalance", 0.0) or 0.0)
        official = str(getattr(context, "directional_alignment", "NEUTRAL") or "NEUTRAL")
        status = str(getattr(context, "status", "NO_DATA") or "NO_DATA")

        shadow = "NEUTRAL"
        if status == "READY":
            delta_signal = 0
            if dominance >= self.delta_threshold:
                if recent_delta > 0:
                    delta_signal = 1
                elif recent_delta < 0:
                    delta_signal = -1
            book_signal = 1 if imbalance >= self.book_threshold else -1 if imbalance <= -self.book_threshold else 0
            if delta_signal == 1 and book_signal == 1:
                shadow = "BULLISH_ALIGNED"
            elif delta_signal == -1 and book_signal == -1:
                shadow = "BEARISH_ALIGNED"
            elif delta_signal and book_signal and delta_signal != book_signal:
                shadow = "DIVERGENT"

        return OrderFlowShadowResult(
            official_alignment=official,
            shadow_alignment=shadow,
            changed=official != shadow,
            delta_threshold=self.delta_threshold,
            book_threshold=self.book_threshold,
            recent_delta=round(recent_delta, 4),
            dominance=round(dominance, 6),
            imbalance=round(imbalance, 6),
        )
