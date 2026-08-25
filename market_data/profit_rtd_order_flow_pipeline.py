"""Pipeline explícita T&T RTD -> dedup -> agressão -> OrderFlowState (RC7)."""

from __future__ import annotations

from dataclasses import dataclass

from market_data.profit_rtd_incremental_aggression import (
    ProfitRTDIncrementalAggressionBuilder,
)
from market_data.profit_rtd_order_flow_state_adapter import (
    ProfitRTDOrderFlowStateAdapter,
)
from market_data.profit_rtd_times_trades_deduplicator import (
    ProfitRTDTimesTradesDeduplicator,
)


@dataclass(frozen=True, slots=True)
class ProfitRTDOrderFlowPipelineReceipt:
    symbol: str
    timestamp: str
    continuity: str
    new_trade_count: int
    state_updated: bool
    baseline_reset: bool
    source_units: int
    source: str = "PROFIT_RTD"
    semantics: str = "EXPLICIT_TT_RTD_TO_ORDER_FLOW_STATE"
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDOrderFlowPipeline:
    """Cadeia explícita e opt-in; não é chamada automaticamente pelo Collector."""

    NAME = "ProfitRTDOrderFlowPipeline"
    VERSION = "RC7"

    def __init__(self, times_trades_reader, order_flow_state, *, deduplicator=None,
                 aggression_builder=None, state_adapter=None):
        if not callable(getattr(times_trades_reader, "read_times_trades", None)):
            raise TypeError("times_trades_reader deve expor read_times_trades().")
        self.reader = times_trades_reader
        self.deduplicator = deduplicator or ProfitRTDTimesTradesDeduplicator()
        self.aggression_builder = aggression_builder or ProfitRTDIncrementalAggressionBuilder
        self.state_adapter = state_adapter or ProfitRTDOrderFlowStateAdapter(order_flow_state)

    def process(self, symbol: str, *, price: float) -> ProfitRTDOrderFlowPipelineReceipt:
        payload = self.reader.read_times_trades(symbol)
        batch = self.deduplicator.observe(payload)
        snapshot = self.aggression_builder.build(batch)
        state_receipt = self.state_adapter.apply(snapshot, price=price)
        return ProfitRTDOrderFlowPipelineReceipt(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            continuity=snapshot.continuity,
            new_trade_count=snapshot.new_trade_count,
            state_updated=state_receipt.state_updated,
            baseline_reset=state_receipt.baseline_reset,
            source_units=state_receipt.source_units,
        )

    def clear(self) -> None:
        clear_dedup = getattr(self.deduplicator, "clear", None)
        if callable(clear_dedup):
            clear_dedup()
        clear_adapter = getattr(self.state_adapter, "clear", None)
        if callable(clear_adapter):
            clear_adapter()
