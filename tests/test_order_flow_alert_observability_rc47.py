"""Testes offline da observabilidade de Order Flow no alerta RC4.7."""

from contextlib import redirect_stdout
from io import StringIO

from alerts.alert_manager import AlertManager
from core.analysis_context import AnalysisContext
from tests.test_order_flow_score_e2e_rc46 import (
    execute_operational_chain,
)


def approved_context(
    *,
    applied=False,
    direction="NONE",
    sampling_mode="NONE",
    contribution=0.0,
):
    context = AnalysisContext()

    context.decision.valid = True
    context.decision.action = direction if applied else "BUY"
    context.decision.direction = direction if applied else "BUY"
    context.decision.signal = direction if applied else "BUY"
    context.decision.setup = "PRICE_ACTION"
    context.decision.score = 90.0
    context.decision.confidence = 0.90

    context.score.order_flow_applied = applied
    context.score.order_flow_direction = direction
    context.score.order_flow_contribution = contribution
    context.order_flow.sampling_mode = sampling_mode

    return context


def execute_alert(context):
    output = StringIO()
    with redirect_stdout(output):
        result = AlertManager().executar(context)

    assert result is context
    return output.getvalue()


def teste_alerta_buy_normal_expoe_bonus_order_flow():
    context = approved_context(
        applied=True,
        direction="BUY",
        sampling_mode="TICK",
        contribution=5.0,
    )

    output = execute_alert(context)
    alert = context.alert

    assert alert.valid is True
    assert alert.order_flow_applied is True
    assert alert.order_flow_direction == "BUY"
    assert alert.order_flow_sampling_mode == "TICK"
    assert alert.order_flow_contribution == 5.0
    assert "Order Flow aplicado ao score" in alert.reasons
    assert "ORDER FLOW: BUY | TICK | +5.00 pts" in output


def teste_alerta_sell_renko_expoe_bonus_order_flow():
    context = approved_context(
        applied=True,
        direction="SELL",
        sampling_mode="RENKO_CLOSE",
        contribution=4.25,
    )

    output = execute_alert(context)
    alert = context.alert

    assert alert.valid is True
    assert alert.order_flow_applied is True
    assert alert.order_flow_direction == "SELL"
    assert alert.order_flow_sampling_mode == "RENKO_CLOSE"
    assert alert.order_flow_contribution == 4.25
    assert "ORDER FLOW: SELL | RENKO_CLOSE | +4.25 pts" in output


def teste_alerta_sem_bonus_preserva_saida_anterior():
    context = approved_context()

    output = execute_alert(context)
    alert = context.alert

    assert alert.valid is True
    assert alert.order_flow_applied is False
    assert alert.order_flow_direction == "NONE"
    assert alert.order_flow_sampling_mode == "NONE"
    assert alert.order_flow_contribution == 0.0
    assert alert.reasons == ["Alerta emitido"]
    assert "ORDER FLOW:" not in output


def teste_clear_remove_observabilidade_anterior():
    context = approved_context(
        applied=True,
        direction="BUY",
        sampling_mode="TICK",
        contribution=5.0,
    )
    execute_alert(context)

    context.decision.action = "WAIT"
    execute_alert(context)

    alert = context.alert
    assert alert.valid is False
    assert alert.order_flow_applied is False
    assert alert.order_flow_direction == "NONE"
    assert alert.order_flow_sampling_mode == "NONE"
    assert alert.order_flow_contribution == 0.0
    assert alert.reasons == []


def teste_cadeia_e2e_propaga_observabilidade_normal_e_renko():
    scenarios = (
        ("BUY", "NORMAL", "TICK"),
        ("SELL", "RENKO", "RENKO_CLOSE"),
    )

    for direction, mode, sampling_mode in scenarios:
        context = execute_operational_chain(
            direction,
            mode,
            True,
        )
        alert = context.alert

        assert alert.valid is True
        assert alert.order_flow_applied is True
        assert alert.order_flow_direction == direction
        assert alert.order_flow_sampling_mode == sampling_mode
        assert alert.order_flow_contribution == 5.0


if __name__ == "__main__":
    tests = (
        teste_alerta_buy_normal_expoe_bonus_order_flow,
        teste_alerta_sell_renko_expoe_bonus_order_flow,
        teste_alerta_sem_bonus_preserva_saida_anterior,
        teste_clear_remove_observabilidade_anterior,
        teste_cadeia_e2e_propaga_observabilidade_normal_e_renko,
    )

    for test in tests:
        test()

    print("OK - Order Flow alert observability RC4.7")
