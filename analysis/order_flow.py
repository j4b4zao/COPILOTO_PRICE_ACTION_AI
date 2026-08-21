"""Análise informativa de Order Flow baseada somente em agressão real."""

from ai.engine_base import EngineBase


class OrderFlow(EngineBase):

    NAME = "OrderFlow"
    VERSION = "RC4.0"
    ENABLED = True
    PRIORITY = 45
    IMBALANCE_THRESHOLD = 0.10

    def executar(self, context):
        result = context.order_flow
        state = context.order_flow_state
        result.clear()
        result.start()
        result.source = "PROFIT_AGGRESSION"

        if state is None or not state.available:
            result.add_reason("ORDER_FLOW_DATA_UNAVAILABLE")
            result.skip()
            return context

        if not state.ready:
            result.add_reason("ORDER_FLOW_BASELINE_PENDING")
            result.skip()
            return context

        result.buy_aggression = state.buy_aggression
        result.sell_aggression = state.sell_aggression
        result.delta = state.delta
        result.total_aggression = state.total_aggression

        if state.total_aggression <= 0:
            result.pressure = "BALANCED"
            result.add_reason("NO_AGGRESSION_IN_INTERVAL")
            result.validate()
            return context

        result.imbalance_ratio = abs(state.delta) / state.total_aggression
        result.confidence = min(1.0, result.imbalance_ratio)

        if result.imbalance_ratio < self.IMBALANCE_THRESHOLD:
            result.pressure = "BALANCED"
            result.add_reason("BALANCED_AGGRESSION")
        elif state.delta > 0:
            result.pressure = "BUY"
            result.add_reason("BUY_AGGRESSION_DOMINANT")
        else:
            result.pressure = "SELL"
            result.add_reason("SELL_AGGRESSION_DOMINANT")

        result.validate()
        return context
