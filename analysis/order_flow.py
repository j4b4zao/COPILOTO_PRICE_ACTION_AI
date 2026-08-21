"""Análise informativa de Order Flow baseada somente em agressão real."""

from ai.engine_base import EngineBase


class OrderFlow(EngineBase):

    NAME = "OrderFlow"
    VERSION = "RC4.2"
    ENABLED = True
    PRIORITY = 45
    IMBALANCE_THRESHOLD = 0.10
    EXHAUSTION_RATIO = 0.50

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
        result.cumulative_delta = state.cumulative_delta
        result.recent_delta = state.recent_delta
        result.average_delta = state.average_delta
        result.sample_count = state.sample_count

        if state.recent_delta > 0:
            result.trend = "BUYING"
        elif state.recent_delta < 0:
            result.trend = "SELLING"
        else:
            result.trend = "BALANCED"

        self._analyze_patterns(state, result)

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

    def _analyze_patterns(self, state, result) -> None:
        if not state.pattern_ready:
            result.add_reason("ORDER_FLOW_PATTERN_HISTORY_PENDING")
            return

        result.patterns_ready = True
        result.recent_price_change = state.recent_price_change
        result.aggression_activity_ratio = state.aggression_activity_ratio
        result.divergence = "NONE"
        result.absorption = "NONE"
        result.exhaustion = "NONE"

        if state.recent_price_change > 0 and state.recent_delta < 0:
            result.divergence = "PRICE_UP_DELTA_DOWN"
            result.absorption = "BUY_ABSORPTION"
        elif state.recent_price_change < 0 and state.recent_delta > 0:
            result.divergence = "PRICE_DOWN_DELTA_UP"
            result.absorption = "SELL_ABSORPTION"
        elif state.recent_price_change == 0 and state.recent_delta < 0:
            result.absorption = "BUY_ABSORPTION"
        elif state.recent_price_change == 0 and state.recent_delta > 0:
            result.absorption = "SELL_ABSORPTION"

        if 0 < state.aggression_activity_ratio <= self.EXHAUSTION_RATIO:
            if state.recent_price_change > 0:
                result.exhaustion = "BUY_EXHAUSTION"
            elif state.recent_price_change < 0:
                result.exhaustion = "SELL_EXHAUSTION"

        for pattern in (
            result.divergence,
            result.absorption,
            result.exhaustion,
        ):
            if pattern not in ("NONE", "INSUFFICIENT_DATA"):
                result.add_reason(pattern)
