"""RC9.4 fase 3: auditoria offline do RiskManager real -> Decision -> Alert.

As condicoes de mercado e score sao fixtures controladas. Metodos de
calculo estrutural do RiskManager sao substituidos por valores deterministas;
o metodo executar e suas regras de aprovacao sao reais. Nao ha RTD/ordens.
"""
from contextlib import redirect_stdout
from io import StringIO

import pytest

from core.analysis_context import AnalysisContext
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine
from alerts.alert_manager import AlertManager


def _context(direction):
    c = AnalysisContext()
    c.strategy.valid = True
    c.strategy.signal = direction
    c.strategy.name = "RC94_CONTROLLED"
    c.score.valid = True
    c.score.total = 90.0
    c.score.confidence = 0.9
    c.market.last_price = 1000.0
    return c


def _risk_engine(monkeypatch, direction, rr=2.0, risk_score=90.0):
    engine = RiskManager()
    entry, distance = 1000.0, 10.0
    stop = entry - distance if direction == "BUY" else entry + distance
    target = entry + distance * rr if direction == "BUY" else entry - distance * rr
    monkeypatch.setattr(engine, "_get_entry_price", lambda *args: entry)
    monkeypatch.setattr(engine, "_calculate_buy_stop", lambda *args: stop)
    monkeypatch.setattr(engine, "_calculate_sell_stop", lambda *args: stop)
    monkeypatch.setattr(engine, "_calculate_structural_target", lambda *args: (target, "RC94_FIXTURE", True))
    monkeypatch.setattr(engine, "_calculate_risk_score", lambda *args: risk_score)
    return engine


def _run(c, risk_engine):
    with redirect_stdout(StringIO()):
        assert risk_engine.executar(c) is c
        assert DecisionEngine().executar(c) is c
        assert AlertManager().executar(c) is c
    return c


def _blocked(c):
    assert c.risk.approved is False
    assert c.decision.action == "WAIT"
    assert c.decision.valid is False
    assert c.alert.valid is False
    assert c.alert.action == "NONE"


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_rc94_phase3_real_risk_approves_valid_trade(monkeypatch, direction):
    c = _run(_context(direction), _risk_engine(monkeypatch, direction))
    assert c.risk.valid is True
    assert c.risk.approved is True
    assert c.risk.risk_reward == pytest.approx(2.0)
    assert c.decision.valid is True
    assert c.decision.action == direction
    assert c.alert.valid is True
    assert c.alert.action == direction


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_rc94_phase3_real_risk_rejects_structural_rr_below_minimum(monkeypatch, direction):
    c = _run(_context(direction), _risk_engine(monkeypatch, direction, rr=1.25))
    assert c.risk.risk_reward == pytest.approx(1.25)
    _blocked(c)


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_rc94_phase3_real_risk_rejects_low_risk_score(monkeypatch, direction):
    c = _run(_context(direction), _risk_engine(monkeypatch, direction, risk_score=69.0))
    _blocked(c)


def test_rc94_phase3_real_risk_clears_previous_approval(monkeypatch):
    c = _context("BUY")
    _run(c, _risk_engine(monkeypatch, "BUY"))
    assert c.alert.valid is True
    c.strategy.valid = False
    _run(c, _risk_engine(monkeypatch, "BUY"))
    _blocked(c)
    assert c.alert.timestamp == ""


def test_rc94_phase3_real_risk_buy_wait_sell_wait(monkeypatch):
    c = _context("BUY")
    _run(c, _risk_engine(monkeypatch, "BUY"))
    assert c.alert.valid and c.alert.action == "BUY"
    c.strategy.valid = False
    _run(c, _risk_engine(monkeypatch, "BUY"))
    _blocked(c)
    c.strategy.valid = True
    c.strategy.signal = "SELL"
    _run(c, _risk_engine(monkeypatch, "SELL"))
    assert c.alert.valid and c.alert.action == "SELL"
    c.strategy.valid = False
    _run(c, _risk_engine(monkeypatch, "SELL"))
    _blocked(c)


def test_rc94_phase3_mismatched_decision_prices_should_not_alert(monkeypatch):
    """Auditoria adversarial: alterar decisao apos aprovacao do risco.

    Se falhar, registra possivel lacuna de validacao cruzada; nao alterar
    producao automaticamente antes de investigar o contrato de seguranca.
    """
    c = _run(_context("BUY"), _risk_engine(monkeypatch, "BUY"))
    assert c.alert.valid is True
    c.decision.entry = c.risk.entry_price + 1.0
    with redirect_stdout(StringIO()):
        AlertManager().executar(c)
    assert c.alert.valid is False, "ALERTA_INCONSISTENTE_COM_RISCO: investigar validacao cruzada"
