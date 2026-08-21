"""
models/price_action_result.py

Resultado produzido pela PriceAction.

RC7.7 - CLOSE QUALITY
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

        # Price Action
        self.breakout = False

        self.pullback = False

        self.continuation = False

        self.rejection = False

        self.fake_breakout = False

        # Estatísticas
        self.score = 0.0

        self.confluences = 0
