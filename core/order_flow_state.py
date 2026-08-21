"""Estado incremental dos dados de agressão exportados pelo Profit."""

from dataclasses import dataclass
import math


@dataclass(slots=True)
class OrderFlowState:

    cumulative_buy: float | None = None
    cumulative_sell: float | None = None
    buy_aggression: float = 0.0
    sell_aggression: float = 0.0
    delta: float = 0.0
    total_aggression: float = 0.0
    ready: bool = False
    available: bool = False

    def update(self, cumulative_buy: float, cumulative_sell: float) -> bool:

        buy = self._validate(cumulative_buy)
        sell = self._validate(cumulative_sell)

        if buy is None or sell is None:
            self.mark_unavailable()
            return False

        previous_buy = self.cumulative_buy
        previous_sell = self.cumulative_sell
        self.cumulative_buy = buy
        self.cumulative_sell = sell
        self.available = True

        if previous_buy is None or previous_sell is None:
            self._clear_interval()
            return False

        if buy < previous_buy or sell < previous_sell:
            self._clear_interval()
            return False

        self.buy_aggression = buy - previous_buy
        self.sell_aggression = sell - previous_sell
        self.delta = self.buy_aggression - self.sell_aggression
        self.total_aggression = self.buy_aggression + self.sell_aggression
        self.ready = True
        return True

    def mark_unavailable(self) -> None:
        self.available = False
        self._clear_interval()

    def clear(self) -> None:
        self.cumulative_buy = None
        self.cumulative_sell = None
        self.available = False
        self._clear_interval()

    def _clear_interval(self) -> None:
        self.buy_aggression = 0.0
        self.sell_aggression = 0.0
        self.delta = 0.0
        self.total_aggression = 0.0
        self.ready = False

    @staticmethod
    def _validate(value) -> float | None:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(converted) or converted < 0:
            return None
        return converted
