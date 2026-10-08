"""RC7.1 passive historical contracts; no live resources or operational state.

Each build describes one explicit (period_start, reference_timestamp] window.
No carry-forward, cumulative reconstruction, aggressor inference or calibration.
Source labels/complete flags are assertions by the offline caller, not evidence
verified against a provider. Missing event identity makes aggregation unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from models.book_depth import BookLevel
from replay.historical_input_contract import AVAILABLE, UNAVAILABLE


class HistoricalOrderFlowValidationError(ValueError):
    """Invalid historical input, with a stable audit reason code."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _require(condition, reason):
    if not condition:
        raise HistoricalOrderFlowValidationError(reason)


def _items(value):
    try:
        return tuple(value)
    except TypeError as exc:
        raise HistoricalOrderFlowValidationError("INVALID_COLLECTION") from exc


def _time(value):
    _require(type(value) is datetime, "TIMESTAMP_REQUIRED")


def _le(left, right):
    try:
        return left <= right
    except TypeError as exc:
        raise HistoricalOrderFlowValidationError("INCOMPATIBLE_TIMESTAMPS") from exc


def _number(value, *, positive=False):
    _require(type(value) in (int, float), "INVALID_NUMBER")
    try:
        valid = math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        valid = False
    _require(valid, "INVALID_NUMBER")


def _text(value):
    _require(type(value) is str, "INVALID_IDENTIFIER")
    return value.strip()


def _proven(source):
    return source.upper() not in ("", "UNKNOWN", "UNAVAILABLE")


@dataclass(frozen=True, slots=True)
class HistoricalTradeEvent:
    timestamp: datetime
    observed_at: datetime
    price: float
    quantity: float
    aggressor: str = "UNKNOWN"
    source_id: str = ""
    event_id: str | None = None

    def __post_init__(self):
        _time(self.timestamp)
        _time(self.observed_at)
        _require(_le(self.timestamp, self.observed_at), "OBSERVATION_BEFORE_EVENT")
        _number(self.price, positive=True)
        _number(self.quantity, positive=True)
        side = _text(self.aggressor).upper()
        _require(side in ("BUY", "SELL", "UNKNOWN"), "INVALID_AGGRESSOR")
        object.__setattr__(self, "aggressor", side)
        # Match RC5 source identity: trim whitespace and normalize case.
        object.__setattr__(self, "source_id", _text(self.source_id).upper())
        if self.event_id is not None:
            object.__setattr__(self, "event_id", _text(self.event_id) or None)


@dataclass(frozen=True, slots=True)
class HistoricalBookSnapshot:
    observed_at: datetime
    source_id: str
    bids: tuple[BookLevel, ...] = ()
    asks: tuple[BookLevel, ...] = ()
    integrity_verified: bool = False
    complete: bool = False

    def __post_init__(self):
        _time(self.observed_at)
        # Match RC5 source identity: trim whitespace and normalize case.
        object.__setattr__(self, "source_id", _text(self.source_id).upper())
        _require(type(self.integrity_verified) is bool and type(self.complete) is bool,
                 "INVALID_COMPLETENESS")
        for name in ("bids", "asks"):
            levels = _items(getattr(self, name))
            for level in levels:
                _require(type(level) is BookLevel, "INVALID_BOOK_LEVEL")
                _number(level.price, positive=True)
                _number(level.quantity)
                _require(type(level.orders) is int and level.orders >= 0, "INVALID_BOOK_ORDERS")
            object.__setattr__(self, name, levels)
        _require(all(a.price > b.price for a, b in zip(self.bids, self.bids[1:])), "UNSORTED_BIDS")
        _require(all(a.price < b.price for a, b in zip(self.asks, self.asks[1:])), "UNSORTED_ASKS")
        if self.bids and self.asks:
            _require(self.bids[0].price < self.asks[0].price, "CROSSED_BOOK")

    @property
    def available(self):
        return bool(_proven(self.source_id) and self.integrity_verified and self.complete
                    and self.bids and self.asks)


def _validated_window(start, reference, trades, book):
    _time(reference)
    if start is not None:
        _time(start)
        _require(_le(start, reference) and start != reference, "INVALID_PERIOD")
    unique = {}
    unidentified = []
    for event in trades:
        _require(type(event) is HistoricalTradeEvent, "INVALID_TRADE_TYPE")
        _require(_le(event.timestamp, reference) and _le(event.observed_at, reference), "FUTURE_EVENT")
        if start is not None:
            _require(_le(start, event.timestamp) and start != event.timestamp, "EVENT_OUTSIDE_PERIOD")
        if not event.event_id:
            unidentified.append(event)
            continue
        key = (event.source_id, event.event_id)
        previous = unique.get(key)
        if previous is not None:
            _require((previous.timestamp, previous.price, previous.quantity, previous.aggressor)
                     == (event.timestamp, event.price, event.quantity, event.aggressor),
                     "CONFLICTING_EVENT_ID")
            if _le(previous.observed_at, event.observed_at):
                continue
        unique[key] = event
    try:
        events = tuple(sorted((*unique.values(), *unidentified), key=lambda e: (
            e.timestamp, e.observed_at, e.source_id, e.event_id or "", e.price, e.quantity, e.aggressor)))
    except TypeError as exc:
        raise HistoricalOrderFlowValidationError("INCOMPATIBLE_TIMESTAMPS") from exc
    if book is not None:
        _require(type(book) is HistoricalBookSnapshot, "INVALID_BOOK_TYPE")
        _require(_le(book.observed_at, reference), "FUTURE_BOOK")
    return events


@dataclass(frozen=True, slots=True)
class HistoricalOrderFlowSnapshot:
    reference_timestamp: datetime
    period_start: datetime | None = None
    trades: tuple[HistoricalTradeEvent, ...] = ()
    book: HistoricalBookSnapshot | None = None
    observation_complete: bool = False

    def __post_init__(self):
        _require(type(self.observation_complete) is bool, "INVALID_COMPLETENESS")
        events = _validated_window(self.period_start, self.reference_timestamp, _items(self.trades), self.book)
        object.__setattr__(self, "trades", events)
        # A historical Book must be explicitly observed at this cutoff. No TTL
        # guess and no promotion of a previous snapshot into current evidence.
        if self.book is not None and (not self.observation_complete or not self.book.available
                                       or self.book.observed_at != self.reference_timestamp):
            object.__setattr__(self, "book", None)
        for side in ("BUY", "SELL", "UNKNOWN"):
            _number(sum(e.quantity for e in events if e.aggressor == side))
        _number(sum(e.quantity for e in events))

    @property
    def reason(self):
        if not self.observation_complete:
            return "OBSERVATION_GAP"
        if self.period_start is None:
            return "PERIOD_UNKNOWN"
        if not self.trades:
            return "NO_TRADE_EVENTS"
        if any(not _proven(e.source_id) for e in self.trades):
            return "PROVENANCE_MISSING"
        if any(e.event_id is None for e in self.trades):
            return "EVENT_IDENTITY_UNVERIFIABLE"
        return ""

    @property
    def status(self):
        return UNAVAILABLE if self.reason else AVAILABLE

    @property
    def available(self):
        return self.status == AVAILABLE

    @property
    def provenance(self):
        return tuple(sorted({e.source_id for e in self.trades if _proven(e.source_id)}))

    @property
    def valid_trades(self):
        return self.trades if self.available else ()

    def _quantity(self, side=None):
        if not self.available:
            return None
        return sum(e.quantity for e in self.trades if side is None or e.aggressor == side)

    @property
    def total_quantity(self):
        return self._quantity()

    @property
    def buy_quantity(self):
        return self._quantity("BUY")

    @property
    def sell_quantity(self):
        return self._quantity("SELL")

    @property
    def unknown_quantity(self):
        return self._quantity("UNKNOWN")

    @property
    def delta(self):
        """Classified-only delta; None when no classified evidence exists.

        UNKNOWN volume remains separate: this is never a full-market delta claim.
        """
        if not self.available or not any(e.aggressor in ("BUY", "SELL") for e in self.trades):
            return None
        return self.buy_quantity - self.sell_quantity


class HistoricalOrderFlowBuilder:
    """Stateless builder: separate calls/sessions never reuse past evidence.

    Caller supplies a single instrument/session and explicit window each call.
    Repeated builds are snapshots, not incremental batches to be summed.
    """

    VERSION = "RC7.1-HISTORICAL-CONTRACTS"

    @staticmethod
    def build(reference_timestamp, trades=(), book=None, *, period_start=None,
              observation_complete=False):
        return HistoricalOrderFlowSnapshot(reference_timestamp, period_start, _items(trades),
                                           book, observation_complete)
