"""
decision/decision_engine.py

Decision Engine

RC8
"""

from ai.engine_base import EngineBase


class DecisionEngine(EngineBase):

    NAME = "DecisionEngine"

    VERSION = "RC8"

    ENABLED = True

    PRIORITY = 100

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        decision = context.decision

        strategy = context.strategy

        risk = context.risk

        score = context.score

        decision.clear()

        # ======================================================
        # NÃO EXISTE SETUP
        # ======================================================

        if not strategy.valid:

            decision.action = "WAIT"

            decision.add_reason("Nenhum setup encontrado")

            return context

        # ======================================================
        # RISCO
        # ======================================================

        if not risk.approved:

            decision.action = "WAIT"

            decision.add_reason("Risco não aprovado")

            return context

        # ======================================================
        # SCORE
        # ======================================================

        if not score.valid:

            decision.action = "WAIT"

            decision.add_reason("Score insuficiente")

            return context

        # ======================================================
        # DECISÃO
        # ======================================================

        decision.action = strategy.signal

        decision.signal = strategy.signal

        decision.setup = strategy.name

        decision.score = score.total

        decision.risk_reward = risk.risk_reward

        decision.stop = risk.stop_loss

        decision.target = risk.take_profit

        decision.entry = 0.0

        decision.valid = True

        decision.confidence = score.confidence

        decision.add_reason("Operação aprovada")

        return context