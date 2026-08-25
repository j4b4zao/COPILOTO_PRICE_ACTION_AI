from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from enums.trend import Trend


def _base_context():
    context = AnalysisContext()
    context.structure.valid = True
    context.structure.trend = Trend.UP
    context.liquidity.valid = True
    context.volume.valid = True
    context.volume.high = True
    context.price_action.valid = True
    return context


def _apply_external(context, *, risk="RISK_ON", bias="BULLISH", confidence=0.75, valid=True):
    state = context.external_market
    state.valid = valid
    state.risk_on_off = risk
    state.global_bias = bias
    state.confidence = confidence
    return context


def test_invalid_external_context_is_marked_unavailable():
    context = _base_context()
    ContextEngine().executar(context)
    assert context.checklist.external_context_ready is False
    assert context.checklist.external_context_status == "UNAVAILABLE"


def test_risk_on_confirms_buy_context():
    context = _apply_external(_base_context())
    ContextEngine().executar(context)
    assert context.checklist.external_context_ready is True
    assert context.checklist.external_context_aligned is True
    assert context.checklist.external_context_conflict is False
    assert context.checklist.external_context_status == "ALIGNED"


def test_risk_off_conflicts_with_buy_context():
    context = _apply_external(_base_context(), risk="RISK_OFF", bias="BEARISH")
    ContextEngine().executar(context)
    assert context.checklist.external_context_conflict is True
    assert context.checklist.external_context_status == "CONFLICT"


def test_neutral_external_context_is_neutral():
    context = _apply_external(_base_context(), risk="NEUTRAL", bias="NEUTRAL")
    ContextEngine().executar(context)
    assert context.checklist.external_context_status == "NEUTRAL"
    assert context.checklist.external_context_aligned is False
    assert context.checklist.external_context_conflict is False


def test_low_confidence_is_reported_as_low_confidence():
    context = _apply_external(_base_context(), confidence=0.20)
    ContextEngine().executar(context)
    assert context.checklist.external_context_status == "LOW_CONFIDENCE"
    assert context.checklist.external_context_confidence == 0.20


def test_confidence_is_clamped_in_checklist():
    context = _apply_external(_base_context(), confidence=2.0)
    ContextEngine().executar(context)
    assert context.checklist.external_context_confidence == 1.0


def test_external_context_does_not_change_confluences():
    without_external = _base_context()
    ContextEngine().executar(without_external)
    baseline = without_external.context.confluences

    with_external = _apply_external(_base_context())
    ContextEngine().executar(with_external)
    assert with_external.context.confluences == baseline


def test_external_context_does_not_change_context_validity():
    context = _apply_external(_base_context(), risk="RISK_OFF", bias="BEARISH")
    ContextEngine().executar(context)
    assert context.context.valid is True


def test_external_context_does_not_change_context_score():
    context = _apply_external(_base_context())
    ContextEngine().executar(context)
    assert context.context.score == 0.0


def test_clear_resets_external_checklist_fields():
    context = _apply_external(_base_context())
    ContextEngine().executar(context)
    context.checklist.clear()
    assert context.checklist.external_context_ready is False
    assert context.checklist.external_context_status == "UNAVAILABLE"
    assert context.checklist.external_context_confidence == 0.0
