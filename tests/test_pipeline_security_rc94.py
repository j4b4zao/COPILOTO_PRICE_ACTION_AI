"""RC9.4 — auditoria offline da cadeia DecisionEngine -> AlertManager.

Não envia ordens, não acessa Profit/RTD e não altera arquivos de produção.
A integração completa Strategy/Score/Risk/Pipeline permanece etapa separada.
"""

from contextlib import redirect_stdout
from io import StringIO

import pytest

from alerts.alert_manager import AlertManager
from core.analysis_context import AnalysisContext
from decision.decision_engine import DecisionEngine


def _context(direction="BUY"):
    context = AnalysisContext()
    strategy = context.strategy
    strategy.valid = True
    strategy.signal = direction
    strategy.name = "PRICE_ACTION"
    score = context.score
    score.valid = True
    score.total = 90.0
    score.confidence = 0.90
    risk = context.risk
    risk.valid = True
    risk.approved = True
    risk.entry_price = 1000.0
    risk.stop_loss = 990.0 if direction == "BUY" else 1010.0
    risk.take_profit = 1020.0 if direction == "BUY" else 980.0
    risk.risk_reward = 2.0
    return context


def _run(context):
    with redirect_stdout(StringIO()):
        assert DecisionEngine().executar(context) is context
        assert AlertManager().executar(context) is context
    return context


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_rc94_valid_controls(direction):
    context = _run(_context(direction))
    assert context.decision.valid is True
    assert context.decision.action == direction
    assert context.alert.valid is True
    assert context.alert.action == direction


@pytest.mark.parametrize("mutation", [
    lambda c: setattr(c.strategy, "valid", False),
    lambda c: setattr(c.strategy, "signal", "NONE"),
    lambda c: setattr(c.risk, "approved", False),
    lambda c: setattr(c.score, "valid", False),
])
def test_rc94_upstream_rejections_never_alert(mutation):
    context = _context()
    mutation(context)
    _run(context)
    assert context.decision.action == "WAIT"
    assert context.alert.valid is False
    assert context.alert.action == "NONE"


def test_rc94_invalid_risk_validity_never_alert():
    context = _context()
    context.risk.valid = False
    _run(context)
    assert context.alert.valid is False


@pytest.mark.parametrize("direction,opposite", [("BUY", "SELL"), ("SELL", "BUY")])
def test_rc94_mtf_conflict_never_alert(direction, opposite):
    context = _context(direction)
    context.multi_timeframe_analysis.valid = True
    context.multi_timeframe_analysis.alignment = opposite
    _run(context)
    assert context.decision.action == "WAIT"
    assert context.alert.valid is False


def test_rc94_stale_alert_cleared_across_cycles():
    context = _context("BUY")
    _run(context)
    assert context.alert.valid and context.alert.action == "BUY"

    # Novo ciclo: o contexto reutilizado deve apagar o alerta anterior.
    context.clear_results()
    _run(context)
    assert context.decision.action == "WAIT"
    assert context.alert.valid is False
    assert context.alert.action == "NONE"
    assert context.alert.reasons == []

    # Reconstitui explicitamente os dados de um novo ciclo SELL.
    new_sell = _context("SELL")
    context.strategy = new_sell.strategy
    context.score = new_sell.score
    context.risk = new_sell.risk
    _run(context)
    assert context.alert.valid and context.alert.action == "SELL"

    context.clear_results()
    _run(context)
    assert context.decision.action == "WAIT"
    assert context.alert.valid is False
    assert context.alert.action == "NONE"


def test_rc94_alert_rejects_mutated_decision_after_approval():
    context = _run(_context("BUY"))
    assert context.alert.valid is True
    context.decision.entry = 0.0
    with redirect_stdout(StringIO()):
        AlertManager().executar(context)
    assert context.alert.valid is False
    assert context.alert.action == "NONE"
