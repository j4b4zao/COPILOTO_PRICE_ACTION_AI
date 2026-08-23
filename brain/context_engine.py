"""
brain/context_engine.py

Context Engine RC15.5

Integrações contextuais:
- External Context RC2.4;
- Market Regime RC3.0;
- Multi-timeframe RC3.4.

Consolida as análises anteriores em contexto operacional sem gerar entrada
nem calcular o Score global. Regime, multi-timeframe e contexto externo
permanecem evidências observacionais: não alteram confluences, valid, score
ou bias operacional.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend
from models.market_narrative import MarketNarrative


class ContextEngine(EngineBase):

    NAME = "Context Engine"
    VERSION = "RC15.5-EXTERNAL-EVIDENCE"
    DESCRIPTION = "Consolida o contexto do mercado."
    PRIORITY = 70
    ENABLED = True

    EXTERNAL_MIN_CONFIDENCE = 0.50

    def executar(self, context):
        result = context.context
        checklist = context.checklist

        result.clear()
        checklist.clear()
        context.narrative = MarketNarrative()
        narrative = context.narrative

        structure = context.structure
        liquidity = context.liquidity
        volume = context.volume
        price_action = context.price_action
        regime = context.regime
        multi_timeframe = context.multi_timeframe_analysis
        external_market = context.external_market

        if structure.valid:
            checklist.structure = True

        if structure.trend == Trend.UP:
            checklist.trend = True
            result.bias = "BUY"
            result.market_state = "FAVORABLE"
            narrative.strengths.append("Tendência de alta definida.")
        elif structure.trend == Trend.DOWN:
            checklist.trend = True
            result.bias = "SELL"
            result.market_state = "FAVORABLE"
            narrative.strengths.append("Tendência de baixa definida.")
        elif structure.trend == Trend.SIDEWAYS:
            result.bias = "NONE"
            result.market_state = "NEUTRAL"
            narrative.weaknesses.append("Mercado lateral.")
        else:
            result.bias = "NONE"
            result.market_state = "UNDEFINED"
            narrative.weaknesses.append("Tendência ainda não confirmada.")

        if liquidity.valid:
            checklist.liquidity = True
            narrative.strengths.append("Liquidez analisada.")
        else:
            narrative.weaknesses.append("Liquidez ainda não confirmada.")

        if volume.valid:
            checklist.volume = True
            if volume.high:
                narrative.strengths.append("Volume forte.")
            elif volume.medium:
                narrative.strengths.append("Volume médio.")
            else:
                narrative.weaknesses.append("Volume fraco.")
        else:
            narrative.weaknesses.append("Volume ainda não confirmado.")

        if price_action.valid:
            checklist.setup = True
            narrative.strengths.append("Price Action possui evidências.")

        self._append_regime_evidence(result, regime, narrative)
        self._append_multi_timeframe_evidence(
            result,
            checklist,
            multi_timeframe,
            narrative,
        )
        self._append_external_evidence(
            result,
            checklist,
            external_market,
            narrative,
        )

        checklist.context = (
            checklist.structure
            and checklist.trend
            and checklist.volume
            and checklist.liquidity
        )

        confluences = 0
        if checklist.structure:
            confluences += 1
        if checklist.trend:
            confluences += 1
        if checklist.volume:
            confluences += 1
        if checklist.liquidity:
            confluences += 1
        if structure.bos_up or structure.bos_down:
            confluences += 1
        if structure.choch:
            confluences += 1
        if price_action.valid:
            confluences += 1
        result.confluences = confluences

        result.valid = checklist.context and result.bias in ("BUY", "SELL")
        result.score = 0.0

        if result.valid:
            narrative.summary = "Contexto direcional favorável."
            narrative.recommendation = "AGUARDAR SETUP"
        elif result.market_state == "NEUTRAL":
            narrative.summary = "Mercado lateral ou sem direção clara."
            narrative.recommendation = "AGUARDAR"
        else:
            narrative.summary = "Contexto ainda não confirmado."
            narrative.recommendation = "AGUARDAR"

        itens = [
            checklist.trend,
            checklist.structure,
            checklist.volume,
            checklist.liquidity,
            checklist.context,
        ]
        narrative.confidence = (sum(itens) / len(itens)) * 100
        return context

    @staticmethod
    def _append_regime_evidence(result, regime, narrative) -> None:
        if not regime.valid:
            narrative.weaknesses.append("Regime de mercado ainda não disponível.")
            return

        if regime.regime == "TRANSITION":
            pending = getattr(regime, "pending_regime", "UNKNOWN")
            narrative.weaknesses.append(
                "Regime de mercado em transição"
                + (f" para {pending}." if pending != "UNKNOWN" else ".")
            )
        elif regime.regime == "RANGE":
            narrative.weaknesses.append("Regime de mercado em range.")
        elif (
            result.bias == "BUY" and regime.trend == Trend.UP
        ) or (
            result.bias == "SELL" and regime.trend == Trend.DOWN
        ):
            narrative.strengths.append("Regime de mercado confirma direção.")
        elif (
            result.bias == "BUY" and regime.trend == Trend.DOWN
        ) or (
            result.bias == "SELL" and regime.trend == Trend.UP
        ):
            narrative.weaknesses.append("Regime de mercado conflita com direção.")
        elif regime.trend == Trend.SIDEWAYS:
            narrative.weaknesses.append("Regime de mercado lateral.")
        else:
            narrative.weaknesses.append("Regime de mercado neutro.")

        if regime.volatility == "HIGH":
            narrative.weaknesses.append("Volatilidade alta detectada pelo regime.")
        elif regime.volatility == "LOW":
            narrative.weaknesses.append("Volatilidade baixa detectada pelo regime.")
        else:
            narrative.strengths.append("Volatilidade normal detectada pelo regime.")

    @staticmethod
    def _append_multi_timeframe_evidence(
        result,
        checklist,
        multi_timeframe,
        narrative,
    ) -> None:
        checklist.multi_timeframe_status = multi_timeframe.alignment

        if not multi_timeframe.valid:
            narrative.weaknesses.append(
                "Multi-timeframe ainda possui dados insuficientes."
            )
            return

        checklist.multi_timeframe_ready = True
        checklist.multi_timeframe_aligned = multi_timeframe.aligned
        checklist.multi_timeframe_conflict = multi_timeframe.conflict

        alignment = multi_timeframe.alignment

        if alignment in ("BUY", "SELL"):
            if result.bias == multi_timeframe.bias:
                narrative.strengths.append(
                    "Multi-timeframe confirma direção operacional."
                )
            elif result.bias in ("BUY", "SELL"):
                checklist.multi_timeframe_conflict = True
                narrative.weaknesses.append(
                    "Multi-timeframe conflita com direção operacional."
                )
            else:
                narrative.weaknesses.append(
                    "Multi-timeframe está alinhado, mas o contexto operacional "
                    "ainda não possui direção."
                )
            return

        if alignment == "CONFLICT_REGIME":
            checklist.multi_timeframe_conflict = True
            narrative.weaknesses.append(
                "Multi-timeframe conflita com o regime de mercado estabilizado."
            )
            return

        if alignment == "WAIT_REGIME":
            narrative.weaknesses.append(
                "Multi-timeframe possui bias, mas aguarda confirmação do regime."
            )
            return

        if alignment == "CONFLICT_M5":
            checklist.multi_timeframe_conflict = True
            narrative.weaknesses.append(
                "M5 contradiz o contexto direcional definido pelo M15."
            )
            return

        if alignment == "CONFLICT_M1":
            checklist.multi_timeframe_conflict = True
            narrative.weaknesses.append(
                "M1 contradiz M15/M5; gatilho ainda não está confirmado."
            )
            return

        if alignment == "WAIT_CONTEXT":
            narrative.weaknesses.append("M15 ainda não definiu contexto direcional.")
        elif alignment == "WAIT_M5":
            narrative.weaknesses.append(
                "M15 possui direção, mas M5 ainda não confirmou o setup."
            )
        elif alignment == "WAIT_TRIGGER":
            narrative.weaknesses.append(
                "M15/M5 estão coerentes; M1 ainda aguarda gatilho."
            )
        else:
            narrative.weaknesses.append(
                "Multi-timeframe aguarda alinhamento completo."
            )

    @classmethod
    def _append_external_evidence(
        cls,
        result,
        checklist,
        external_market,
        narrative,
    ) -> None:
        if not external_market.valid:
            checklist.external_context_status = "UNAVAILABLE"
            narrative.weaknesses.append("Contexto externo ainda não disponível.")
            return

        checklist.external_context_ready = True
        confidence = min(max(float(external_market.confidence or 0.0), 0.0), 1.0)
        checklist.external_context_confidence = confidence

        risk_on_off = str(external_market.risk_on_off or "NEUTRAL").upper()
        global_bias = str(external_market.global_bias or "NEUTRAL").upper()

        if confidence < cls.EXTERNAL_MIN_CONFIDENCE:
            checklist.external_context_status = "LOW_CONFIDENCE"
            narrative.weaknesses.append(
                f"Contexto externo com baixa confiança ({confidence:.0%})."
            )
            return

        aligned = (
            result.bias == "BUY"
            and risk_on_off == "RISK_ON"
            and global_bias == "BULLISH"
        ) or (
            result.bias == "SELL"
            and risk_on_off == "RISK_OFF"
            and global_bias == "BEARISH"
        )

        conflict = (
            result.bias == "BUY"
            and risk_on_off == "RISK_OFF"
            and global_bias == "BEARISH"
        ) or (
            result.bias == "SELL"
            and risk_on_off == "RISK_ON"
            and global_bias == "BULLISH"
        )

        if aligned:
            checklist.external_context_aligned = True
            checklist.external_context_status = "ALIGNED"
            narrative.strengths.append(
                f"Contexto externo confirma direção ({confidence:.0%} confiança)."
            )
        elif conflict:
            checklist.external_context_conflict = True
            checklist.external_context_status = "CONFLICT"
            narrative.weaknesses.append(
                f"Contexto externo conflita com direção ({confidence:.0%} confiança)."
            )
        else:
            checklist.external_context_status = "NEUTRAL"
            narrative.weaknesses.append(
                f"Contexto externo neutro ({confidence:.0%} confiança)."
            )
