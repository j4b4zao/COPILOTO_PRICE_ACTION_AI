"""Análise informativa de Order Flow baseada somente em agressão real."""

from ai.engine_base import EngineBase


class OrderFlow(EngineBase):

    NAME = "OrderFlow"
    VERSION = "RC5.1-PATTERN-STRUCTURE-EVIDENCE"
    ENABLED = True
    PRIORITY = 45
    IMBALANCE_THRESHOLD = 0.10
    EXHAUSTION_RATIO = 0.50
    CONFIRMATION_THRESHOLD = 0.60
    HIGH_QUALITY_THRESHOLD = 0.75
    MEDIUM_QUALITY_THRESHOLD = 0.50
    MATURE_HISTORY_SAMPLES = 20
    PERSISTENCE_THRESHOLD = 0.70
    IMPULSE_THRESHOLD = 0.20

    def executar(self, context):
        result = context.order_flow
        state = context.order_flow_state
        result.clear()
        result.start()
        result.source = "PROFIT_AGGRESSION"

        if state is not None:
            result.sampling_mode = state.sampling_mode
            result.source_units = state.source_units

        if state is None or not state.available:
            result.add_reason("ORDER_FLOW_DATA_UNAVAILABLE")
            result.skip()
            return context

        if not state.ready:
            if state.waiting_for_sample:
                result.add_reason("ORDER_FLOW_WAITING_RENKO_CLOSE")
            else:
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
        result.delta_persistence = state.delta_persistence
        result.delta_acceleration = state.delta_acceleration
        result.delta_impulse_ratio = state.delta_impulse_ratio

        if state.recent_delta > 0:
            result.trend = "BUYING"
        elif state.recent_delta < 0:
            result.trend = "SELLING"
        else:
            result.trend = "BALANCED"

        self._classify_flow_momentum(state, result)
        self._analyze_patterns(state, result, context)

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

    def _classify_flow_momentum(self, state, result) -> None:
        if state.sample_count < state.DYNAMICS_WINDOW * 2:
            result.flow_momentum = "INSUFFICIENT_DATA"
            result.add_reason("ORDER_FLOW_DYNAMICS_HISTORY_PENDING")
            return

        persistence = state.delta_persistence
        acceleration = state.delta_acceleration
        impulse = state.delta_impulse_ratio
        direction = 1 if state.recent_delta > 0 else -1 if state.recent_delta < 0 else 0

        if direction == 0 or persistence < self.PERSISTENCE_THRESHOLD:
            result.flow_momentum = "MIXED"
            result.add_reason("ORDER_FLOW_MOMENTUM_MIXED")
            return

        accelerating_same_direction = (
            direction > 0 and acceleration > 0
        ) or (
            direction < 0 and acceleration < 0
        )

        if accelerating_same_direction and impulse >= self.IMPULSE_THRESHOLD:
            result.flow_momentum = "ACCELERATING_BUY" if direction > 0 else "ACCELERATING_SELL"
            result.add_reason(result.flow_momentum)
        elif accelerating_same_direction:
            result.flow_momentum = "PERSISTENT_BUY" if direction > 0 else "PERSISTENT_SELL"
            result.add_reason(result.flow_momentum)
        else:
            result.flow_momentum = "FADING_BUY" if direction > 0 else "FADING_SELL"
            result.add_reason(result.flow_momentum)

    def _analyze_patterns(self, state, result, context) -> None:
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

        for pattern in (result.divergence, result.absorption, result.exhaustion):
            if pattern not in ("NONE", "INSUFFICIENT_DATA"):
                result.add_reason(pattern)

        self._qualify_patterns(state, result)
        self._qualify_structure(context, result)

    def _qualify_patterns(self, state, result) -> None:
        patterns = (result.divergence, result.absorption, result.exhaustion)

        if all(pattern == "NONE" for pattern in patterns):
            result.pattern_quality = "NONE"
            result.add_reason("ORDER_FLOW_NO_PATTERN")
            return

        result.delta_dominance = state.recent_delta_dominance
        result.price_efficiency = state.recent_price_efficiency
        result.history_maturity = min(1.0, state.sample_count / self.MATURE_HISTORY_SAMPLES)

        evidence_strength = result.delta_dominance
        if result.exhaustion != "NONE":
            exhaustion_strength = max(0.0, 1.0 - state.aggression_activity_ratio)
            evidence_strength = max(evidence_strength, exhaustion_strength)

        result.pattern_confidence = min(
            1.0,
            0.25 * result.history_maturity
            + 0.35 * result.price_efficiency
            + 0.40 * evidence_strength,
        )

        if result.pattern_confidence >= self.HIGH_QUALITY_THRESHOLD:
            result.pattern_quality = "HIGH"
        elif result.pattern_confidence >= self.MEDIUM_QUALITY_THRESHOLD:
            result.pattern_quality = "MEDIUM"
        else:
            result.pattern_quality = "LOW"

        result.pattern_confirmed = result.pattern_confidence >= self.CONFIRMATION_THRESHOLD
        if result.pattern_confirmed:
            result.add_reason("ORDER_FLOW_PATTERN_CONFIRMED")
        else:
            result.add_reason("ORDER_FLOW_PATTERN_LOW_CONFIDENCE")

    def _qualify_structure(self, context, result) -> None:
        result.pattern_direction = self._pattern_direction(result)
        if result.pattern_direction == "NONE":
            result.structure_alignment = "NEUTRAL"
            return

        structure = getattr(context, "market_structure", None)
        trend = str(getattr(structure, "trend", "") or "").upper()
        if not trend:
            result.structure_alignment = "UNAVAILABLE"
            return

        aligned = (
            result.pattern_direction == "BUY" and trend in {"BULLISH", "UP", "UPTREND", "TREND_UP"}
        ) or (
            result.pattern_direction == "SELL" and trend in {"BEARISH", "DOWN", "DOWNTREND", "TREND_DOWN"}
        )
        conflicting = (
            result.pattern_direction == "BUY" and trend in {"BEARISH", "DOWN", "DOWNTREND", "TREND_DOWN"}
        ) or (
            result.pattern_direction == "SELL" and trend in {"BULLISH", "UP", "UPTREND", "TREND_UP"}
        )

        if aligned:
            result.structure_alignment = "ALIGNED"
            multiplier = 1.0
            result.add_reason("ORDER_FLOW_PATTERN_STRUCTURE_ALIGNED")
        elif conflicting:
            result.structure_alignment = "CONFLICT"
            multiplier = 0.60
            result.add_reason("ORDER_FLOW_PATTERN_STRUCTURE_CONFLICT")
        else:
            result.structure_alignment = "NEUTRAL"
            multiplier = 0.80

        result.structural_pattern_confidence = min(1.0, result.pattern_confidence * multiplier)

    @staticmethod
    def _pattern_direction(result) -> str:
        if result.absorption == "BUY_ABSORPTION" or result.exhaustion == "SELL_EXHAUSTION":
            return "BUY"
        if result.absorption == "SELL_ABSORPTION" or result.exhaustion == "BUY_EXHAUSTION":
            return "SELL"
        return "NONE"
