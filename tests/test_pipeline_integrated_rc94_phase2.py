"""RC9.4 fase 2 — regressao offline com engines reais e pipeline completo.

Nao conecta Profit/RTD, nao envia ordens, nao modifica codigo de producao.
"""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import runpy

import pytest

from core.analysis_context import AnalysisContext
from strategies.strategy_engine import StrategyEngine
from ai.score_engine_rc13_2 import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine
from alerts.alert_manager import AlertManager
from analysis.analysis_pipeline import AnalysisPipeline


def _chain(context, *, strategy_engine=None):
    engines = [
        strategy_engine or StrategyEngine(),
        ScoreEngine(enable_order_flow=False, enable_regime_mtf=False),
        RiskManager(),
        DecisionEngine(),
        AlertManager(),
    ]
    with redirect_stdout(StringIO()):
        for engine in engines:
            assert engine.executar(context) is context
    return context


class _NoSetup:
    ENABLED = True
    def executar(self, context):
        from models.strategy_result import StrategyResult
        return StrategyResult()


class _SyntheticSetup:
    ENABLED = True
    def __init__(self, direction):
        self.direction = direction
    def executar(self, context):
        from models.strategy_result import StrategyResult
        result = StrategyResult()
        result.valid = True
        result.name = 'RC94_CONTROLLED'
        result.signal = self.direction
        result.score = 95.0
        return result


def _strategy_with(setup):
    engine = StrategyEngine()
    engine.setups = [setup]
    return engine


def _assert_blocked(context):
    assert context.decision.action == 'WAIT'
    assert context.decision.valid is False
    assert context.alert.valid is False
    assert context.alert.action == 'NONE'
    assert context.alert.timestamp == ''


def test_rc94_real_chain_no_setup_blocks_alert():
    context = _chain(AnalysisContext(), strategy_engine=_strategy_with(_NoSetup()))
    assert context.strategy.valid is False
    assert context.score.valid is False
    assert context.risk.approved is False
    _assert_blocked(context)


@pytest.mark.parametrize('direction', ['BUY', 'SELL'])
def test_rc94_real_chain_setup_without_market_confluence_blocks(direction):
    context = _chain(AnalysisContext(), strategy_engine=_strategy_with(_SyntheticSetup(direction)))
    assert context.strategy.valid is True
    assert context.strategy.signal == direction
    assert context.score.valid is False
    assert context.risk.approved is False
    _assert_blocked(context)


def test_rc94_real_chain_stale_alert_cleared_on_next_cycle():
    context = AnalysisContext()
    context.alert.valid = True
    context.alert.action = 'BUY'
    context.alert.timestamp = 'STALE'
    context.decision.valid = True
    context.decision.action = 'BUY'
    _chain(context, strategy_engine=_strategy_with(_NoSetup()))
    _assert_blocked(context)


def _controlled_market():
    # Reutiliza exatamente a fixture do teste de integracao existente.
    test_file = Path(__file__).resolve().parent / 'test_full_pipeline_controlled.py'
    fixture = runpy.run_path(str(test_file))
    return fixture['construir_historico']()


def test_rc94_full_pipeline_reused_context_stale_alert_cleared():
    context = AnalysisContext(market=_controlled_market())
    pipeline = AnalysisPipeline()
    with redirect_stdout(StringIO()):
        assert pipeline.executar(context) is context
    _assert_blocked(context)
    context.alert.valid = True
    context.alert.action = 'SELL'
    context.alert.timestamp = 'STALE'
    context.decision.valid = True
    context.decision.action = 'SELL'
    with redirect_stdout(StringIO()):
        assert pipeline.executar(context) is context
    _assert_blocked(context)
    assert context.strategy.valid is False
    assert context.risk.approved is False
