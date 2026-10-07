"""Offline execution of official decisions; profit is gross points, without costs.

CLOSE_ENTRY cannot fill structural entries away from the decision candle close.
STOP_FIRST is a conservative OHLC model, not an observed intrabar trajectory.
"""
from dataclasses import dataclass
from datetime import datetime
from math import isclose, isfinite
from numbers import Real

from core.analysis_context import AnalysisContext


@dataclass(slots=True)
class TradeResult:
    opened: bool = False
    closed: bool = False
    direction: str = "NONE"
    entry: float = 0.0
    stop: float = 0.0
    target: float = 0.0
    risk_reward: float = 0.0
    exit: float = 0.0
    profit: float = 0.0  # Gross points; no monetary multiplier or costs.
    bars: int = 0
    max_profit: float = 0.0  # OHLC bounds, not exact pre-exit excursions.
    max_loss: float = 0.0
    reason: str = ""
    setup: str = ""
    opened_at: datetime | None = None
    last_timestamp: datetime | None = None


class TradeSimulator:
    NAME = "TradeSimulator"
    VERSION = "CURRENT-DECISION-CONTRACT-RC1"
    ENTRY_MODEL = "CLOSE_ENTRY"
    INTRABAR_POLICY = "STOP_FIRST"
    PNL_UNIT = "GROSS_POINTS"

    def __init__(self):
        self.trade = None
        self.last_rejection = ""

    @staticmethod
    def _positive(value):
        return (isinstance(value, Real) and not isinstance(value, bool)
                and isfinite(value) and value > 0)

    @staticmethod
    def _same(left, right):
        # Narrow numerical comparison already used by project risk audits.
        return isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)

    @classmethod
    def valid_candle(cls, candle):
        timestamp = getattr(candle, "timestamp", None)
        if not isinstance(timestamp, datetime):
            return False
        prices = [getattr(candle, name, None) for name in ("open", "high", "low", "close")]
        if not all(cls._positive(value) for value in prices):
            return False
        opening, high, low, close = prices
        return low <= min(opening, close) <= max(opening, close) <= high

    def _reject(self, reason):
        self.last_rejection = reason
        return None

    def simulate(self, context, candle):
        self.last_rejection = ""
        if not isinstance(context, AnalysisContext):
            return self._reject("UNSUPPORTED_CONTRACT")
        if self.opened:
            return self._reject("POSITION_ALREADY_OPEN")
        decision, risk = context.decision, context.risk
        if (decision.valid is not True or decision.action not in ("BUY", "SELL")
                or decision.direction != decision.action or decision.signal != decision.action):
            return self._reject("DECISION_NOT_AUTHORIZED")
        if risk.valid is not True or risk.approved is not True:
            return self._reject("RISK_NOT_APPROVED")
        levels = (decision.entry, decision.stop, decision.target, decision.risk_reward)
        risk_levels = (risk.entry_price, risk.stop_loss, risk.take_profit, risk.risk_reward)
        if not all(self._positive(value) for value in levels + risk_levels):
            return self._reject("INVALID_LEVELS")
        if not all(self._same(left, right) for left, right in zip(levels, risk_levels)):
            return self._reject("DECISION_RISK_MISMATCH")
        entry, stop, target, rr = levels
        geometry = stop < entry < target if decision.action == "BUY" else target < entry < stop
        if not geometry:
            return self._reject("INVALID_GEOMETRY")
        if not self.valid_candle(candle):
            return self._reject("INVALID_CANDLE")
        if not self._same(entry, candle.close):
            return self._reject("UNSUPPORTED_ENTRY_MODEL")
        self.trade = TradeResult(
            opened=True, direction=decision.action, entry=entry, stop=stop,
            target=target, risk_reward=rr, setup=decision.setup,
            opened_at=candle.timestamp, last_timestamp=candle.timestamp,
        )
        return self.trade

    def update(self, candle):
        self.last_rejection = ""
        if not self.opened:
            return None
        if not self.valid_candle(candle):
            return self._reject("INVALID_CANDLE")
        trade = self.trade
        try:
            later = candle.timestamp > trade.last_timestamp
        except TypeError:
            return self._reject("INVALID_TIMESTAMP")
        if not later:
            return self._reject("NON_INCREASING_TIMESTAMP")
        trade.last_timestamp = candle.timestamp
        trade.bars += 1
        buy = trade.direction == "BUY"
        # Gaps are resolved at the opening before considering the candle range.
        if (candle.open <= trade.stop if buy else candle.open >= trade.stop):
            return self.close(candle.open, reason="GAP_STOP")
        if (candle.open >= trade.target if buy else candle.open <= trade.target):
            return self.close(trade.target, reason="GAP_TARGET")
        favorable = candle.high - trade.entry if buy else trade.entry - candle.low
        adverse = trade.entry - candle.low if buy else candle.high - trade.entry
        trade.max_profit = max(trade.max_profit, favorable)
        trade.max_loss = max(trade.max_loss, adverse)
        if (candle.low <= trade.stop if buy else candle.high >= trade.stop):
            return self.close(trade.stop, reason="STOP")
        if (candle.high >= trade.target if buy else candle.low <= trade.target):
            return self.close(trade.target, reason="TARGET")
        return None

    @property
    def opened(self):
        return self.trade is not None

    def close(self, price, *, reason="MANUAL"):
        self.last_rejection = ""
        if not self.opened:
            return None
        if not self._positive(price):
            return self._reject("INVALID_EXIT_PRICE")
        if reason not in ("MANUAL", "SESSION_END", "STOP", "TARGET", "GAP_STOP", "GAP_TARGET"):
            return self._reject("INVALID_EXIT_REASON")
        trade = self.trade
        trade.closed = True
        trade.exit = price
        trade.profit = price - trade.entry if trade.direction == "BUY" else trade.entry - price
        trade.reason = reason
        self.trade = None
        return trade
