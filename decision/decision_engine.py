"""
decision/decision_engine.py

Decision Engine

RC9.1
"""

from ai.engine_base import EngineBase


class DecisionEngine(EngineBase):

    NAME = "DecisionEngine"

    VERSION = "RC9.1"

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
        # SEM SETUP
        # ======================================================

        if not strategy.valid:

            decision.action = "WAIT"

            decision.add_reason(
                "Nenhum setup encontrado."
            )

            return context

        # ======================================================
        # RISCO
        # ======================================================

        if not risk.approved:

            decision.action = "WAIT"

            decision.add_reason(
                "Risco não aprovado."
            )

            return context

        # ======================================================
        # SCORE
        # ======================================================

        if not score.valid:

            decision.action = "WAIT"

            decision.add_reason(
                "Score insuficiente."
            )

            return context

        # ======================================================
        # DIREÇÃO
        # ======================================================

        direction = str(
            getattr(
                strategy,
                "signal",
                "NONE",
            )
        ).upper()

        if direction not in (
            "BUY",
            "SELL",
        ):

            decision.action = "WAIT"

            decision.add_reason(
                "Direção da estratégia inválida."
            )

            return context

        # ======================================================
        # DECISÃO
        # ======================================================

        decision.action = direction

        decision.direction = direction

        decision.signal = direction

        decision.setup = strategy.name

        decision.score = score.total

        decision.risk_reward = (
            risk.risk_reward
        )

        decision.entry = (
            risk.entry_price
        )

        decision.stop = (
            risk.stop_loss
        )

        decision.target = (
            risk.take_profit
        )

        decision.valid = True

        decision.confidence = (
            score.confidence
        )

        # ======================================================
        # MOTIVOS
        # ======================================================

        decision.add_reason(
            "Operação aprovada."
        )

        decision.add_reason(
            f"Setup: {strategy.name}"
        )

        decision.add_reason(
            f"Direção: {direction}"
        )

        decision.add_reason(
            f"Score: {score.total:.2f}"
        )

        decision.add_reason(
            f"Entrada: {risk.entry_price:.2f}"
        )

        decision.add_reason(
            f"Stop: {risk.stop_loss:.2f}"
        )

        decision.add_reason(
            f"Alvo: {risk.take_profit:.2f}"
        )

        decision.add_reason(
            f"R:R: {risk.risk_reward:.2f}"
        )

        return context