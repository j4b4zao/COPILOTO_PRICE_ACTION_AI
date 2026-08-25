"""Snapshot observacional de Order Flow derivado do Book e T&T RTD (RC3)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfitRTDOrderFlowWindowSnapshot:
    symbol: str
    timestamp: str
    trade_count: int
    buyer_aggressed_quantity: float
    seller_aggressed_quantity: float
    rlp_quantity: float
    classified_aggression_quantity: float
    total_traded_quantity: float
    delta: float
    delta_ratio: float
    aggression_pressure: str
    bid_quantity: float
    ask_quantity: float
    book_imbalance: float
    book_pressure: str
    source: str = "PROFIT_RTD"
    window_semantics: str = "CURRENT_RTD_WINDOW"
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDOrderFlowWindowBuilder:
    """Agrega somente a janela atual dos leitores RTD, sem acumular ciclos."""

    NAME = "ProfitRTDOrderFlowWindowBuilder"
    VERSION = "RC3"
    PRESSURE_THRESHOLD = 0.10

    def __init__(self, times_trades_reader, book_reader=None):
        if not callable(getattr(times_trades_reader, "read_times_trades", None)):
            raise TypeError("times_trades_reader deve expor read_times_trades().")
        if book_reader is not None and not callable(
            getattr(book_reader, "read_book_depth", None)
        ):
            raise TypeError("book_reader deve expor read_book_depth().")
        self.times_trades_reader = times_trades_reader
        self.book_reader = book_reader

    def snapshot(self, symbol):
        trades_payload = self.times_trades_reader.read_times_trades(symbol)
        book_payload = (
            self.book_reader.read_book_depth(symbol)
            if self.book_reader is not None
            else None
        )
        return self.build(trades_payload, book_payload)

    @classmethod
    def build(cls, trades_payload, book_payload=None):
        if not isinstance(trades_payload, dict):
            raise TypeError("Payload de T&T deve ser dict.")
        if not trades_payload.get("observational_only", False):
            raise ValueError("Payload de T&T deve permanecer observacional.")

        symbol = str(trades_payload.get("symbol") or "").strip().upper()
        timestamp = str(trades_payload.get("timestamp") or "").strip()
        trades = trades_payload.get("trades")
        if not symbol or not timestamp or not isinstance(trades, list) or not trades:
            raise ValueError("Payload de T&T incompleto.")

        buy = 0.0
        sell = 0.0
        rlp = 0.0
        total = 0.0
        for trade in trades:
            if not isinstance(trade, dict):
                raise TypeError("Negócio deve ser dict.")
            quantity = cls._non_negative_quantity(trade.get("quantity"))
            aggressor = str(trade.get("aggressor") or "").strip()
            if aggressor == "Comprador":
                buy += quantity
            elif aggressor == "Vendedor":
                sell += quantity
            elif aggressor == "RLP":
                rlp += quantity
            else:
                raise ValueError("Agressor incompatível com T&T RTD.")
            total += quantity

        classified = buy + sell
        delta = buy - sell
        delta_ratio = delta / classified if classified > 0 else 0.0
        aggression_pressure = cls._pressure(delta_ratio, "BUY", "SELL")

        bid_quantity = 0.0
        ask_quantity = 0.0
        book_imbalance = 0.0
        book_pressure = "UNAVAILABLE"
        if book_payload is not None:
            if not isinstance(book_payload, dict):
                raise TypeError("Payload de Book deve ser dict.")
            book_symbol = str(book_payload.get("symbol") or "").strip().upper()
            if book_symbol != symbol:
                raise ValueError("Ativo do Book difere do T&T RTD.")
            if not book_payload.get("passive_only", False):
                raise ValueError("Payload de Book deve permanecer passivo.")
            bids = book_payload.get("bids")
            asks = book_payload.get("asks")
            if not isinstance(bids, list) or not isinstance(asks, list) or not bids or not asks:
                raise ValueError("Payload de Book incompleto.")
            bid_quantity = sum(
                cls._non_negative_quantity(level.get("quantity"))
                for level in bids
                if isinstance(level, dict)
            )
            ask_quantity = sum(
                cls._non_negative_quantity(level.get("quantity"))
                for level in asks
                if isinstance(level, dict)
            )
            book_total = bid_quantity + ask_quantity
            book_imbalance = (
                (bid_quantity - ask_quantity) / book_total
                if book_total > 0
                else 0.0
            )
            book_pressure = cls._pressure(
                book_imbalance,
                "BID_DOMINANT",
                "ASK_DOMINANT",
            )

        return ProfitRTDOrderFlowWindowSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            trade_count=len(trades),
            buyer_aggressed_quantity=buy,
            seller_aggressed_quantity=sell,
            rlp_quantity=rlp,
            classified_aggression_quantity=classified,
            total_traded_quantity=total,
            delta=delta,
            delta_ratio=delta_ratio,
            aggression_pressure=aggression_pressure,
            bid_quantity=bid_quantity,
            ask_quantity=ask_quantity,
            book_imbalance=book_imbalance,
            book_pressure=book_pressure,
        )

    @classmethod
    def _pressure(cls, ratio, positive, negative):
        if ratio >= cls.PRESSURE_THRESHOLD:
            return positive
        if ratio <= -cls.PRESSURE_THRESHOLD:
            return negative
        return "BALANCED"

    @staticmethod
    def _non_negative_quantity(value):
        if isinstance(value, bool):
            raise TypeError("Quantidade deve ser numérica.")
        try:
            quantity = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Quantidade inválida.") from exc
        if quantity < 0:
            raise ValueError("Quantidade não pode ser negativa.")
        return quantity
