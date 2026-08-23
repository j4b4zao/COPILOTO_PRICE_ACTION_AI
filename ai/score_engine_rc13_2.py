"""
ai/score_engine_rc13_2.py

ScoreEngine RC13.2 - REGIME + MTF OPTIONAL ADJUSTMENT

Mantém o ScoreEngine RC13.1 como base oficial e adiciona um ajuste
contextual pequeno, explícito e desativado por padrão.

O ajuste usa apenas o resultado já consolidado do Multi-Timeframe RC3.4,
que por sua vez contém a compatibilidade com o MarketRegime RC3.0.

Nenhum peso-base é alterado.
"""

import math

from ai.score_engine import ScoreEngine as ScoreEngineRC13_1


class ScoreEngine(ScoreEngineRC13_1):

    VERSION = "RC13.2-REGIME-MTF-OPTIONAL"
    MAX_REGIME_MTF_WEIGHT = 5.0

    def __init__(
        self,
        enable_order_flow=None,
        order_flow_weight=None,
        enable_regime_mtf=None,
        regime_mtf_weight=None,
    ):
        super().__init__(
            enable_order_flow=enable_order_flow,
            order_flow_weight=order_flow_weight,
        )

        from config.settings import (
            ENABLE_REGIME_MTF_SCORE,
            REGIME_MTF_SCORE_WEIGHT,
        )

        self.enable_regime_mtf = bool(
            ENABLE_REGIME_MTF_SCORE
            if enable_regime_mtf is None
            else enable_regime_mtf
        )

        weight = (
            REGIME_MTF_SCORE_WEIGHT
            if regime_mtf_weight is None
            else regime_mtf_weight
        )

        try:
            self.regime_mtf_weight = float(weight)
        except (TypeError, ValueError):
            raise ValueError(
                "Peso experimental de Regime+MTF deve ser numérico."
            ) from None

        if (
            not math.isfinite(self.regime_mtf_weight)
            or not 0.0 <= self.regime_mtf_weight <= self.MAX_REGIME_MTF_WEIGHT
        ):
            raise ValueError(
                "Peso experimental de Regime+MTF deve ficar entre 0 e 5."
            )

    def executar(self, context):
        super().executar(context)

        if not self.enable_regime_mtf or self.regime_mtf_weight <= 0.0:
            return context

        score = context.score
        adjustment = self._contextual_adjustment(
            score_bias=score.bias,
            multi_timeframe=context.multi_timeframe_analysis,
            weight=self.regime_mtf_weight,
        )

        if adjustment == 0.0:
            return context

        score.add_score("RegimeMTFAdjustment", adjustment)
        score.calculate_total()
        score.total = min(max(float(score.total), 0.0), self.MAX_SCORE)
        score.classify()
        score.confidence = score.total / self.MAX_SCORE
        score.valid = (
            context.strategy.valid
            and score.total >= self.MIN_SCORE
        )

        return context

    @classmethod
    def _contextual_adjustment(
        cls,
        *,
        score_bias: str,
        multi_timeframe,
        weight: float,
    ) -> float:
        """Retorna um ajuste limitado entre -weight e +weight."""
        if score_bias not in ("BUY", "SELL"):
            return 0.0

        if not getattr(multi_timeframe, "valid", False):
            return 0.0

        alignment = str(
            getattr(multi_timeframe, "alignment", "")
        ).upper()
        mtf_bias = str(
            getattr(multi_timeframe, "bias", "NONE")
        ).upper()
        regime_compatible = bool(
            getattr(multi_timeframe, "regime_compatible", False)
        )

        # Confirmação completa: hierarquia M15/M5/M1 alinhada e regime compatível.
        if (
            alignment == score_bias
            and mtf_bias == score_bias
            and regime_compatible
        ):
            return round(weight, 2)

        # Regime oposto à direção superior é o conflito contextual mais forte.
        if alignment == "CONFLICT_REGIME":
            return round(-weight, 2)

        # Conflito estrutural no M5/M1 recebe penalidade intermediária.
        if alignment in ("CONFLICT_M5", "CONFLICT_M1"):
            return round(-0.75 * weight, 2)

        # RANGE/TRANSITION pede espera, mas não invalida o Price Action por si só.
        if alignment == "WAIT_REGIME":
            return round(-0.50 * weight, 2)

        # Contexto M15/M5/M1 ainda incompleto não ganha nem perde pontos.
        return 0.0
