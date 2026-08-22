"""
analysis/book_diagnostics_engine.py

Book Diagnostics Engine RC5 - Experimental / Observational.

Executa diagnósticos passivos selecionados dos livros.
Não altera Strategy, Score, Risk, Decision nem execução.
"""

from ai.engine_base import EngineBase

from analysis.price_action.always_in_dynamics import AlwaysInDynamics
from analysis.price_action.trend_strength_dynamics import TrendStrengthDynamics
from analysis.price_action.breakout_strength_dynamics import BreakoutStrengthDynamics
from analysis.price_action.major_trend_reversal_dynamics import MajorTrendReversalDynamics
from analysis.price_action.wedge_reversal_dynamics import WedgeReversalDynamics


class BookDiagnosticsEngine(EngineBase):

    NAME = "BookDiagnostics"
    VERSION = "RC5-WEDGE-OBSERVATIONAL"
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
        self._synthesize(result)

        result.validate()
        result.add_reason("PASSIVE_DIAGNOSTICS_ONLY")
        result.add_reason("OBSERVATIONAL_PIPELINE_ONLY")
        result.add_reason("RC5_WEDGE_REVERSAL_EXPERIMENT")

        return context

    @staticmethod
    def _run_always_in(candles, result) -> None:
        metrics = AlwaysInDynamics().analyze(candles)
        result.always_in.update(metrics.to_dict())

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
        metrics = BreakoutStrengthDynamics().analyze(candles)
        result.breakout_strength.update(metrics.to_dict())

    @classmethod
    def _run_major_trend_reversal(cls, candles, context, result) -> None:
        old_trend = cls._normalize_old_trend(context.structure.trend)
        metrics = MajorTrendReversalDynamics().analyze(candles, old_trend)
        result.major_trend_reversal.update(metrics.to_dict())

    @classmethod
    def _run_wedge_reversal(cls, candles, context, result) -> None:
        old_trend = cls._normalize_old_trend(context.structure.trend)
        mtr_break = bool(result.major_trend_reversal.get("structural_break", False))
        metrics = WedgeReversalDynamics().analyze(
            candles,
            old_trend=old_trend,
            structural_break=mtr_break,
        )
        result.wedge_reversal.update(metrics.to_dict())

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
            BookDiagnosticsEngine._apply_reversal_overlay(result)
            BookDiagnosticsEngine._apply_wedge_overlay(result)
            return

        buy_count = sum(direction == "BUY" for direction, _ in observations)
        sell_count = sum(direction == "SELL" for direction, _ in observations)

        if buy_count > sell_count:
            bias = "BUY"
            majority = buy_count
            minority = sell_count
        elif sell_count > buy_count:
            bias = "SELL"
            majority = sell_count
            minority = buy_count
        else:
            bias = "NONE"
            majority = buy_count
            minority = sell_count

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
            valid and direction in {"BUY", "SELL"}
            and (structural_break or state.startswith("MTR_"))
        )
        result.reversal_confirmed = bool(
            valid and state == "MTR_CONFIRMED" and follow_through
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
            valid and direction in {"BUY", "SELL"}
            and push_count >= 3
            and (momentum_loss or state.startswith("WEDGE_") or state.startswith("THREE_PUSH_"))
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
