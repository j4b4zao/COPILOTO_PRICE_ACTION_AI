"""Diagnóstico observacional de prontidão e qualidade do BookDepth real."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class BookDepthSourceReport:
    status: str = "NO_DATA"
    total_snapshots: int = 0
    fresh_snapshots: int = 0
    duplicate_snapshots: int = 0
    unavailable_snapshots: int = 0
    invalid_snapshots: int = 0
    symbol_changes: int = 0
    bid_levels: int = 0
    ask_levels: int = 0
    spread: float = 0.0
    imbalance: float = 0.0
    duplicate_rate: float = 0.0
    availability_rate: float = 0.0
    symbol: str = ""
    source: str = "UNAVAILABLE"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BookDepthSourceDiagnostics:
    """Mede saúde básica da fonte Level 2 sem efeito operacional."""

    VERSION = "RC1-BOOK-DEPTH-SOURCE-DIAGNOSTICS"
    MIN_READY_FRESH = 3
    MIN_LEVELS_PER_SIDE = 3
    MAX_DUPLICATE_RATE = 0.80

    def __init__(self):
        self.total_snapshots = 0
        self.fresh_snapshots = 0
        self.duplicate_snapshots = 0
        self.unavailable_snapshots = 0
        self.invalid_snapshots = 0
        self.symbol_changes = 0
        self._last_fingerprint = None
        self._last_symbol = ""
        self._last_snapshot = None

    def observe(self, snapshot) -> BookDepthSourceReport:
        self.total_snapshots += 1
        if snapshot is None or not bool(getattr(snapshot, "available", False)):
            self.unavailable_snapshots += 1
            self._last_snapshot = snapshot
            return self.report

        symbol = str(getattr(snapshot, "symbol", "") or "").upper()
        if self._last_symbol and symbol and symbol != self._last_symbol:
            self.symbol_changes += 1
        if symbol:
            self._last_symbol = symbol

        try:
            fingerprint = self._fingerprint(snapshot)
            duplicate = fingerprint == self._last_fingerprint
            if duplicate:
                self.duplicate_snapshots += 1
            else:
                self.fresh_snapshots += 1
                self._last_fingerprint = fingerprint
            self._last_snapshot = snapshot
        except Exception:
            self.invalid_snapshots += 1
            self._last_snapshot = None

        return self.report

    @property
    def report(self) -> BookDepthSourceReport:
        total = self.total_snapshots
        duplicate_rate = self.duplicate_snapshots / total if total else 0.0
        availability_rate = (total - self.unavailable_snapshots - self.invalid_snapshots) / total if total else 0.0
        snap = self._last_snapshot
        bids = tuple(getattr(snap, "bids", ()) or ()) if snap is not None else ()
        asks = tuple(getattr(snap, "asks", ()) or ()) if snap is not None else ()
        spread = float(getattr(snap, "spread", 0.0) or 0.0) if snap is not None else 0.0
        imbalance = float(getattr(snap, "imbalance", 0.0) or 0.0) if snap is not None else 0.0
        status = self._status(len(bids), len(asks), duplicate_rate, availability_rate)
        return BookDepthSourceReport(
            status=status,
            total_snapshots=total,
            fresh_snapshots=self.fresh_snapshots,
            duplicate_snapshots=self.duplicate_snapshots,
            unavailable_snapshots=self.unavailable_snapshots,
            invalid_snapshots=self.invalid_snapshots,
            symbol_changes=self.symbol_changes,
            bid_levels=len(bids),
            ask_levels=len(asks),
            spread=round(spread, 10),
            imbalance=round(imbalance, 6),
            duplicate_rate=round(duplicate_rate, 4),
            availability_rate=round(availability_rate, 4),
            symbol=str(getattr(snap, "symbol", "") or "") if snap is not None else self._last_symbol,
            source=str(getattr(snap, "source", "UNAVAILABLE") or "UNAVAILABLE") if snap is not None else "UNAVAILABLE",
            passive_only=True,
        )

    def clear(self) -> None:
        self.__init__()

    def _status(self, bid_levels, ask_levels, duplicate_rate, availability_rate):
        if self.total_snapshots == 0:
            return "NO_DATA"
        if availability_rate <= 0.0:
            return "UNAVAILABLE"
        if self.invalid_snapshots > 0:
            return "DEGRADED"
        if bid_levels < self.MIN_LEVELS_PER_SIDE or ask_levels < self.MIN_LEVELS_PER_SIDE:
            return "SHALLOW"
        if duplicate_rate >= self.MAX_DUPLICATE_RATE and self.total_snapshots >= 5:
            return "DEGRADED"
        if self.fresh_snapshots < self.MIN_READY_FRESH:
            return "INITIALIZING"
        return "READY"

    @staticmethod
    def _fingerprint(snapshot):
        bids = tuple((float(level.price), float(level.quantity), int(level.orders)) for level in snapshot.bids)
        asks = tuple((float(level.price), float(level.quantity), int(level.orders)) for level in snapshot.asks)
        return (str(snapshot.symbol).upper(), bids, asks)
