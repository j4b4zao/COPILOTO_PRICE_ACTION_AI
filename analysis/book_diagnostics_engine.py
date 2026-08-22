"""
analysis/book_diagnostics_engine.py

Book Diagnostics Engine RC3 - Experimental / Observational.

Executa diagnósticos passivos selecionados dos livros.
Não altera Strategy, Score, Risk, Decision nem execução.
"""

from ai.engine_base import EngineBase

from analysis.price_action.always_in_dynamics import AlwaysInDynamics
from analysis.price_action.trend_strength_dynamics import TrendStrengthDynamics
from analysis.price_action.breakout_strength_dynamics import BreakoutStrengthDynamics


class BookDiagnosticsEngine(EngineBase):

    NAME = "BookDiagnostics"
    VERSION = "RC3-EXPERIMENTAL"
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
        self._synthesize(result)

        result.validate()
        result.add_reason("PASSIVE_DIAGNOSTICS_ONLY")
        result.add_reason("OBSERVATIONAL_PIPELINE_ONLY")
        result.add_reason("RC3_BREAKOUT_STRENGTH_EXPERIMENT")

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

    @staticmethod
    def _synthesize(result) -> None:

        observations = []

        always_direction = str(
            result.always_in.get("direction", "NONE")
        ).upper()
        always_score = float(
            result.always_in.get("quality_score", 0.0) or 0.0
        )
        if always_direction in {"BUY", "SELL"}:
            observations.append((always_direction, always_score))

        trend_direction = str(
            result.trend_strength.get(
                "brooks_trend_strength_direction", "NONE"
            )
        ).upper()
        trend_score = float(
            result.trend_strength.get(
                "brooks_trend_strength_score", 0.0
            ) or 0.0
        )
        if trend_direction in {"BUY", "SELL"}:
            observations.append((trend_direction, trend_score))

        breakout_valid = bool(
            result.breakout_strength.get("valid", False)
        )
        breakout_direction = str(
            result.breakout_strength.get("direction", "NONE")
        ).upper()
        breakout_score = float(
            result.breakout_strength.get("score", 0.0) or 0.0
        )
        if breakout_valid and breakout_direction in {"BUY", "SELL"}:
            observations.append((breakout_direction, breakout_score))

        if not observations:
            result.directional_bias = "NONE"
            result.alignment = "NEUTRAL"
            result.add_reason("BOOK_ALIGNMENT_NEUTRAL")
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
                max(0.0, min(100.0, base_quality - conflict_penalty)),
                2,
            )

        result.confidence = min(1.0, result.quality_score / 100.0)
        result.add_reason(f"BOOK_ALIGNMENT_{result.alignment}")
