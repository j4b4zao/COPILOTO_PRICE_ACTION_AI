"""Deduplicação temporal da janela móvel de Times & Trades RTD (RC4)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfitRTDNewTradesBatch:
    symbol: str
    timestamp: str
    new_trades: tuple[dict, ...]
    new_trade_count: int
    overlap_count: int
    window_trade_count: int
    baseline_only: bool
    continuity: str
    source: str = "PROFIT_RTD"
    semantics: str = "NEW_TRADES_SINCE_PREVIOUS_WINDOW"
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDTimesTradesDeduplicator:
    """Extrai somente negócios novos entre janelas RTD newest-first."""

    NAME = "ProfitRTDTimesTradesDeduplicator"
    VERSION = "RC4"

    def __init__(self):
        self._symbol: str | None = None
        self._previous: tuple[tuple, ...] = ()

    def clear(self) -> None:
        self._symbol = None
        self._previous = ()

    def observe(self, payload: dict) -> ProfitRTDNewTradesBatch:
        symbol, timestamp, trades = self._validate_payload(payload)
        fingerprints = tuple(self._fingerprint(trade) for trade in trades)

        if self._symbol is None:
            self._symbol = symbol
            self._previous = fingerprints
            return self._batch(symbol, timestamp, trades, 0, 0, True, "BASELINE_ESTABLISHED")

        if symbol != self._symbol:
            self._symbol = symbol
            self._previous = fingerprints
            return self._batch(symbol, timestamp, trades, 0, 0, True, "SYMBOL_RESET")

        shift, overlap = self._find_shift(fingerprints, self._previous)
        if shift is None:
            self._previous = fingerprints
            return self._batch(symbol, timestamp, trades, 0, 0, True, "OVERLAP_LOST_REBASE")

        self._previous = fingerprints
        return self._batch(symbol, timestamp, trades, shift, overlap, False, "CONTIGUOUS")

    @staticmethod
    def _find_shift(current: tuple[tuple, ...], previous: tuple[tuple, ...]):
        if current == previous:
            return 0, len(current)
        max_overlap = min(len(current), len(previous))
        for overlap in range(max_overlap, 0, -1):
            shift = len(current) - overlap
            if current[shift:] == previous[:overlap]:
                return shift, overlap
        return None, 0

    @staticmethod
    def _fingerprint(trade: dict) -> tuple:
        if not isinstance(trade, dict):
            raise TypeError("Negócio RTD deve ser dict.")
        required = ("timestamp", "buyer", "price", "quantity", "seller", "aggressor")
        values = []
        for key in required:
            value = trade.get(key)
            if value is None or str(value).strip() == "":
                raise ValueError(f"Campo obrigatório ausente no negócio RTD: {key}.")
            values.append(value)
        try:
            price = float(values[2])
            quantity = float(values[3])
        except (TypeError, ValueError) as exc:
            raise ValueError("Preço/quantidade inválidos no negócio RTD.") from exc
        if price <= 0 or quantity <= 0:
            raise ValueError("Preço/quantidade devem ser positivos no negócio RTD.")
        return (
            str(values[0]),
            str(values[1]).strip(),
            price,
            quantity,
            str(values[4]).strip(),
            str(values[5]).strip(),
        )

    @staticmethod
    def _validate_payload(payload: dict):
        if not isinstance(payload, dict):
            raise TypeError("Payload de T&T deve ser dict.")
        if not payload.get("observational_only", False):
            raise ValueError("Payload de T&T deve permanecer observacional.")
        symbol = str(payload.get("symbol") or "").strip().upper()
        timestamp = str(payload.get("timestamp") or "").strip()
        trades = payload.get("trades")
        if not symbol or not timestamp or not isinstance(trades, list) or not trades:
            raise ValueError("Payload de T&T incompleto.")
        return symbol, timestamp, trades

    @staticmethod
    def _batch(symbol, timestamp, trades, new_count, overlap_count, baseline_only, continuity):
        new_trades = tuple(dict(trade) for trade in trades[:new_count])
        return ProfitRTDNewTradesBatch(
            symbol=symbol,
            timestamp=timestamp,
            new_trades=new_trades,
            new_trade_count=len(new_trades),
            overlap_count=overlap_count,
            window_trade_count=len(trades),
            baseline_only=baseline_only,
            continuity=continuity,
        )
