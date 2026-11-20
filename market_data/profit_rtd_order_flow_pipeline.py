"""Pipeline explícita T&T RTD -> dedup -> agressão -> OrderFlowState (RC7)."""

from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import dataclass, fields
from weakref import ref

from core.order_flow_state import OrderFlowState

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
        self.aggression_builder = aggression_builder or ProfitRTDIncrementalAggressionBuilder
        self._local_state = (
            deduplicator or ProfitRTDTimesTradesDeduplicator(),
            state_adapter or ProfitRTDOrderFlowStateAdapter(order_flow_state),
        )
        self._collector_ref = None

    def _bind_collector(self, collector):
        owner = self._collector_ref() if self._collector_ref is not None else None
        if owner is not None and owner is not collector:
            raise ValueError("RTD_PIPELINE_ALREADY_BOUND")
        if owner is None:
            self._collector_ref = ref(collector)

    def _accepted_state(self):
        owner = self._collector_ref() if self._collector_ref is not None else None
        return owner._rtd_state_for(self) if owner is not None else None

    def _state(self):
        return self._accepted_state() or self._local_state

    def _set_state(self, state):
        if self._accepted_state() is None:
            self._local_state = state
        else:
            self._collector_ref()._accepted_rtd_version = (self, state)

    @property
    def deduplicator(self):
        return self._state()[0]

    @deduplicator.setter
    def deduplicator(self, value):
        self._set_state((value, self.state_adapter))

    @property
    def state_adapter(self):
        return self._state()[1]

    @state_adapter.setter
    def state_adapter(self, value):
        self._set_state((self.deduplicator, value))

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

    def _fork(self, memo):
        """Isola o estado RTD e conserva os colaboradores configurados."""
        fork = copy(self)
        memo[id(self)] = fork
        # Reader and builder are callbacks, not versioned RTD state. Keep their
        # identity, as prepare() already does for a stand-alone pipeline.
        memo[id(self.reader)] = self.reader
        memo[id(self.aggression_builder)] = self.aggression_builder
        attributes = {**vars(self), "_collector_ref": None, "_local_state": self._state()}
        fork.__dict__ = deepcopy(attributes, memo)
        return fork

    def prepare(self, symbol: str, *, price: float, rebase: bool):
        """Calcula o ciclo sobre o estado auxiliar isolado, usando o leitor atual."""
        staged = copy(self)
        staged._collector_ref = None
        staged._local_state = deepcopy(self._state())
        if rebase:
            staged.clear()
        return staged, staged.process(symbol, price=price)

    def publish(self, staged) -> None:
        """Atualiza o estado compartilhado sem trocar sua identidade."""
        state = self.state_adapter.state
        for field in fields(OrderFlowState):
            setattr(state, field.name, getattr(staged.state_adapter.state, field.name))
        staged.state_adapter.state = state
        self._set_state((staged.deduplicator, staged.state_adapter))
