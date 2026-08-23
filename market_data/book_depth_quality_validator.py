"""Validador observacional da qualidade de snapshots reais de BookDepth."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class BookDepthQualityReport:
    status: str = "NO_DATA"
    levels_bid: int = 0
    levels_ask: int = 0
    spread: float = 0.0
    spread_ratio: float = 0.0
    imbalance: float = 0.0
    top_bid_concentration: float = 0.0
    top_ask_concentration: float = 0.0
    concentration_edge: float = 0.0
    duplicate_rate: float = 0.0
    availability_rate: float = 0.0
    anomaly_count: int = 0
    source_status: str = "NO_DATA"
    reasons: tuple[str, ...] = ()
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BookDepthQualityValidator:
    VERSION = "RC1-BOOK-DEPTH-QUALITY"
    MIN_LEVELS = 3
    MAX_SPREAD_RATIO = 0.002
    MAX_DUPLICATE_RATE = 0.80
    MIN_AVAILABILITY_RATE = 0.80

    def evaluate(self, snapshot, source_snapshot=None) -> BookDepthQualityReport:
        source_status = str(getattr(source_snapshot, "status", "NO_DATA") or "NO_DATA")
        duplicate_rate = float(getattr(source_snapshot, "duplicate_rate", 0.0) or 0.0)
        availability_rate = float(getattr(source_snapshot, "availability_rate", 0.0) or 0.0)
        reasons = []
        anomalies = 0

        if snapshot is None or not getattr(snapshot, "available", False):
            return BookDepthQualityReport(
                status="NO_DATA" if source_status == "NO_DATA" else "UNAVAILABLE",
                duplicate_rate=duplicate_rate,
                availability_rate=availability_rate,
                source_status=source_status,
                reasons=("BOOK_UNAVAILABLE",),
            )

        bids = tuple(getattr(snapshot, "bids", ()) or ())
        asks = tuple(getattr(snapshot, "asks", ()) or ())
        levels_bid = len(bids)
        levels_ask = len(asks)
        spread = float(getattr(snapshot, "spread", 0.0) or 0.0)
        best_bid = float(getattr(snapshot, "best_bid", 0.0) or 0.0)
        best_ask = float(getattr(snapshot, "best_ask", 0.0) or 0.0)
        mid = (best_bid + best_ask) / 2.0 if best_bid > 0 and best_ask > 0 else 0.0
        spread_ratio = spread / mid if mid > 0 else 0.0

        total_bid = float(getattr(snapshot, "bid_quantity", 0.0) or 0.0)
        total_ask = float(getattr(snapshot, "ask_quantity", 0.0) or 0.0)
        top_bid = sum(float(level.quantity) for level in bids[:3])
        top_ask = sum(float(level.quantity) for level in asks[:3])
        bid_conc = top_bid / total_bid if total_bid > 0 else 0.0
        ask_conc = top_ask / total_ask if total_ask > 0 else 0.0
        edge = abs(bid_conc - ask_conc)

        if levels_bid < self.MIN_LEVELS or levels_ask < self.MIN_LEVELS:
            reasons.append("SHALLOW_BOOK")
        if spread_ratio > self.MAX_SPREAD_RATIO:
            anomalies += 1
            reasons.append("WIDE_SPREAD")
        if duplicate_rate >= self.MAX_DUPLICATE_RATE:
            anomalies += 1
            reasons.append("EXCESSIVE_DUPLICATION")
        if availability_rate and availability_rate < self.MIN_AVAILABILITY_RATE:
            anomalies += 1
            reasons.append("LOW_AVAILABILITY")
        if source_status in {"UNAVAILABLE", "DEGRADED"}:
            anomalies += 1
            reasons.append(f"SOURCE_{source_status}")

        if source_status in {"UNAVAILABLE", "DEGRADED"} or anomalies > 0:
            status = "DEGRADED"
        elif levels_bid < self.MIN_LEVELS or levels_ask < self.MIN_LEVELS:
            status = "SHALLOW"
        elif source_status in {"NO_DATA", "INITIALIZING"}:
            status = "INITIALIZING"
        else:
            status = "VALID"

        return BookDepthQualityReport(
            status=status,
            levels_bid=levels_bid,
            levels_ask=levels_ask,
            spread=round(spread, 10),
            spread_ratio=round(spread_ratio, 6),
            imbalance=round(float(getattr(snapshot, "imbalance", 0.0) or 0.0), 6),
            top_bid_concentration=round(bid_conc, 4),
            top_ask_concentration=round(ask_conc, 4),
            concentration_edge=round(edge, 4),
            duplicate_rate=round(duplicate_rate, 4),
            availability_rate=round(availability_rate, 4),
            anomaly_count=anomalies,
            source_status=source_status,
            reasons=tuple(dict.fromkeys(reasons)),
            passive_only=True,
        )
