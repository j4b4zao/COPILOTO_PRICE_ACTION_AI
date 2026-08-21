"""
decision/decision_engine.py

Decision Engine

RC9.2 - MULTI-TIMEFRAME SAFETY GATE
"""

from ai.engine_base import EngineBase


class DecisionEngine(EngineBase):

    NAME = "DecisionEngine"

    VERSION = "RC9.2"

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
        # MULTI-TIMEFRAME SAFETY GATE (RC3.5)
        # ======================================================
        #
        # O MTF não adiciona score nem cria uma operação.
        # Ele apenas bloqueia uma decisão já formada quando:
        #
        # - existe conflito direcional entre M15/M5/M1; ou
        # - o alinhamento válido aponta para o lado oposto.
        #
        # WAIT, dados insuficientes e análise não executada
        # preservam o comportamento operacional anterior.

        multi_timeframe = (
            context.multi_timeframe_analysis
        )

        block_reason = self._multi_timeframe_block_reason(
            multi_timeframe,
            direction,
        )

        if block_reason:

            decision.action = "WAIT"

            decision.add_reason(
                block_reason
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

        if (
            multi_timeframe.valid
            and multi_timeframe.alignment == direction
        ):

            decision.add_reason(
                "Multi-timeframe confirma a direção da operação."
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

    # ==========================================================
    # MULTI-TIMEFRAME SAFETY GATE
    # ==========================================================

    @staticmethod
    def _multi_timeframe_block_reason(
        multi_timeframe,
        direction,
    ):

        if not multi_timeframe.valid:

            return None

        if multi_timeframe.alignment == "CONFLICT":

            return (
                "Operação bloqueada: conflito direcional "
                "entre M15, M5 e M1."
            )

        if (
            multi_timeframe.alignment
            in ("BUY", "SELL")
            and multi_timeframe.alignment != direction
        ):

            return (
                "Operação bloqueada: multi-timeframe "
                f"{multi_timeframe.alignment} contradiz "
                f"a direção {direction} da estratégia."
            )

        return None
