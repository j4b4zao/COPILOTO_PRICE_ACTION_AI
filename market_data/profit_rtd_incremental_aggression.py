"""Agregação observacional dos negócios novos deduplicados do T&T RTD (RC5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfitRTDIncrementalAggressionSnapshot:
    symbol: str
    timestamp: str
    new_trade_count: int
    buyer_aggression: float
    seller_aggression: float
    rlp_quantity: float
    classified_aggression: float
    total_traded_quantity: float
    delta: float
    delta_ratio: float
    pressure: str
    continuity: str
    baseline_only: bool
    source: str = "PROFIT_RTD"
    semantics: str = "NEW_DEDUPLICATED_TRADES_ONLY"
    observational_only: bool = True
    state_update_allowed: bool = False
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDIncrementalAggressionBuilder:
    NAME = "ProfitRTDIncrementalAggressionBuilder"
    VERSION = "RC5"
    PRESSURE_THRESHOLD = 0.10

    @classmethod
    def build(cls, batch) -> ProfitRTDIncrementalAggressionSnapshot:
        if not getattr(batch, "observational_only", False):
            raise ValueError("Batch deve permanecer observacional.")

        symbol = str(getattr(batch, "symbol", "") or "").strip().upper()
        timestamp = str(getattr(batch, "timestamp", "") or "").strip()
        trades = tuple(getattr(batch, "new_trades", ()) or ())
        baseline_only = bool(getattr(batch, "baseline_only", False))
        continuity = str(getattr(batch, "continuity", "") or "").strip()

        if not symbol or not timestamp or not continuity:
            raise ValueError("Batch RTD incompleto.")
        if len(trades) != int(getattr(batch, "new_trade_count", -1)):
            raise ValueError("Contagem de negócios novos inconsistente.")
        if baseline_only and trades:
            raise ValueError("Baseline não pode emitir negócios novos.")

        buy = sell = rlp = total = 0.0
        for trade in trades:
            if not isinstance(trade, dict):
                raise TypeError("Negócio novo deve ser dict.")
            quantity = cls._positive_quantity(trade.get("quantity"))
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
        ratio = delta / classified if classified > 0 else 0.0
        pressure = cls._pressure(ratio)

        return ProfitRTDIncrementalAggressionSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            new_trade_count=len(trades),
            buyer_aggression=buy,
            seller_aggression=sell,
            rlp_quantity=rlp,
            classified_aggression=classified,
            total_traded_quantity=total,
            delta=delta,
            delta_ratio=ratio,
            pressure=pressure,
            continuity=continuity,
            baseline_only=baseline_only,
        )

    @classmethod
    def _pressure(cls, ratio: float) -> str:
        if ratio >= cls.PRESSURE_THRESHOLD:
            return "BUY"
        if ratio <= -cls.PRESSURE_THRESHOLD:
            return "SELL"
        return "BALANCED"

    @staticmethod
    def _positive_quantity(value) -> float:
        if isinstance(value, bool):
            raise TypeError("Quantidade deve ser numérica.")
        try:
            quantity = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Quantidade inválida.") from exc
        if quantity <= 0:
            raise ValueError("Quantidade deve ser positiva.")
        return quantity
