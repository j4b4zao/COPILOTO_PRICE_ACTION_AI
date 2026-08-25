"""
Resultado da análise combinada M15/M5/M1.

RC3.4 - REGIME CONTEXT BRIDGE
"""

from dataclasses import dataclass, field

from enums.trend import Trend
from models.result_base import ResultBase


@dataclass(slots=True)
class MultiTimeframeResult(ResultBase):

    alignment: str = "INSUFFICIENT_DATA"
    bias: str = "NONE"
    aligned: bool = False
    conflict: bool = False

    m15_trend: Trend = Trend.UNKNOWN
    m5_trend: Trend = Trend.UNKNOWN
    m1_trend: Trend = Trend.UNKNOWN

    regime_context: str = "UNKNOWN"
    regime_compatible: bool = False

    closed_candle_counts: dict[str, int] = field(default_factory=dict)

    def clear(self) -> None:
        ResultBase.clear(self)

        self.alignment = "INSUFFICIENT_DATA"
        self.bias = "NONE"
        self.aligned = False
        self.conflict = False

        self.m15_trend = Trend.UNKNOWN
        self.m5_trend = Trend.UNKNOWN
        self.m1_trend = Trend.UNKNOWN

        self.regime_context = "UNKNOWN"
        self.regime_compatible = False

        self.closed_candle_counts.clear()
