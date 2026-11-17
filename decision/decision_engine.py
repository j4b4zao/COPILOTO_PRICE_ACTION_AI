"""DecisionEngine RC9.5-A4: validacao fail-closed de contratos de risco.

Preserva o bloqueio multi-timeframe RC3.6. Nao executa ordens.
"""

import math
from numbers import Real

from ai.engine_base import EngineBase


class DecisionEngine(EngineBase):
    NAME = "DecisionEngine"
    VERSION = "RC9.5-A4-MTF-CONFLICT-SAFETY-RC3.6"
    ENABLED = True
    PRIORITY = 100

    @staticmethod
    def _finite_number(value):
        return (
            isinstance(value, Real)
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    @classmethod
    def _valid_contract(cls, risk, score, direction):
        if risk.valid is not True or risk.approved is not True:
            return "Risco nao esta valido e aprovado."

        entry = risk.entry_price
        stop = risk.stop_loss
        target = risk.take_profit
        rr = risk.risk_reward
        total = score.total
        confidence = score.confidence

        if not all(cls._finite_number(x) and x > 0 for x in (entry, stop, target)):
            return "Precos de risco ausentes, nao finitos ou nao positivos."

        if direction == "BUY" and not (stop < entry < target):
            return "Precos BUY incoerentes com a direcao."
        if direction == "SELL" and not (target < entry < stop):
            return "Precos SELL incoerentes com a direcao."

        if not cls._finite_number(rr) or rr <= 0:
            return "Relacao risco-retorno invalida."

        calculated_rr = abs(target - entry) / abs(entry - stop)
        if not math.isclose(rr, calculated_rr, rel_tol=1e-6, abs_tol=1e-6):
            return "Relacao risco-retorno divergente dos precos aprovados."

        if not cls._finite_number(total) or not 0 <= total <= 100:
            return "Score invalido."
        if not cls._finite_number(confidence) or not 0 <= confidence <= 1:
            return "Confianca invalida."
        return None

    def executar(self, context):
        decision = context.decision
        strategy = context.strategy
        risk = context.risk
        score = context.score
        decision.clear()

        if not strategy.valid:
            decision.action = "WAIT"
            decision.add_reason("Nenhum setup encontrado.")
            return context

        if risk.approved is not True or risk.valid is not True:
            decision.action = "WAIT"
            decision.add_reason("Risco nao aprovado ou invalido.")
            return context

        if not score.valid:
            decision.action = "WAIT"
            decision.add_reason("Score insuficiente.")
            return context

        direction = str(getattr(strategy, "signal", "NONE")).upper()
        if direction not in ("BUY", "SELL"):
            decision.action = "WAIT"
            decision.add_reason("Direcao da estrategia invalida.")
            return context

        invalid_reason = self._valid_contract(risk, score, direction)
        if invalid_reason:
            decision.action = "WAIT"
            decision.add_reason(invalid_reason)
            return context

        multi_timeframe = context.multi_timeframe_analysis
        block_reason = self._multi_timeframe_block_reason(multi_timeframe, direction)
        if block_reason:
            decision.action = "WAIT"
            decision.add_reason(block_reason)
            return context

        decision.action = direction
        decision.direction = direction
        decision.signal = direction
        decision.setup = strategy.name
        decision.score = score.total
        decision.risk_reward = risk.risk_reward
        decision.entry = risk.entry_price
        decision.stop = risk.stop_loss
        decision.target = risk.take_profit
        decision.valid = True
        decision.confidence = score.confidence

        decision.add_reason("Operação aprovada.")
        if multi_timeframe.valid and multi_timeframe.alignment == direction:
            decision.add_reason("Multi-timeframe confirma a direção da operação.")
        decision.add_reason(f"Setup: {strategy.name}")
        decision.add_reason(f"Direção: {direction}")
        decision.add_reason(f"Score: {score.total:.2f}")
        decision.add_reason(f"Entrada: {risk.entry_price:.2f}")
        decision.add_reason(f"Stop: {risk.stop_loss:.2f}")
        decision.add_reason(f"Alvo: {risk.take_profit:.2f}")
        decision.add_reason(f"R:R: {risk.risk_reward:.2f}")
        return context

    @staticmethod
    def _multi_timeframe_block_reason(multi_timeframe, direction):
        if not multi_timeframe.valid:
            return None
        if multi_timeframe.conflict:
            return (
                "Operação bloqueada: conflito direcional "
                "entre M15, M5 e M1 ou regime de mercado."
            )
        if multi_timeframe.alignment == "CONFLICT":
            return (
                "Operação bloqueada: conflito direcional "
                "entre M15, M5 e M1."
            )
        if (
            multi_timeframe.alignment in ("BUY", "SELL")
            and multi_timeframe.alignment != direction
        ):
            return (
                "Operação bloqueada: multi-timeframe "
                f"{multi_timeframe.alignment} contradiz "
                f"a direção {direction} da estratégia."
            )
        return None
