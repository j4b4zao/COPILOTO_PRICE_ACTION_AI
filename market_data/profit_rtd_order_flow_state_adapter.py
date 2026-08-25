"""Ponte controlada do T&T RTD deduplicado para OrderFlowState (RC6)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfitRTDOrderFlowStateAdapterReceipt:
    symbol: str
    timestamp: str
    continuity: str
    state_updated: bool
    baseline_reset: bool
    cumulative_buy: float
    cumulative_sell: float
    source_units: int
    source: str = "PROFIT_RTD"
    semantics: str = "DEDUPLICATED_LOCAL_CUMULATIVES_TO_ORDER_FLOW_STATE"
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDOrderFlowStateAdapter:
    """Alimenta OrderFlowState apenas com cumulativos locais derivados do RC5."""

    NAME = "ProfitRTDOrderFlowStateAdapter"
    VERSION = "RC6"
    SAMPLING_MODE = "PROFIT_RTD_TT"

    def __init__(self, state):
        required = ("update", "clear", "mark_waiting")
        if any(not callable(getattr(state, name, None)) for name in required):
            raise TypeError("state deve ser compatível com OrderFlowState.")
        self.state = state
        self._symbol: str | None = None
        self._cumulative_buy = 0.0
        self._cumulative_sell = 0.0

    def clear(self) -> None:
        self._symbol = None
        self._cumulative_buy = 0.0
        self._cumulative_sell = 0.0
        self.state.clear()

    def apply(self, snapshot, *, price: float):
        self._validate_snapshot(snapshot)
        valid_price = self._positive_price(price)
        symbol = snapshot.symbol
        continuity = snapshot.continuity

        must_reset = (
            self._symbol is None
            or symbol != self._symbol
            or snapshot.baseline_only
            or continuity in {"SYMBOL_RESET", "OVERLAP_LOST_REBASE", "BASELINE_ESTABLISHED"}
        )

        if must_reset:
            self._symbol = symbol
            self._cumulative_buy = 0.0
            self._cumulative_sell = 0.0
            self.state.clear()
            self.state.update(
                cumulative_buy=0.0,
                cumulative_sell=0.0,
                price=valid_price,
                sampling_mode=self.SAMPLING_MODE,
                source_units=0,
            )
            return self._receipt(snapshot, state_updated=False, baseline_reset=True, source_units=0)

        if snapshot.new_trade_count <= 0:
            self.state.mark_waiting("RTD_NO_NEW_TRADES")
            return self._receipt(snapshot, state_updated=False, baseline_reset=False, source_units=0)

        self._cumulative_buy += float(snapshot.buyer_aggression)
        self._cumulative_sell += float(snapshot.seller_aggression)
        updated = bool(
            self.state.update(
                cumulative_buy=self._cumulative_buy,
                cumulative_sell=self._cumulative_sell,
                price=valid_price,
                sampling_mode=self.SAMPLING_MODE,
                source_units=int(snapshot.new_trade_count),
            )
        )
        return self._receipt(
            snapshot,
            state_updated=updated,
            baseline_reset=False,
            source_units=int(snapshot.new_trade_count),
        )

    @staticmethod
    def _validate_snapshot(snapshot) -> None:
        if not getattr(snapshot, "observational_only", False):
            raise ValueError("Snapshot deve permanecer observacional.")
        if getattr(snapshot, "state_update_allowed", True):
            raise ValueError("RC6 exige snapshot RC5 com state_update_allowed=False.")
        if getattr(snapshot, "score_influence_allowed", True):
            raise ValueError("Snapshot não pode influenciar Score.")
        if getattr(snapshot, "decision_influence_allowed", True):
            raise ValueError("Snapshot não pode influenciar Decision.")
        if getattr(snapshot, "order_execution_allowed", True):
            raise ValueError("Snapshot não pode executar ordens.")
        symbol = str(getattr(snapshot, "symbol", "") or "").strip().upper()
        continuity = str(getattr(snapshot, "continuity", "") or "").strip()
        if not symbol or not continuity:
            raise ValueError("Snapshot RC5 incompleto.")
        for name in ("buyer_aggression", "seller_aggression"):
            value = float(getattr(snapshot, name, -1.0))
            if value < 0:
                raise ValueError(f"{name} não pode ser negativo.")

    @staticmethod
    def _positive_price(value) -> float:
        if isinstance(value, bool):
            raise TypeError("Preço deve ser numérico.")
        try:
            price = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Preço inválido.") from exc
        if price <= 0:
            raise ValueError("Preço deve ser positivo.")
        return price

    def _receipt(self, snapshot, *, state_updated: bool, baseline_reset: bool, source_units: int):
        return ProfitRTDOrderFlowStateAdapterReceipt(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            continuity=snapshot.continuity,
            state_updated=state_updated,
            baseline_reset=baseline_reset,
            cumulative_buy=self._cumulative_buy,
            cumulative_sell=self._cumulative_sell,
            source_units=source_units,
        )
