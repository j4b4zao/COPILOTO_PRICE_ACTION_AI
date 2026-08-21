"""
models/price_action_result.py

Resultado produzido pela PriceAction.

RC7.15 - MICROCHANNELS
"""

from dataclasses import dataclass

from enums.trend import Trend
from models.result_base import ResultBase


@dataclass(slots=True)
class PriceActionResult(ResultBase):

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    trend: Trend = Trend.UNKNOWN

    bias: str = "NONE"

    structure: str = ""

    # ==========================================================
    # ESTRUTURA
    # ==========================================================

    bos: bool = False

    choch: bool = False

    last_high: float = 0.0

    last_low: float = 0.0

    # ==========================================================
    # PADRÕES
    # ==========================================================

    bullish_engulfing: bool = False

    bearish_engulfing: bool = False

    hammer: bool = False

    shooting_star: bool = False

    doji: bool = False

    inside_bar: bool = False

    outside_bar: bool = False

    # ==========================================================
    # DINÂMICA DA BARRA - BROOKS TRENDS CAP. 2
    # ==========================================================

    bar_classification: str = "UNKNOWN"

    bar_direction: str = "NONE"

    body_ratio: float = 0.0

    relative_body_ratio: float = 0.0

    close_position: float = 0.5

    trend_bar_strength: str = "UNKNOWN"

    climax_direction: str = "NONE"

    climax_length: int = 0

    climax_active: bool = False

    climax_ended: bool = False

    pause_detected: bool = False

    # ==========================================================
    # CICLO DO ROMPIMENTO - BROOKS TRENDS CAP. 3
    # ==========================================================

    brooks_breakout_phase: str = "UNKNOWN"

    brooks_breakout_direction: str = "NONE"

    brooks_breakout_level: float = 0.0

    brooks_breakout_penetration: float = 0.0

    brooks_breakout_distance: float = 0.0

    brooks_breakout_follow_through: bool = False

    brooks_breakout_tested: bool = False

    brooks_breakout_failed: bool = False

    brooks_range_high: float = 0.0

    brooks_range_low: float = 0.0

    # ==========================================================
    # CICLO SINAL / ENTRADA - BROOKS TRENDS CAP. 4
    # ==========================================================

    brooks_signal_phase: str = "UNKNOWN"

    brooks_signal_direction: str = "NONE"

    brooks_signal_quality: str = "UNKNOWN"

    brooks_signal_context: str = "NEUTRAL"

    brooks_entry_level: float = 0.0

    brooks_entry_triggered: bool = False

    brooks_follow_through: bool = False

    brooks_follow_through_strength: str = "NONE"

    # ==========================================================
    # BARRA DE REVERSÃO - BROOKS TRENDS CAP. 5
    # ==========================================================

    brooks_reversal_candidate: bool = False

    brooks_reversal_direction: str = "NONE"

    brooks_reversal_quality: str = "NONE"

    brooks_reversal_context: str = "NEUTRAL"

    brooks_reversal_body_ratio: float = 0.0

    brooks_reversal_tail_ratio: float = 0.0

    brooks_reversal_opposite_tail_ratio: float = 0.0

    brooks_reversal_overlap_ratio: float = 0.0

    brooks_reversal_relative_range: float = 0.0

    brooks_reversal_reversed_closes: int = 0

    brooks_reversal_reversed_extremes: int = 0

    brooks_reversal_excessive_overlap: bool = False

    brooks_reversal_large_doji_risk: bool = False

    # ==========================================================
    # PADRÕES COMPOSTOS - BROOKS TRENDS CAP. 6
    # ==========================================================

    brooks_composite_pattern: str = "NONE"

    brooks_composite_direction: str = "NONE"

    brooks_two_bar_reversal: bool = False

    brooks_two_bar_direction: str = "NONE"

    brooks_three_bar_reversal: bool = False

    brooks_three_bar_direction: str = "NONE"

    brooks_inside_sequence_count: int = 0

    brooks_ioi_pattern: bool = False

    brooks_micro_double_bottom: bool = False

    brooks_micro_double_top: bool = False

    brooks_failed_reversal: bool = False

    brooks_failed_reversal_direction: str = "NONE"

    brooks_shaved_top: bool = False

    brooks_shaved_bottom: bool = False

    brooks_shaved_trend_bar: bool = False

    brooks_exhaustion_bar: bool = False

    brooks_composite_context: str = "NEUTRAL"

    # ==========================================================
    # BARRA EXTERNA - BROOKS TRENDS CAP. 7
    # ==========================================================

    brooks_outside_detected: bool = False

    brooks_outside_direction: str = "NONE"

    brooks_outside_classification: str = "NONE"

    brooks_outside_quality: str = "NONE"

    brooks_outside_context: str = "NEUTRAL"

    brooks_outside_close_position: float = 0.5

    brooks_outside_body_ratio: float = 0.0

    brooks_outside_expansion_ratio: float = 0.0

    brooks_outside_balanced: bool = False

    brooks_outside_range_like: bool = False

    brooks_outside_trapped_side: str = "NONE"

    brooks_double_outside: bool = False

    brooks_outside_follow_through: bool = False

    brooks_outside_failed: bool = False

    # ==========================================================
    # QUALIDADE DO FECHAMENTO - BROOKS TRENDS CAP. 8
    # ==========================================================

    brooks_close_state: str = "UNKNOWN"

    brooks_close_direction: str = "NEUTRAL"

    brooks_close_quality: str = "UNKNOWN"

    brooks_close_context: str = "NEUTRAL"

    brooks_close_position: float = 0.5

    brooks_close_distance_to_extreme: float = 0.5

    brooks_close_body_ratio: float = 0.0

    brooks_close_progress: float = 0.0

    brooks_close_reversed_closes: int = 0

    brooks_close_consistency: int = 0

    brooks_close_near_extreme: bool = False

    brooks_close_follow_through: bool = False

    brooks_close_deterioration: bool = False

    brooks_close_confirmed: bool = False

    # ==========================================================
    # PERSPECTIVA DO GRÁFICO - BROOKS TRENDS CAP. 9
    # ==========================================================

    brooks_perspective_state: str = "UNKNOWN"

    brooks_perspective_direction: str = "NEUTRAL"

    brooks_perspective_inverse_direction: str = "NEUTRAL"

    brooks_perspective_clarity: str = "UNKNOWN"

    brooks_perspective_efficiency: float = 0.0

    brooks_perspective_consistency: float = 0.0

    brooks_perspective_inverse_consistent: bool = False

    brooks_perspective_confirmed: bool = False

    # ==========================================================
    # SEGUNDA ENTRADA - BROOKS TRENDS CAP. 10
    # ==========================================================

    brooks_second_entry_phase: str = "NONE"

    brooks_second_entry_direction: str = "NONE"

    brooks_second_entry_context: str = "NEUTRAL"

    brooks_second_entry_quality: str = "NONE"

    brooks_second_entry_attempt_count: int = 0

    brooks_second_entry_first_level: float = 0.0

    brooks_second_entry_level: float = 0.0

    brooks_second_entry_price_relation: str = "NONE"

    brooks_second_entry_bargain_risk: bool = False

    brooks_second_entry_opposing_momentum: bool = False

    brooks_second_entry_detected: bool = False

    brooks_second_entry_confirmed: bool = False

    # ==========================================================
    # ENTRADA TARDIA / PERDIDA - BROOKS TRENDS CAP. 11
    # ==========================================================

    brooks_late_entry_state: str = "NO_CLEAR_TREND"

    brooks_late_entry_direction: str = "NONE"

    brooks_late_entry_trend_bars: int = 0

    brooks_late_entry_efficiency: float = 0.0

    brooks_late_entry_range_ratio: float = 0.0

    brooks_late_entry_stop_reference: float = 0.0

    brooks_late_entry_stop_distance: float = 0.0

    brooks_late_entry_missed: bool = False

    brooks_late_entry_candidate: bool = False

    brooks_late_entry_pullback_available: bool = False

    brooks_late_entry_climax_risk: bool = False

    brooks_late_entry_reduce_position: bool = False

    brooks_late_entry_confirmed: bool = False

    # ==========================================================
    # EVOLUÇÃO DE PADRÕES - BROOKS TRENDS CAP. 12
    # ==========================================================

    brooks_evolution_state: str = "STABLE"

    brooks_evolution_original_pattern: str = "NONE"

    brooks_evolution_pattern: str = "NONE"

    brooks_evolution_direction: str = "NONE"

    brooks_evolution_failure: bool = False

    brooks_evolution_expanded: bool = False

    brooks_evolution_breakout_mode: bool = False

    brooks_evolution_trapped_side: str = "NONE"

    brooks_evolution_confirmed: bool = False

    # ==========================================================
    # LINHA DE TENDÊNCIA - BROOKS TRENDS CAP. 13
    # ==========================================================

    brooks_trend_line_state: str = "NO_CLEAR_TREND"

    brooks_trend_line_direction: str = "NONE"

    brooks_trend_line_slope: float = 0.0

    brooks_trend_line_level: float = 0.0

    brooks_trend_line_distance: float = 0.0

    brooks_trend_line_tolerance: float = 0.0

    brooks_trend_line_touch_count: int = 0

    brooks_trend_line_tested: bool = False

    brooks_trend_line_rejected: bool = False

    brooks_trend_line_broken: bool = False

    brooks_trend_line_break_strength: float = 0.0

    brooks_trend_line_two_sided_risk: bool = False

    brooks_trend_line_valid: bool = False

    # ==========================================================
    # LINHA DE CANAL - BROOKS TRENDS CAP. 14
    # ==========================================================

    brooks_channel_line_state: str = "NO_CLEAR_TREND"

    brooks_channel_line_direction: str = "NONE"

    brooks_channel_line_slope: float = 0.0

    brooks_channel_line_trend_level: float = 0.0

    brooks_channel_line_level: float = 0.0

    brooks_channel_line_width: float = 0.0

    brooks_channel_line_position: float = 0.5

    brooks_channel_line_tolerance: float = 0.0

    brooks_channel_line_overshoot_distance: float = 0.0

    brooks_channel_line_tested: bool = False

    brooks_channel_line_overshoot: bool = False

    brooks_channel_line_returned_inside: bool = False

    brooks_channel_line_accelerating: bool = False

    brooks_channel_line_reversal_candidate: bool = False

    brooks_channel_line_valid: bool = False

    # ==========================================================
    # COMPORTAMENTO DO CANAL - BROOKS TRENDS CAP. 15
    # ==========================================================

    brooks_channel_state: str = "NO_CHANNEL"

    brooks_channel_classification: str = "NONE"

    brooks_channel_behavior: str = "NONE"

    brooks_channel_direction: str = "NONE"

    brooks_channel_location: str = "MIDDLE"

    brooks_channel_width_ratio: float = 0.0

    brooks_channel_slope_strength: float = 0.0

    brooks_channel_overlap: float = 0.0

    brooks_channel_pushes: int = 0

    brooks_channel_outer_zone: bool = False

    brooks_channel_third_push_risk: bool = False

    brooks_channel_two_sided: bool = False

    brooks_channel_countertrend_risk: bool = False

    brooks_channel_measured_target: float = 0.0

    brooks_channel_valid: bool = False

    # ==========================================================
    # MICROCANAIS - BROOKS TRENDS CAP. 16
    # ==========================================================

    brooks_microchannel_state: str = "NO_MICROCHANNEL"

    brooks_microchannel_direction: str = "NONE"

    brooks_microchannel_strength: str = "NONE"

    brooks_microchannel_bar_count: int = 0

    brooks_microchannel_pullback_count: int = 0

    brooks_microchannel_quality: float = 0.0

    brooks_microchannel_overlap: float = 0.0

    brooks_microchannel_first_break: bool = False

    brooks_microchannel_break_direction: str = "NONE"

    brooks_microchannel_first_break_failure_risk: bool = False

    brooks_microchannel_retest_level: float = 0.0

    brooks_microchannel_active: bool = False

    brooks_microchannel_valid: bool = False

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    breakout: bool = False

    pullback: bool = False

    continuation: bool = False

    rejection: bool = False

    fake_breakout: bool = False

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    score: float = 0.0

    confluences: int = 0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        # Limpa os campos da classe base
        ResultBase.clear(self)

        # Contexto
        self.trend = Trend.UNKNOWN

        self.bias = "NONE"

        self.structure = ""

        # Estrutura
        self.bos = False

        self.choch = False

        self.last_high = 0.0

        self.last_low = 0.0

        # Padrões
        self.bullish_engulfing = False

        self.bearish_engulfing = False

        self.hammer = False

        self.shooting_star = False

        self.doji = False

        self.inside_bar = False

        self.outside_bar = False

        self.bar_classification = "UNKNOWN"

        self.bar_direction = "NONE"

        self.body_ratio = 0.0

        self.relative_body_ratio = 0.0

        self.close_position = 0.5

        self.trend_bar_strength = "UNKNOWN"

        self.climax_direction = "NONE"

        self.climax_length = 0

        self.climax_active = False

        self.climax_ended = False

        self.pause_detected = False

        self.brooks_breakout_phase = "UNKNOWN"

        self.brooks_breakout_direction = "NONE"

        self.brooks_breakout_level = 0.0

        self.brooks_breakout_penetration = 0.0

        self.brooks_breakout_distance = 0.0

        self.brooks_breakout_follow_through = False

        self.brooks_breakout_tested = False

        self.brooks_breakout_failed = False

        self.brooks_range_high = 0.0

        self.brooks_range_low = 0.0

        self.brooks_signal_phase = "UNKNOWN"

        self.brooks_signal_direction = "NONE"

        self.brooks_signal_quality = "UNKNOWN"

        self.brooks_signal_context = "NEUTRAL"

        self.brooks_entry_level = 0.0

        self.brooks_entry_triggered = False

        self.brooks_follow_through = False

        self.brooks_follow_through_strength = "NONE"

        self.brooks_reversal_candidate = False

        self.brooks_reversal_direction = "NONE"

        self.brooks_reversal_quality = "NONE"

        self.brooks_reversal_context = "NEUTRAL"

        self.brooks_reversal_body_ratio = 0.0

        self.brooks_reversal_tail_ratio = 0.0

        self.brooks_reversal_opposite_tail_ratio = 0.0

        self.brooks_reversal_overlap_ratio = 0.0

        self.brooks_reversal_relative_range = 0.0

        self.brooks_reversal_reversed_closes = 0

        self.brooks_reversal_reversed_extremes = 0

        self.brooks_reversal_excessive_overlap = False

        self.brooks_reversal_large_doji_risk = False

        self.brooks_composite_pattern = "NONE"

        self.brooks_composite_direction = "NONE"

        self.brooks_two_bar_reversal = False

        self.brooks_two_bar_direction = "NONE"

        self.brooks_three_bar_reversal = False

        self.brooks_three_bar_direction = "NONE"

        self.brooks_inside_sequence_count = 0

        self.brooks_ioi_pattern = False

        self.brooks_micro_double_bottom = False

        self.brooks_micro_double_top = False

        self.brooks_failed_reversal = False

        self.brooks_failed_reversal_direction = "NONE"

        self.brooks_shaved_top = False

        self.brooks_shaved_bottom = False

        self.brooks_shaved_trend_bar = False

        self.brooks_exhaustion_bar = False

        self.brooks_composite_context = "NEUTRAL"

        self.brooks_outside_detected = False

        self.brooks_outside_direction = "NONE"

        self.brooks_outside_classification = "NONE"

        self.brooks_outside_quality = "NONE"

        self.brooks_outside_context = "NEUTRAL"

        self.brooks_outside_close_position = 0.5

        self.brooks_outside_body_ratio = 0.0

        self.brooks_outside_expansion_ratio = 0.0

        self.brooks_outside_balanced = False

        self.brooks_outside_range_like = False

        self.brooks_outside_trapped_side = "NONE"

        self.brooks_double_outside = False

        self.brooks_outside_follow_through = False

        self.brooks_outside_failed = False

        self.brooks_close_state = "UNKNOWN"

        self.brooks_close_direction = "NEUTRAL"

        self.brooks_close_quality = "UNKNOWN"

        self.brooks_close_context = "NEUTRAL"

        self.brooks_close_position = 0.5

        self.brooks_close_distance_to_extreme = 0.5

        self.brooks_close_body_ratio = 0.0

        self.brooks_close_progress = 0.0

        self.brooks_close_reversed_closes = 0

        self.brooks_close_consistency = 0

        self.brooks_close_near_extreme = False

        self.brooks_close_follow_through = False

        self.brooks_close_deterioration = False

        self.brooks_close_confirmed = False

        self.brooks_perspective_state = "UNKNOWN"

        self.brooks_perspective_direction = "NEUTRAL"

        self.brooks_perspective_inverse_direction = "NEUTRAL"

        self.brooks_perspective_clarity = "UNKNOWN"

        self.brooks_perspective_efficiency = 0.0

        self.brooks_perspective_consistency = 0.0

        self.brooks_perspective_inverse_consistent = False

        self.brooks_perspective_confirmed = False

        self.brooks_second_entry_phase = "NONE"

        self.brooks_second_entry_direction = "NONE"

        self.brooks_second_entry_context = "NEUTRAL"

        self.brooks_second_entry_quality = "NONE"

        self.brooks_second_entry_attempt_count = 0

        self.brooks_second_entry_first_level = 0.0

        self.brooks_second_entry_level = 0.0

        self.brooks_second_entry_price_relation = "NONE"

        self.brooks_second_entry_bargain_risk = False

        self.brooks_second_entry_opposing_momentum = False

        self.brooks_second_entry_detected = False

        self.brooks_second_entry_confirmed = False

        self.brooks_late_entry_state = "NO_CLEAR_TREND"

        self.brooks_late_entry_direction = "NONE"

        self.brooks_late_entry_trend_bars = 0

        self.brooks_late_entry_efficiency = 0.0

        self.brooks_late_entry_range_ratio = 0.0

        self.brooks_late_entry_stop_reference = 0.0

        self.brooks_late_entry_stop_distance = 0.0

        self.brooks_late_entry_missed = False

        self.brooks_late_entry_candidate = False

        self.brooks_late_entry_pullback_available = False

        self.brooks_late_entry_climax_risk = False

        self.brooks_late_entry_reduce_position = False

        self.brooks_late_entry_confirmed = False

        self.brooks_evolution_state = "STABLE"

        self.brooks_evolution_original_pattern = "NONE"

        self.brooks_evolution_pattern = "NONE"

        self.brooks_evolution_direction = "NONE"

        self.brooks_evolution_failure = False

        self.brooks_evolution_expanded = False

        self.brooks_evolution_breakout_mode = False

        self.brooks_evolution_trapped_side = "NONE"

        self.brooks_evolution_confirmed = False

        self.brooks_trend_line_state = "NO_CLEAR_TREND"

        self.brooks_trend_line_direction = "NONE"

        self.brooks_trend_line_slope = 0.0

        self.brooks_trend_line_level = 0.0

        self.brooks_trend_line_distance = 0.0

        self.brooks_trend_line_tolerance = 0.0

        self.brooks_trend_line_touch_count = 0

        self.brooks_trend_line_tested = False

        self.brooks_trend_line_rejected = False

        self.brooks_trend_line_broken = False

        self.brooks_trend_line_break_strength = 0.0

        self.brooks_trend_line_two_sided_risk = False

        self.brooks_trend_line_valid = False

        self.brooks_channel_line_state = "NO_CLEAR_TREND"

        self.brooks_channel_line_direction = "NONE"

        self.brooks_channel_line_slope = 0.0

        self.brooks_channel_line_trend_level = 0.0

        self.brooks_channel_line_level = 0.0

        self.brooks_channel_line_width = 0.0

        self.brooks_channel_line_position = 0.5

        self.brooks_channel_line_tolerance = 0.0

        self.brooks_channel_line_overshoot_distance = 0.0

        self.brooks_channel_line_tested = False

        self.brooks_channel_line_overshoot = False

        self.brooks_channel_line_returned_inside = False

        self.brooks_channel_line_accelerating = False

        self.brooks_channel_line_reversal_candidate = False

        self.brooks_channel_line_valid = False

        self.brooks_channel_state = "NO_CHANNEL"

        self.brooks_channel_classification = "NONE"

        self.brooks_channel_behavior = "NONE"

        self.brooks_channel_direction = "NONE"

        self.brooks_channel_location = "MIDDLE"

        self.brooks_channel_width_ratio = 0.0

        self.brooks_channel_slope_strength = 0.0

        self.brooks_channel_overlap = 0.0

        self.brooks_channel_pushes = 0

        self.brooks_channel_outer_zone = False

        self.brooks_channel_third_push_risk = False

        self.brooks_channel_two_sided = False

        self.brooks_channel_countertrend_risk = False

        self.brooks_channel_measured_target = 0.0

        self.brooks_channel_valid = False

        self.brooks_microchannel_state = "NO_MICROCHANNEL"

        self.brooks_microchannel_direction = "NONE"

        self.brooks_microchannel_strength = "NONE"

        self.brooks_microchannel_bar_count = 0

        self.brooks_microchannel_pullback_count = 0

        self.brooks_microchannel_quality = 0.0

        self.brooks_microchannel_overlap = 0.0

        self.brooks_microchannel_first_break = False

        self.brooks_microchannel_break_direction = "NONE"

        self.brooks_microchannel_first_break_failure_risk = False

        self.brooks_microchannel_retest_level = 0.0

        self.brooks_microchannel_active = False

        self.brooks_microchannel_valid = False

        # Price Action
        self.breakout = False

        self.pullback = False

        self.continuation = False

        self.rejection = False

        self.fake_breakout = False

        # Estatísticas
        self.score = 0.0

        self.confluences = 0
