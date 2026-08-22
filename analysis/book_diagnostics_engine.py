"""
analysis/book_diagnostics_engine.py

Book Diagnostics Engine RC2 - Observational.

Executa somente diagnósticos passivos selecionados dos livros.
Não altera Strategy, Score, Risk, Decision nem execução.
"""

from ai.engine_base import EngineBase

from analysis.price_action.always_in_dynamics import AlwaysInDynamics
from analysis.price_action.trend_strength_dynamics import TrendStrengthDynamics


class BookDiagnosticsEngine(EngineBase):

    NAME = "BookDiagnostics"

    VERSION = "RC2-OBSERVATIONAL"

    ENABLED = True

    PRIORITY = 55

    # ==========================================================
    # EXECUTAR
    # ==========================================================

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

        self._run_always_in(
            candles,
            result,
        )

        self._run_trend_strength(
            candles,
            context,
            result,
        )

        self._synthesize(result)

        result.validate()
        result.add_reason("PASSIVE_DIAGNOSTICS_ONLY")
        result.add_reason("OBSERVATIONAL_PIPELINE_ONLY")

        return context

    # ==========================================================
    # ALWAYS IN
    # ==========================================================

    @staticmethod
    def _run_always_in(candles, result) -> None:

        metrics = AlwaysInDynamics().analyze(candles)

        result.always_in.update(metrics.to_dict())

    # ==========================================================
    # TREND STRENGTH
    # ==========================================================

    @staticmethod
    def _run_trend_strength(
        candles,
        context,
        result,
    ) -> None:

        metrics = TrendStrengthDynamics.analyze(
            candles,
            context.structure.trend,
            result=context.price_action,
        )

        result.trend_strength.update(metrics)

    # ==========================================================
    # SÍNTESE PASSIVA
    # ==========================================================

    @staticmethod
    def _synthesize(result) -> None:

        always_direction = str(
            result.always_in.get(
                "direction",
                "NONE",
            )
        ).upper()

        trend_direction = str(
            result.trend_strength.get(
                "brooks_trend_strength_direction",
                "NONE",
            )
        ).upper()

        always_score = float(
            result.always_in.get(
                "quality_score",
                0.0,
            )
            or 0.0
        )

        trend_score = float(
            result.trend_strength.get(
                "brooks_trend_strength_score",
                0.0,
            )
            or 0.0
        )

        directions = {
            value
            for value in (
                always_direction,
                trend_direction,
            )
            if value in {"BUY", "SELL"}
        }

        if len(directions) == 1:
            result.directional_bias = directions.pop()

            if (
                always_direction == trend_direction
                and always_direction in {"BUY", "SELL"}
            ):
                result.alignment = "ALIGNED"
            else:
                result.alignment = "PARTIAL"

        elif len(directions) > 1:
            result.directional_bias = "NONE"
            result.alignment = "CONFLICT"

        else:
            result.directional_bias = "NONE"
            result.alignment = "NEUTRAL"

        scores = [
            score
            for score in (
                always_score,
                trend_score,
            )
            if score > 0.0
        ]

        if scores:
            result.quality_score = round(
                sum(scores) / len(scores),
                2,
            )

        result.confidence = min(
            1.0,
            result.quality_score / 100.0,
        )

        result.add_reason(
            f"BOOK_ALIGNMENT_{result.alignment}"
        )
