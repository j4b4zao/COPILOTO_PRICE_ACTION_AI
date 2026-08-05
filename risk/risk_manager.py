"""
risk/risk_manager.py

Risk Manager

RC8
"""

from ai.engine_base import EngineBase

from config.settings import (
    DEFAULT_STOP,
    DEFAULT_TARGET,
    DEFAULT_RR,
)


class RiskManager(EngineBase):

    NAME = "RiskManager"

    VERSION = "RC8"

    ENABLED = True

    PRIORITY = 90

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        risk = context.risk

        strategy = context.strategy

        volume = context.volume

        liquidity = context.liquidity

        risk.clear()

        # ======================================================
        # SETUP
        # ======================================================

        if not strategy.valid:

            risk.add_reason("Nenhum setup válido")

            return context

        # ======================================================
        # CONFIGURAÇÃO PADRÃO
        # ======================================================

        risk.stop_loss = DEFAULT_STOP

        risk.take_profit = DEFAULT_TARGET

        risk.risk_reward = DEFAULT_RR

        # ======================================================
        # SCORE DO SETUP
        # ======================================================

        score = strategy.score

        if score >= 95:

            risk.risk_score += 40

        elif score >= 90:

            risk.risk_score += 35

        elif score >= 80:

            risk.risk_score += 25

        else:

            risk.risk_score += 10

        # ======================================================
        # VOLUME
        # ======================================================

        if volume.high:

            risk.risk_score += 20

        elif volume.medium:

            risk.risk_score += 10

        # ======================================================
        # LIQUIDEZ
        # ======================================================

        if liquidity.buy_side:

            risk.risk_score += 20

        if liquidity.sell_side:

            risk.risk_score += 20

        # ======================================================
        # CONFLUÊNCIAS
        # ======================================================

        risk.risk_score += min(

            len(strategy.reasons) * 2,

            20,

        )

        # ======================================================
        # LIMITE
        # ======================================================

        risk.risk_score = min(

            risk.risk_score,

            100,

        )

        # ======================================================
        # CLASSIFICAÇÃO
        # ======================================================

        if risk.risk_score >= 90:

            risk.approved = True

            risk.risk_level = "LOW"

        elif risk.risk_score >= 75:

            risk.approved = True

            risk.risk_level = "MEDIUM"

        else:

            risk.approved = False

            risk.risk_level = "HIGH"

        # ======================================================
        # VALIDAÇÃO
        # ======================================================

        risk.valid = risk.approved

        risk.confidence = (

            risk.risk_score / 100

        )

        # ======================================================
        # MOTIVOS
        # ======================================================

        risk.add_reason(

            f"Risk Score {risk.risk_score:.0f}"

        )

        risk.add_reason(

            f"Risk/Reward {risk.risk_reward:.2f}"

        )

        return context