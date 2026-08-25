"""Resultado observacional da análise de profundidade do Book."""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class BookDepthAnalysisResult(ResultBase):
    pressure: str = "UNAVAILABLE"
    imbalance: float = 0.0
    spread: float = 0.0
    spread_ratio: float = 0.0
    top_bid_concentration: float = 0.0
    top_ask_concentration: float = 0.0
    concentration_bias: str = "BALANCED"
    price_action_alignment: str = "UNAVAILABLE"
    order_flow_alignment: str = "UNAVAILABLE"
    confidence: float = 0.0
    duplicate_evidence_risk: bool = False
    passive_only: bool = True

    def clear(self) -> None:
        ResultBase.clear(self)
        self.pressure = "UNAVAILABLE"
        self.imbalance = 0.0
        self.spread = 0.0
        self.spread_ratio = 0.0
        self.top_bid_concentration = 0.0
        self.top_ask_concentration = 0.0
        self.concentration_bias = "BALANCED"
        self.price_action_alignment = "UNAVAILABLE"
        self.order_flow_alignment = "UNAVAILABLE"
        self.confidence = 0.0
        self.duplicate_evidence_risk = False
        self.passive_only = True
