"""RC9.5-A3: testes adversariais offline do contrato DecisionEngine.

Estes testes são diagnósticos: falhas indicam comportamento a investigar.
Não executam ordens, não usam dados de mercado nem alteram arquivos.
"""

import pytest

from core.analysis_context import AnalysisContext
from decision.decision_engine import DecisionEngine


def _contexto_valido():
    ctx = AnalysisContext()
    ctx.strategy.valid = True
    ctx.strategy.name = "SETUP_RC95_CONTROLADO"
    ctx.strategy.signal = "BUY"
    ctx.score.valid = True
    ctx.score.total = 92.0
    ctx.score.confidence = 0.92
    ctx.risk.valid = True
    ctx.risk.approved = True
    ctx.risk.entry_price = 100.0
    ctx.risk.stop_loss = 90.0
    ctx.risk.take_profit = 120.0
    ctx.risk.risk_reward = 2.0
    return ctx


def _executar(ctx):
    result = DecisionEngine().executar(ctx)
    assert result is ctx
    return ctx.decision


def test_rc95_controle_buy_valido():
    decision = _executar(_contexto_valido())
    assert decision.valid is True
    assert decision.action == "BUY"
    assert (decision.entry, decision.stop, decision.target) == (100.0, 90.0, 120.0)


def test_rc95_risco_invalido_nao_pode_aprovar_decisao():
    ctx = _contexto_valido()
    ctx.risk.valid = False
    decision = _executar(ctx)
    assert decision.valid is False
    assert decision.action == "WAIT"


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("entry_price", 0.0),
        ("stop_loss", -1.0),
        ("take_profit", float("nan")),
        ("entry_price", float("inf")),
        ("stop_loss", 110.0),  # BUY: stop acima da entrada
        ("take_profit", 95.0),  # BUY: alvo abaixo da entrada
    ],
)
def test_rc95_preco_invalido_nao_pode_aprovar_decisao(campo, valor):
    ctx = _contexto_valido()
    setattr(ctx.risk, campo, valor)
    decision = _executar(ctx)
    assert decision.valid is False
    assert decision.action == "WAIT"


@pytest.mark.parametrize("valor", [0.0, -1.0, float("nan"), float("inf")])
def test_rc95_rr_invalido_nao_pode_aprovar_decisao(valor):
    ctx = _contexto_valido()
    ctx.risk.risk_reward = valor
    decision = _executar(ctx)
    assert decision.valid is False
    assert decision.action == "WAIT"


@pytest.mark.parametrize("campo,valor", [("total", float("nan")), ("confidence", float("inf"))])
def test_rc95_score_nao_finito_nao_pode_aprovar_decisao(campo, valor):
    ctx = _contexto_valido()
    setattr(ctx.score, campo, valor)
    decision = _executar(ctx)
    assert decision.valid is False
    assert decision.action == "WAIT"


def test_rc95_decisao_anterior_e_limpa_antes_de_wait():
    ctx = _contexto_valido()
    assert _executar(ctx).valid is True
    ctx.strategy.valid = False
    decision = _executar(ctx)
    assert decision.valid is False
    assert decision.action == "WAIT"
    assert decision.direction not in ("BUY", "SELL")
    assert decision.entry not in (100.0,)
