"""
alerts/alert_manager.py

Alert Manager

RC8
"""

from ai.engine_base import EngineBase

from datetime import datetime


class AlertManager(EngineBase):

    NAME = "AlertManager"

    VERSION = "RC8"

    ENABLED = True

    PRIORITY = 110

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        alert = context.alert

        decision = context.decision

        alert.clear()

        # ------------------------------------------------------
        # NÃO EXISTE OPERAÇÃO
        # ------------------------------------------------------

        if not decision.approved:

            return context

        # ------------------------------------------------------
        # ALERTA
        # ------------------------------------------------------

        alert.timestamp = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        alert.action = decision.action

        alert.signal = decision.signal

        alert.setup = decision.setup

        alert.score = decision.score

        alert.confidence = decision.confidence

        alert.valid = True

        alert.add_reason("Alerta emitido")

        # ------------------------------------------------------
        # LOG
        # ------------------------------------------------------

        print("=" * 60)

        print(f"[{alert.timestamp}]")

        print(f"AÇÃO : {alert.action}")

        print(f"SETUP: {alert.setup}")

        print(f"SCORE: {alert.score:.1f}")

        print(f"CONF.: {alert.confidence:.2f}")

        print("=" * 60)

        return context