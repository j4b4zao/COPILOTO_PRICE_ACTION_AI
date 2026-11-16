"""alerts/alert_manager.py — RC9.3, validação fail-closed de alertas.

Não executa ordens. Rejeita decisões e riscos inconsistentes.
"""

from datetime import datetime
from math import isfinite

from ai.engine_base import EngineBase


class AlertManager(EngineBase):
    NAME = "AlertManager"
    VERSION = "RC9.3"
    ENABLED = True
    PRIORITY = 110

    @staticmethod
    def _positive_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
            and value > 0
        )

    @classmethod
    def _safe_to_alert(cls, context):
        try:
            decision = context.decision
            risk = context.risk
            if decision.valid is not True or risk.valid is not True:
                return False
            if risk.approved is not True or not decision.approved:
                return False

            action = decision.action
            if action not in ("BUY", "SELL"):
                return False
            if decision.direction != action or decision.signal != action:
                return False
            if not isinstance(decision.setup, str) or not decision.setup.strip():
                return False
            if not cls._positive_number(decision.score):
                return False
            if not cls._positive_number(decision.confidence) or decision.confidence > 1:
                return False

            entry, stop, target = decision.entry, decision.stop, decision.target
            if not all(cls._positive_number(x) for x in (entry, stop, target)):
                return False
            if action == "BUY" and not (stop < entry < target):
                return False
            if action == "SELL" and not (target < entry < stop):
                return False

            actual_rr = abs(target - entry) / abs(entry - stop)
            # Limite atual do RiskManager RC10.2. Não exige campo
            # risk_reward em DecisionResult: calcula a partir dos preços.
            from risk.risk_manager import RiskManager
            minimum_rr = getattr(RiskManager, "MIN_RISK_REWARD", 1.5)
            if not cls._positive_number(minimum_rr):
                return False
            if not isfinite(actual_rr) or actual_rr < minimum_rr:
                return False

            return True
        except (AttributeError, TypeError, ValueError, ZeroDivisionError, OverflowError):
            return False

    def executar(self, context):
        alert = context.alert
        alert.clear()
        if not self._safe_to_alert(context):
            return context

        decision = context.decision
        alert.timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        alert.action = decision.action
        alert.direction = decision.direction
        alert.signal = decision.signal
        alert.setup = decision.setup
        alert.score = decision.score
        alert.confidence = decision.confidence

        score = context.score
        if score.order_flow_applied:
            alert.order_flow_applied = True
            alert.order_flow_direction = score.order_flow_direction
            alert.order_flow_sampling_mode = context.order_flow.sampling_mode
            alert.order_flow_contribution = score.order_flow_contribution
            alert.add_reason("Order Flow aplicado ao score")

        alert.valid = True
        alert.add_reason("Alerta emitido")
        print("=" * 60)
        print(f"[{alert.timestamp}]")
        print(f"AÇÃO : {alert.action}")
        print(f"DIREÇÃO: {alert.direction}")
        print(f"SETUP: {alert.setup}")
        print(f"SCORE: {alert.score:.1f}")
        print(f"CONF.: {alert.confidence:.2f}")
        if alert.order_flow_applied:
            print(
                "ORDER FLOW: "
                f"{alert.order_flow_direction} | "
                f"{alert.order_flow_sampling_mode} | "
                f"+{alert.order_flow_contribution:.2f} pts"
            )
        print("=" * 60)
        return context
