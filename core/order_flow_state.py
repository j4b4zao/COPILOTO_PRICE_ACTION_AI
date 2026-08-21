"""Estado incremental e histórico de agressão exportada pelo Profit."""

from collections import deque
from dataclasses import dataclass
from dataclasses import field
import math
from typing import ClassVar


@dataclass(slots=True)
class OrderFlowState:

    HISTORY_SIZE: ClassVar[int] = 50
    RECENT_WINDOW: ClassVar[int] = 5
    PATTERN_WINDOW: ClassVar[int] = 3
    MIN_PATTERN_SAMPLES: ClassVar[int] = 6

    cumulative_buy: float | None = None
    cumulative_sell: float | None = None
    buy_aggression: float = 0.0
    sell_aggression: float = 0.0
    delta: float = 0.0
    total_aggression: float = 0.0
    cumulative_delta: float = 0.0
    history: deque[float] = field(
        default_factory=lambda: deque(maxlen=50)
    )
    aggression_history: deque[float] = field(
        default_factory=lambda: deque(maxlen=50)
    )
    price_history: deque[float] = field(
        default_factory=lambda: deque(maxlen=51)
    )
    ready: bool = False
    available: bool = False
    waiting_for_sample: bool = False
    sampling_mode: str = "TICK"
    source_units: int = 0

    def update(
        self,
        cumulative_buy: float,
        cumulative_sell: float,
        price: float | None = None,
        sampling_mode: str = "TICK",
        source_units: int = 1,
    ) -> bool:

        buy = self._validate(cumulative_buy)
        sell = self._validate(cumulative_sell)

        if buy is None or sell is None:
            self.mark_unavailable()
            return False

        previous_buy = self.cumulative_buy
        previous_sell = self.cumulative_sell
        valid_price = self._validate_price(price)
        self.sampling_mode = sampling_mode
        self.source_units = max(0, int(source_units))
        self.waiting_for_sample = False
        self.cumulative_buy = buy
        self.cumulative_sell = sell
        self.available = True

        if previous_buy is None or previous_sell is None:
            if valid_price is not None:
                self.price_history.append(valid_price)
            self._clear_interval()
            return False

        if buy < previous_buy or sell < previous_sell:
            self._clear_history()
            if valid_price is not None:
                self.price_history.append(valid_price)
            self._clear_interval()
            return False

        self.buy_aggression = buy - previous_buy
        self.sell_aggression = sell - previous_sell
        self.delta = self.buy_aggression - self.sell_aggression
        self.total_aggression = self.buy_aggression + self.sell_aggression
        self.history.append(self.delta)
        self.aggression_history.append(self.total_aggression)
        if valid_price is not None:
            self.price_history.append(valid_price)
        self.cumulative_delta += self.delta
        self.ready = True
        return True

    @property
    def sample_count(self) -> int:
        return len(self.history)

    @property
    def average_delta(self) -> float:
        if not self.history:
            return 0.0
        return sum(self.history) / len(self.history)

    @property
    def recent_delta(self) -> float:
        if not self.history:
            return 0.0
        return sum(tuple(self.history)[-self.RECENT_WINDOW:])

    @property
    def pattern_ready(self) -> bool:
        return (
            self.sample_count >= self.MIN_PATTERN_SAMPLES
            and len(self.aggression_history) >= self.MIN_PATTERN_SAMPLES
            and len(self.price_history) >= self.MIN_PATTERN_SAMPLES + 1
        )

    @property
    def recent_price_change(self) -> float:
        if not self.pattern_ready:
            return 0.0
        prices = tuple(self.price_history)
        window = min(self.RECENT_WINDOW, self.sample_count)
        return prices[-1] - prices[-(window + 1)]

    @property
    def aggression_activity_ratio(self) -> float:
        if not self.pattern_ready:
            return 0.0

        totals = tuple(self.aggression_history)
        recent = totals[-self.PATTERN_WINDOW:]
        previous = totals[-(self.PATTERN_WINDOW * 2):-self.PATTERN_WINDOW]
        previous_average = sum(previous) / len(previous)

        if previous_average <= 0:
            return 0.0

        return (sum(recent) / len(recent)) / previous_average

    def mark_unavailable(self) -> None:
        self.available = False
        self.waiting_for_sample = False
        self._clear_interval()

    def mark_waiting(self, sampling_mode: str) -> None:
        self.available = True
        self.sampling_mode = sampling_mode
        self.source_units = 0
        self.waiting_for_sample = True
        self._clear_interval()

    def clear(self) -> None:
        self.cumulative_buy = None
        self.cumulative_sell = None
        self.available = False
        self.waiting_for_sample = False
        self.sampling_mode = "TICK"
        self.source_units = 0
        self._clear_history()
        self._clear_interval()

    def _clear_history(self) -> None:
        self.history.clear()
        self.aggression_history.clear()
        self.price_history.clear()
        self.cumulative_delta = 0.0

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

    @staticmethod
    def _validate_price(value) -> float | None:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(converted) or converted <= 0:
            return None
        return converted
