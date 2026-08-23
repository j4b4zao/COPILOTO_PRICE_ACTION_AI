"""Diagnóstico de prontidão da fonte real de Delta via Profit/Excel."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ProfitDeltaSourceSnapshot:
    status: str = "NO_DATA"
    total_snapshots: int = 0
    fresh_snapshots: int = 0
    duplicate_snapshots: int = 0
    aggression_available_snapshots: int = 0
    aggression_unavailable_snapshots: int = 0
    symbol_changes: int = 0
    accumulator_resets: int = 0
    order_flow_samples: int = 0
    duplicate_rate: float = 0.0
    aggression_availability_rate: float = 0.0
    symbol: str = ""
    last_buy: float | None = None
    last_sell: float | None = None
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ProfitDeltaSourceDiagnostics:
    """Acumula métricas de saúde da fonte de agressão do Profit."""

    VERSION = "RC1-PROFIT-DELTA-SOURCE-DIAGNOSTICS"
    MIN_READY_FRESH = 3
    DUPLICATE_DEGRADED_RATE = 0.80

    def __init__(self):
        self.total_snapshots = 0
        self.fresh_snapshots = 0
        self.duplicate_snapshots = 0
        self.aggression_available_snapshots = 0
        self.aggression_unavailable_snapshots = 0
        self.symbol_changes = 0
        self.accumulator_resets = 0
        self.symbol = ""
        self.last_buy: float | None = None
        self.last_sell: float | None = None
        self.order_flow_samples = 0

    def observe(self, *, integrity, aggression_buy, aggression_sell, order_flow) -> None:
        self.total_snapshots += 1
        symbol = str(getattr(integrity, "symbol", "") or "")
        duplicate = bool(getattr(integrity, "duplicate", False))
        symbol_changed = bool(getattr(integrity, "symbol_changed", False))
        available = aggression_buy is not None and aggression_sell is not None

        if duplicate:
            self.duplicate_snapshots += 1
        else:
            self.fresh_snapshots += 1

        if available:
            self.aggression_available_snapshots += 1
        else:
            self.aggression_unavailable_snapshots += 1

        if symbol_changed:
            self.symbol_changes += 1
            self.last_buy = None
            self.last_sell = None

        if available and not duplicate:
            buy = float(aggression_buy)
            sell = float(aggression_sell)
            if (
                self.last_buy is not None
                and self.last_sell is not None
                and (buy < self.last_buy or sell < self.last_sell)
            ):
                self.accumulator_resets += 1
            self.last_buy = buy
            self.last_sell = sell

        if symbol:
            self.symbol = symbol

        self.order_flow_samples = int(getattr(order_flow, "sample_count", 0) or 0)

    @property
    def snapshot(self) -> ProfitDeltaSourceSnapshot:
        total = self.total_snapshots
        duplicate_rate = self.duplicate_snapshots / total if total else 0.0
        availability_rate = self.aggression_available_snapshots / total if total else 0.0
        status = self._status(duplicate_rate, availability_rate)
        return ProfitDeltaSourceSnapshot(
            status=status,
            total_snapshots=total,
            fresh_snapshots=self.fresh_snapshots,
            duplicate_snapshots=self.duplicate_snapshots,
            aggression_available_snapshots=self.aggression_available_snapshots,
            aggression_unavailable_snapshots=self.aggression_unavailable_snapshots,
            symbol_changes=self.symbol_changes,
            accumulator_resets=self.accumulator_resets,
            order_flow_samples=self.order_flow_samples,
            duplicate_rate=round(duplicate_rate, 4),
            aggression_availability_rate=round(availability_rate, 4),
            symbol=self.symbol,
            last_buy=self.last_buy,
            last_sell=self.last_sell,
            passive_only=True,
        )

    def clear(self) -> None:
        self.__init__()

    def _status(self, duplicate_rate: float, availability_rate: float) -> str:
        if self.total_snapshots == 0:
            return "NO_DATA"
        if self.aggression_available_snapshots == 0:
            return "AGGRESSION_UNAVAILABLE"
        if duplicate_rate >= self.DUPLICATE_DEGRADED_RATE and self.total_snapshots >= 5:
            return "DEGRADED"
        if self.fresh_snapshots < self.MIN_READY_FRESH or self.order_flow_samples < 1:
            return "INITIALIZING"
        if availability_rate < 0.80:
            return "DEGRADED"
        return "READY"
