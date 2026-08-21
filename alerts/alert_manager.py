"""
alerts/alert_manager.py

Alert Manager

RC9.2 - ORDER FLOW OBSERVABILITY
"""

from datetime import datetime

from ai.engine_base import EngineBase


class AlertManager(EngineBase):

    NAME = "AlertManager"

    VERSION = "RC9.2"

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

        alert.direction = decision.direction

        alert.signal = decision.signal

        alert.setup = decision.setup

        alert.score = decision.score

        alert.confidence = decision.confidence

        score = context.score

        if score.order_flow_applied:

            alert.order_flow_applied = True

            alert.order_flow_direction = (
                score.order_flow_direction
            )

            alert.order_flow_sampling_mode = (
                context.order_flow.sampling_mode
            )

            alert.order_flow_contribution = (
                score.order_flow_contribution
            )

            alert.add_reason(
                "Order Flow aplicado ao score"
            )

        alert.valid = True

        alert.add_reason(
            "Alerta emitido"
        )

        # ------------------------------------------------------
        # LOG
        # ------------------------------------------------------

        print("=" * 60)

        print(
            f"[{alert.timestamp}]"
        )

        print(
            f"AÇÃO : {alert.action}"
        )

        print(
            f"DIREÇÃO: {alert.direction}"
        )

        print(
            f"SETUP: {alert.setup}"
        )

        print(
            f"SCORE: {alert.score:.1f}"
        )

        print(
            f"CONF.: {alert.confidence:.2f}"
        )

        if alert.order_flow_applied:

            print(
                "ORDER FLOW: "
                f"{alert.order_flow_direction} | "
                f"{alert.order_flow_sampling_mode} | "
                f"+{alert.order_flow_contribution:.2f} pts"
            )

        print("=" * 60)

        return context
