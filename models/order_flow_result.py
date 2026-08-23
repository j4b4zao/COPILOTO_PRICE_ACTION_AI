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
    cumulative_delta: float = 0.0
    recent_delta: float = 0.0
    average_delta: float = 0.0
    sample_count: int = 0
    trend: str = "INSUFFICIENT_DATA"
    patterns_ready: bool = False
    recent_price_change: float = 0.0
    aggression_activity_ratio: float = 0.0
    divergence: str = "INSUFFICIENT_DATA"
    absorption: str = "INSUFFICIENT_DATA"
    exhaustion: str = "INSUFFICIENT_DATA"
    sampling_mode: str = "TICK"
    source_units: int = 0
    delta_dominance: float = 0.0
    price_efficiency: float = 0.0
    history_maturity: float = 0.0
    pattern_confidence: float = 0.0
    pattern_quality: str = "INSUFFICIENT_DATA"
    pattern_confirmed: bool = False
    delta_persistence: float = 0.0
    delta_acceleration: float = 0.0
    delta_impulse_ratio: float = 0.0
    flow_momentum: str = "INSUFFICIENT_DATA"

    def clear(self) -> None:
        ResultBase.clear(self)
        self.pressure = "INSUFFICIENT_DATA"
        self.buy_aggression = 0.0
        self.sell_aggression = 0.0
        self.delta = 0.0
        self.total_aggression = 0.0
        self.imbalance_ratio = 0.0
        self.cumulative_delta = 0.0
        self.recent_delta = 0.0
        self.average_delta = 0.0
        self.sample_count = 0
        self.trend = "INSUFFICIENT_DATA"
        self.patterns_ready = False
        self.recent_price_change = 0.0
        self.aggression_activity_ratio = 0.0
        self.divergence = "INSUFFICIENT_DATA"
        self.absorption = "INSUFFICIENT_DATA"
        self.exhaustion = "INSUFFICIENT_DATA"
        self.sampling_mode = "TICK"
        self.source_units = 0
        self.delta_dominance = 0.0
        self.price_efficiency = 0.0
        self.history_maturity = 0.0
        self.pattern_confidence = 0.0
        self.pattern_quality = "INSUFFICIENT_DATA"
        self.pattern_confirmed = False
        self.delta_persistence = 0.0
        self.delta_acceleration = 0.0
        self.delta_impulse_ratio = 0.0
        self.flow_momentum = "INSUFFICIENT_DATA"
