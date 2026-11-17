"""RC9.7-A3: contratos adversariais para recorders (somente offline).

Esperado antes da correcao: falhas que demonstram ausencia de isolamento
ou de invalidacao de resultados operacionais em caso de excecao.
"""

import pytest

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext


RECORDERS = (
    'book_diagnostics_replay',
    'score_regime_mtf_ab',
    'score_external_context_ab',
    'score_order_flow_ab',
    'score_order_flow_structure_ab',
    'score_book_depth_ab',
    'score_microstructure_eligibility_ab',
    'microstructure_confluence_replay',
    'microstructure_eligibility_replay',
)


class _Engine:
    ENABLED = True

    def executar(self, context):
        context.risk.valid = True
        context.risk.approved = True
        context.risk.entry_price = 100.0
        context.decision.valid = True
        context.decision.action = 'BUY'
        context.alert.valid = True
        context.alert.action = 'BUY'
        return context


def _pipeline():
    pipeline = AnalysisPipeline()
    pipeline.engines = [_Engine()]
    pipeline._refresh_trader_psychology = lambda: None
    for name in RECORDERS:
        getattr(pipeline, name).record = lambda context: None
    return pipeline


@pytest.mark.parametrize('recorder_name', RECORDERS)
def test_rc97_recorder_exception_invalidates_operational_results(recorder_name):
    pipeline = _pipeline()

    def failing_recorder(context):
        raise RuntimeError('RC97_RECORDER_FAILURE')

    getattr(pipeline, recorder_name).record = failing_recorder
    context = AnalysisContext()
    with pytest.raises(RuntimeError, match='RC97_RECORDER_FAILURE'):
        pipeline.executar(context)
    assert context.decision.valid is False, f'{recorder_name}: DECISAO_VALIDA_APOS_FALHA'
    assert context.alert.valid is False, f'{recorder_name}: ALERTA_VALIDO_APOS_FALHA'
    assert context.risk.valid is False, f'{recorder_name}: RISCO_VALIDO_APOS_FALHA'


@pytest.mark.parametrize('recorder_name', RECORDERS)
def test_rc97_recorder_cannot_modify_official_decision(recorder_name):
    pipeline = _pipeline()

    def hostile_recorder(context):
        context.decision.valid = False
        context.decision.action = 'SELL'
        context.alert.action = 'SELL'

    getattr(pipeline, recorder_name).record = hostile_recorder
    context = pipeline.executar(AnalysisContext())
    assert context.decision.valid is True, f'{recorder_name}: DECISAO_MUTADA'
    assert context.decision.action == 'BUY', f'{recorder_name}: DIRECAO_MUTADA'
    assert context.alert.action == 'BUY', f'{recorder_name}: ALERTA_MUTADO'


@pytest.mark.parametrize('recorder_name', RECORDERS)
def test_rc97_recorder_cannot_modify_official_risk(recorder_name):
    pipeline = _pipeline()

    def hostile_recorder(context):
        context.risk.valid = False
        context.risk.approved = False
        context.risk.entry_price = 999.0

    getattr(pipeline, recorder_name).record = hostile_recorder
    context = pipeline.executar(AnalysisContext())
    assert context.risk.valid is True, f'{recorder_name}: RISCO_MUTADO'
    assert context.risk.approved is True, f'{recorder_name}: APROVACAO_MUTADA'
    assert context.risk.entry_price == 100.0, f'{recorder_name}: PRECO_MUTADO'
