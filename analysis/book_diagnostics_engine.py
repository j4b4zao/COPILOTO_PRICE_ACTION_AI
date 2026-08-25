"""
analysis/book_diagnostics_engine.py

Book Diagnostics Engine RC7 - Observational synthesis.

Executa diagnósticos passivos selecionados dos livros e organiza o resultado
em Trend Control, Reversal Pressure e Market Environment.
Não altera Strategy, Score, Risk, Decision nem execução.
"""

from ai.engine_base import EngineBase

from analysis.price_action.always_in_dynamics import AlwaysInDynamics
from analysis.price_action.trend_strength_dynamics import TrendStrengthDynamics
from analysis.price_action.breakout_strength_dynamics import BreakoutStrengthDynamics
from analysis.price_action.major_trend_reversal_dynamics import MajorTrendReversalDynamics
from analysis.price_action.wedge_reversal_dynamics import WedgeReversalDynamics
from analysis.price_action.tight_trading_range_dynamics import TightTradingRangeDynamics


class BookDiagnosticsEngine(EngineBase):

    NAME = "BookDiagnostics"
    VERSION = "RC7-OBSERVATIONAL-SYNTHESIS"
    ENABLED = True
    PRIORITY = 55

    def executar(self, context):
        result = context.book_diagnostics
        result.clear()
        result.start()
        result.source = self.NAME

        market = context.market
        if not market.ready:
            result.skip()
            result.add_reason("MARKET_NOT_READY")
            return context

        candles = market.candles.all()
        if len(candles) < 2:
            result.skip()
            result.add_reason("INSUFFICIENT_CANDLES")
            return context

        self._run_always_in(candles, result)
        self._run_trend_strength(candles, context, result)
        self._run_breakout_strength(candles, result)
        self._run_major_trend_reversal(candles, context, result)
        self._run_wedge_reversal(candles, context, result)
        self._run_tight_trading_range(candles, result)
        self._synthesize(result)

        result.validate()
        result.add_reason("PASSIVE_DIAGNOSTICS_ONLY")
        result.add_reason("OBSERVATIONAL_PIPELINE_ONLY")
        result.add_reason("RC7_THREE_BLOCK_SYNTHESIS")
        return context

    @staticmethod
    def _run_always_in(candles, result) -> None:
        result.always_in.update(AlwaysInDynamics().analyze(candles).to_dict())

    @staticmethod
    def _run_trend_strength(candles, context, result) -> None:
        metrics = TrendStrengthDynamics.analyze(
            candles,
            context.structure.trend,
            result=context.price_action,
        )
        result.trend_strength.update(metrics)

    @staticmethod
    def _run_breakout_strength(candles, result) -> None:
        result.breakout_strength.update(
            BreakoutStrengthDynamics().analyze(candles).to_dict()
        )

    @classmethod
    def _run_major_trend_reversal(cls, candles, context, result) -> None:
        old_trend = cls._normalize_old_trend(context.structure.trend)
        result.major_trend_reversal.update(
            MajorTrendReversalDynamics().analyze(candles, old_trend).to_dict()
        )

    @classmethod
    def _run_wedge_reversal(cls, candles, context, result) -> None:
        old_trend = cls._normalize_old_trend(context.structure.trend)
        mtr_break = bool(result.major_trend_reversal.get("structural_break", False))
        result.wedge_reversal.update(
            WedgeReversalDynamics().analyze(
                candles,
                old_trend=old_trend,
                structural_break=mtr_break,
            ).to_dict()
        )

    @staticmethod
    def _run_tight_trading_range(candles, result) -> None:
        result.tight_trading_range.update(
            TightTradingRangeDynamics().analyze(candles).to_dict()
        )

    @staticmethod
    def _normalize_old_trend(value) -> str:
        if value is None:
            return "NONE"
        if hasattr(value, "name"):
            value = value.name
        text = str(value).upper().strip()
        if text in {"UP", "BUY", "LONG", "BULL", "BULLISH", "TREND_UP"}:
            return "UP"
        if text in {"DOWN", "SELL", "SHORT", "BEAR", "BEARISH", "TREND_DOWN"}:
            return "DOWN"
        return "NONE"

    @staticmethod
    def _synthesize(result) -> None:
        observations = []

        always_direction = str(result.always_in.get("direction", "NONE")).upper()
        always_score = float(result.always_in.get("quality_score", 0.0) or 0.0)
        if always_direction in {"BUY", "SELL"}:
            observations.append((always_direction, always_score))

        trend_direction = str(
            result.trend_strength.get("brooks_trend_strength_direction", "NONE")
        ).upper()
        trend_score = float(
            result.trend_strength.get("brooks_trend_strength_score", 0.0) or 0.0
        )
        if trend_direction in {"BUY", "SELL"}:
            observations.append((trend_direction, trend_score))

        breakout_valid = bool(result.breakout_strength.get("valid", False))
        breakout_direction = str(
            result.breakout_strength.get("direction", "NONE")
        ).upper()
        breakout_score = float(result.breakout_strength.get("score", 0.0) or 0.0)
        if breakout_valid and breakout_direction in {"BUY", "SELL"}:
            observations.append((breakout_direction, breakout_score))

        if not observations:
            result.directional_bias = "NONE"
            result.alignment = "NEUTRAL"
            result.add_reason("BOOK_ALIGNMENT_NEUTRAL")
        else:
            buy_count = sum(direction == "BUY" for direction, _ in observations)
            sell_count = sum(direction == "SELL" for direction, _ in observations)

            if buy_count > sell_count:
                bias, majority, minority = "BUY", buy_count, sell_count
            elif sell_count > buy_count:
                bias, majority, minority = "SELL", sell_count, buy_count
            else:
                bias, majority, minority = "NONE", buy_count, sell_count

            result.aligned_diagnostics = majority
            result.conflicting_diagnostics = minority

            if bias == "NONE":
                result.directional_bias = "NONE"
                result.alignment = "CONFLICT"
            else:
                result.directional_bias = bias
                if minority > 0:
                    result.alignment = "MAJORITY_WITH_CONFLICT"
                elif majority >= 3:
                    result.alignment = "FULL_ALIGNMENT"
                elif majority == 2:
                    result.alignment = "ALIGNED"
                else:
                    result.alignment = "PARTIAL"

            aligned_scores = [
                score
                for direction, score in observations
                if direction == result.directional_bias and score > 0.0
            ]
            if aligned_scores:
                base_quality = sum(aligned_scores) / len(aligned_scores)
                conflict_penalty = result.conflicting_diagnostics * 12.5
                result.quality_score = round(
                    max(0.0, min(100.0, base_quality - conflict_penalty)), 2
                )

            result.confidence = min(1.0, result.quality_score / 100.0)
            result.add_reason(f"BOOK_ALIGNMENT_{result.alignment}")

        BookDiagnosticsEngine._apply_reversal_overlay(result)
        BookDiagnosticsEngine._apply_wedge_overlay(result)
        BookDiagnosticsEngine._apply_tight_range_overlay(result)
        BookDiagnosticsEngine._build_rc7_synthesis(result)

    @staticmethod
    def _apply_reversal_overlay(result) -> None:
        mtr = result.major_trend_reversal
        valid = bool(mtr.get("valid", False))
        state = str(mtr.get("state", "NO_MTR")).upper()
        direction = str(mtr.get("reversal_direction", "NONE")).upper()
        quality = float(mtr.get("quality_score", 0.0) or 0.0)
        structural_break = bool(mtr.get("structural_break", False))
        follow_through = bool(mtr.get("follow_through", False))

        result.reversal_watch = bool(
            valid
            and direction in {"BUY", "SELL"}
            and (structural_break or state.startswith("MTR_"))
        )
        result.reversal_confirmed = bool(
            valid
            and state == "MTR_CONFIRMED"
            and follow_through
            and direction in {"BUY", "SELL"}
        )
        result.reversal_direction = direction if result.reversal_watch else "NONE"
        result.reversal_quality_score = round(quality, 2) if result.reversal_watch else 0.0
        result.trend_reversal_divergence = bool(
            result.reversal_watch
            and result.directional_bias in {"BUY", "SELL"}
            and result.reversal_direction != result.directional_bias
        )

        if result.trend_reversal_divergence:
            result.add_reason(
                "CONFIRMED_MTR_OPPOSES_DIRECTIONAL_BIAS"
                if result.reversal_confirmed
                else "MTR_WATCH_OPPOSES_DIRECTIONAL_BIAS"
            )
        if result.reversal_confirmed:
            result.add_reason("MTR_CONFIRMED_OBSERVATIONAL_ONLY")

    @staticmethod
    def _apply_wedge_overlay(result) -> None:
        wedge = result.wedge_reversal
        valid = bool(wedge.get("valid", False))
        state = str(wedge.get("state", "NO_WEDGE_REVERSAL")).upper()
        direction = str(wedge.get("reversal_direction", "NONE")).upper()
        quality = float(wedge.get("quality_score", 0.0) or 0.0)
        push_count = int(wedge.get("push_count", 0) or 0)
        momentum_loss = bool(wedge.get("momentum_loss", False))

        result.wedge_watch = bool(
            valid
            and direction in {"BUY", "SELL"}
            and push_count >= 3
            and (
                momentum_loss
                or state.startswith("WEDGE_")
                or state.startswith("THREE_PUSH_")
            )
        )
        result.wedge_confirmed = bool(
            result.wedge_watch
            and state == "WEDGE_REVERSAL_CONFIRMED"
            and bool(wedge.get("reversal_confirmed", False))
        )
        result.wedge_direction = direction if result.wedge_watch else "NONE"
        result.wedge_quality_score = round(quality, 2) if result.wedge_watch else 0.0

        result.mtr_wedge_confluence = bool(
            result.reversal_watch
            and result.wedge_watch
            and result.reversal_direction == result.wedge_direction
        )
        result.mtr_wedge_conflict = bool(
            result.reversal_watch
            and result.wedge_watch
            and result.reversal_direction != result.wedge_direction
        )

        if result.mtr_wedge_confluence:
            result.add_reason("MTR_WEDGE_REVERSAL_CONFLUENCE")
        if result.mtr_wedge_conflict:
            result.add_reason("MTR_WEDGE_REVERSAL_CONFLICT")
        if result.wedge_confirmed:
            result.add_reason("WEDGE_REVERSAL_CONFIRMED_OBSERVATIONAL_ONLY")

    @staticmethod
    def _apply_tight_range_overlay(result) -> None:
        tight = result.tight_trading_range
        valid = bool(tight.get("valid", False))
        state = str(tight.get("state", "NONE")).upper()
        no_trade_zone = bool(tight.get("no_trade_zone", False))
        breakout_confirmed = bool(tight.get("breakout_confirmed", False))
        breakout_direction = str(tight.get("breakout_direction", "NONE")).upper()
        width_atr = float(tight.get("range_width_atr", 0.0) or 0.0)
        overlap = float(tight.get("overlap_ratio", 0.0) or 0.0)
        barbwire = bool(tight.get("barbwire", False))

        result.tight_range_active = bool(
            valid
            and (no_trade_zone or state in {"TIGHT_TRADING_RANGE", "NO_TRADE_ZONE"})
        )
        result.no_trade_zone_watch = bool(valid and no_trade_zone)
        result.range_breakout_confirmed = bool(valid and breakout_confirmed)
        result.range_breakout_direction = (
            breakout_direction
            if result.range_breakout_confirmed and breakout_direction in {"UP", "DOWN"}
            else "NONE"
        )
        result.directional_signal_range_conflict = bool(
            result.tight_range_active and result.directional_bias in {"BUY", "SELL"}
        )

        penalty = 0.0
        if result.tight_range_active:
            penalty += 15.0
        if barbwire:
            penalty += 10.0
        if width_atr > 0.0 and width_atr <= 2.0:
            penalty += 5.0
        if overlap >= 0.80:
            penalty += 5.0
        result.range_quality_penalty = min(35.0, penalty)

        if result.directional_signal_range_conflict:
            result.add_reason("DIRECTIONAL_SIGNAL_INSIDE_TIGHT_RANGE")
        if result.no_trade_zone_watch:
            result.add_reason("TIGHT_RANGE_NO_TRADE_ZONE_OBSERVATIONAL_ONLY")
        if result.range_breakout_confirmed:
            result.add_reason(
                f"TIGHT_RANGE_BREAKOUT_CONFIRMED_{result.range_breakout_direction}"
            )

    @staticmethod
    def _build_rc7_synthesis(result) -> None:
        # ------------------------------------------------------
        # TREND CONTROL
        # ------------------------------------------------------
        if result.directional_bias not in {"BUY", "SELL"}:
            trend_state = "NEUTRAL" if result.alignment == "NEUTRAL" else "CONFLICTED"
        elif result.alignment == "FULL_ALIGNMENT" and result.quality_score >= 70.0:
            trend_state = "STRONG_CONTROL"
        elif result.alignment in {"FULL_ALIGNMENT", "ALIGNED"}:
            trend_state = "CONTROL"
        elif result.alignment == "MAJORITY_WITH_CONFLICT":
            trend_state = "CONTROL_WITH_CONFLICT"
        else:
            trend_state = "WEAK_CONTROL"

        result.trend_control.update(
            {
                "state": trend_state,
                "direction": result.directional_bias,
                "score": round(result.quality_score, 2),
                "aligned": result.aligned_diagnostics,
                "conflicting": result.conflicting_diagnostics,
            }
        )

        # ------------------------------------------------------
        # REVERSAL PRESSURE
        # ------------------------------------------------------
        reversal_scores = []
        reversal_directions = []
        if result.reversal_watch:
            reversal_scores.append(result.reversal_quality_score)
            reversal_directions.append(result.reversal_direction)
        if result.wedge_watch:
            reversal_scores.append(result.wedge_quality_score)
            reversal_directions.append(result.wedge_direction)

        if result.reversal_confirmed and result.wedge_confirmed and result.mtr_wedge_confluence:
            reversal_state = "CONFIRMED_CONFLUENCE"
        elif result.reversal_confirmed or result.wedge_confirmed:
            reversal_state = "CONFIRMED"
        elif result.mtr_wedge_confluence:
            reversal_state = "CONFLUENT_WATCH"
        elif result.mtr_wedge_conflict:
            reversal_state = "CONFLICTED_PRESSURE"
        elif result.reversal_watch or result.wedge_watch:
            reversal_state = "WATCH"
        else:
            reversal_state = "NONE"

        unique_reversal_directions = {
            direction for direction in reversal_directions if direction in {"BUY", "SELL"}
        }
        reversal_direction = (
            unique_reversal_directions.pop()
            if len(unique_reversal_directions) == 1
            else "NONE"
        )
        reversal_score = (
            round(sum(reversal_scores) / len(reversal_scores), 2)
            if reversal_scores
            else 0.0
        )

        result.reversal_pressure.update(
            {
                "state": reversal_state,
                "direction": reversal_direction,
                "score": reversal_score,
                "mtr_confirmed": result.reversal_confirmed,
                "wedge_confirmed": result.wedge_confirmed,
                "confluence": result.mtr_wedge_confluence,
                "conflict": result.mtr_wedge_conflict,
            }
        )

        # ------------------------------------------------------
        # MARKET ENVIRONMENT
        # ------------------------------------------------------
        if result.range_breakout_confirmed:
            environment_state = "RANGE_BREAKOUT"
        elif result.no_trade_zone_watch:
            environment_state = "TIGHT_RANGE_NO_TRADE_WATCH"
        elif result.tight_range_active:
            environment_state = "TIGHT_RANGE"
        else:
            environment_state = "NORMAL_OR_OTHER"

        favorability = round(max(0.0, 100.0 - result.range_quality_penalty), 2)
        result.market_environment.update(
            {
                "state": environment_state,
                "favorability": favorability,
                "range_penalty": round(result.range_quality_penalty, 2),
                "directional_conflict": result.directional_signal_range_conflict,
                "range_breakout_direction": result.range_breakout_direction,
            }
        )

        # ------------------------------------------------------
        # RESUMO RC7 - APENAS PARA REPLAY/A-B
        # ------------------------------------------------------
        caution_count = 0
        if result.conflicting_diagnostics:
            caution_count += 1
        if result.trend_reversal_divergence:
            caution_count += 1
        if result.mtr_wedge_conflict:
            caution_count += 1
        if result.directional_signal_range_conflict:
            caution_count += 1
        if result.no_trade_zone_watch:
            caution_count += 1
        result.caution_count = caution_count

        if result.directional_bias not in {"BUY", "SELL"}:
            synthesis_state = "NO_DIRECTIONAL_EDGE"
            synthesis_direction = "NONE"
        elif result.no_trade_zone_watch:
            synthesis_state = "DIRECTIONAL_EDGE_IN_POOR_ENVIRONMENT"
            synthesis_direction = result.directional_bias
        elif (
            reversal_direction in {"BUY", "SELL"}
            and reversal_direction != result.directional_bias
            and reversal_state in {"CONFIRMED", "CONFIRMED_CONFLUENCE", "CONFLUENT_WATCH"}
        ):
            synthesis_state = "TREND_REVERSAL_TENSION"
            synthesis_direction = result.directional_bias
        elif result.alignment == "FULL_ALIGNMENT" and caution_count == 0:
            synthesis_state = "CLEAN_DIRECTIONAL_CONTEXT"
            synthesis_direction = result.directional_bias
        elif caution_count > 0:
            synthesis_state = "DIRECTIONAL_CONTEXT_WITH_CAUTION"
            synthesis_direction = result.directional_bias
        else:
            synthesis_state = "DIRECTIONAL_CONTEXT"
            synthesis_direction = result.directional_bias

        result.synthesis_state = synthesis_state
        result.synthesis_direction = synthesis_direction

        raw_score = result.quality_score
        observational_penalty = min(
            60.0,
            result.range_quality_penalty + (caution_count * 7.5),
        )
        result.synthesis_score = round(
            max(0.0, min(100.0, raw_score - observational_penalty)),
            2,
        )

        result.add_reason(f"BOOK_SYNTHESIS_{result.synthesis_state}")
