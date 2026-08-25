"""Contratos imutáveis para profundidade real do Book de ofertas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass(slots=True, frozen=True)
class BookLevel:
    price: float
    quantity: float
    orders: int = 0

    def __post_init__(self):
        if self.price <= 0:
            raise ValueError("BookLevel.price deve ser positivo.")
        if self.quantity < 0:
            raise ValueError("BookLevel.quantity não pode ser negativo.")
        if self.orders < 0:
            raise ValueError("BookLevel.orders não pode ser negativo.")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class BookDepthSnapshot:
    symbol: str
    timestamp: str
    bids: tuple[BookLevel, ...] = field(default_factory=tuple)
    asks: tuple[BookLevel, ...] = field(default_factory=tuple)
    source: str = "UNAVAILABLE"
    available: bool = False

    @classmethod
    def unavailable(cls, symbol: str = "", source: str = "UNAVAILABLE"):
        return cls(
            symbol=str(symbol or ""),
            timestamp="",
            bids=(),
            asks=(),
            source=str(source or "UNAVAILABLE"),
            available=False,
        )

    @classmethod
    def build(cls, *, symbol, timestamp, bids, asks, source):
        bid_levels = tuple(cls._coerce_level(level) for level in bids)
        ask_levels = tuple(cls._coerce_level(level) for level in asks)
        cls._validate_sides(bid_levels, ask_levels)
        return cls(
            symbol=str(symbol or "").upper(),
            timestamp=cls._normalize_timestamp(timestamp),
            bids=bid_levels,
            asks=ask_levels,
            source=str(source or "UNKNOWN"),
            available=bool(bid_levels and ask_levels),
        )

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round(self.best_ask - self.best_bid, 10)

    @property
    def bid_quantity(self) -> float:
        return round(sum(level.quantity for level in self.bids), 10)

    @property
    def ask_quantity(self) -> float:
        return round(sum(level.quantity for level in self.asks), 10)

    @property
    def imbalance(self) -> float:
        total = self.bid_quantity + self.ask_quantity
        if total <= 0:
            return 0.0
        return round((self.bid_quantity - self.ask_quantity) / total, 6)

    @property
    def liquidity_pressure(self) -> str:
        value = self.imbalance
        if value >= 0.15:
            return "BID_DOMINANT"
        if value <= -0.15:
            return "ASK_DOMINANT"
        return "BALANCED"

    def top(self, levels: int = 5) -> "BookDepthSnapshot":
        levels = max(1, int(levels))
        return BookDepthSnapshot(
            symbol=self.symbol,
            timestamp=self.timestamp,
            bids=self.bids[:levels],
            asks=self.asks[:levels],
            source=self.source,
            available=self.available,
        )

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "source": self.source,
            "available": self.available,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "bid_quantity": self.bid_quantity,
            "ask_quantity": self.ask_quantity,
            "imbalance": self.imbalance,
            "liquidity_pressure": self.liquidity_pressure,
        }

    @staticmethod
    def _coerce_level(level) -> BookLevel:
        if isinstance(level, BookLevel):
            return level
        if isinstance(level, dict):
            return BookLevel(
                price=float(level["price"]),
                quantity=float(level["quantity"]),
                orders=int(level.get("orders", 0) or 0),
            )
        if isinstance(level, (tuple, list)) and len(level) in (2, 3):
            return BookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
                orders=int(level[2]) if len(level) == 3 else 0,
            )
        raise TypeError("Nível de Book inválido.")

    @staticmethod
    def _validate_sides(bids, asks):
        if bids and any(bids[i].price < bids[i + 1].price for i in range(len(bids) - 1)):
            raise ValueError("Bids devem estar ordenados do maior para o menor preço.")
        if asks and any(asks[i].price > asks[i + 1].price for i in range(len(asks) - 1)):
            raise ValueError("Asks devem estar ordenados do menor para o maior preço.")
        if bids and asks and bids[0].price >= asks[0].price:
            raise ValueError("Book cruzado: best_bid deve ser menor que best_ask.")

    @staticmethod
    def _normalize_timestamp(value) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        text = str(value or "").strip()
        if not text:
            raise ValueError("timestamp do Book é obrigatório.")
        return text


class BookDepthProvider:
    """Interface mínima para qualquer fonte real de profundidade."""

    SOURCE = "ABSTRACT"

    def snapshot(self, symbol: str) -> BookDepthSnapshot:
        raise NotImplementedError
