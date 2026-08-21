"""Resultado informativo da análise de agressão e Delta."""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class OrderFlowResult(ResultBase):

    pressure: str = "INSUFFICIENT_DATA"
    buy_aggression: float = 0.0
    sell_aggression: float = 0.0
    delta: float = 0.0
    total_aggression: float = 0.0
    imbalance_ratio: float = 0.0

    def clear(self) -> None:
        ResultBase.clear(self)
        self.pressure = "INSUFFICIENT_DATA"
        self.buy_aggression = 0.0
        self.sell_aggression = 0.0
        self.delta = 0.0
        self.total_aggression = 0.0
        self.imbalance_ratio = 0.0
