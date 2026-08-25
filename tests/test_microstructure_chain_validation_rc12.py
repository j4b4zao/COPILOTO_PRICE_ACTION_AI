from analysis.book_depth_analysis import BookDepthAnalysis
from analysis.replay.microstructure_confluence import MicrostructureConfluenceAudit
from analysis.replay.microstructure_eligibility_policy import MicrostructureEligibilityPolicy
from core.analysis_context import AnalysisContext
from models.book_depth import BookDepthSnapshot


def _book(bid_qty=180.0, ask_qty=40.0):
    return BookDepthSnapshot.build(
        symbol="WINV26",
        timestamp="2026-08-23T10:00:00",
        bids=[(100.0, bid_qty), (99.5, 60.0), (99.0, 40.0)],
        asks=[(100.5, ask_qty), (101.0, 20.0), (101.5, 10.0)],
        source="TEST",
    )


def _prepare_context(*, pa_bias="BUY", flow_pressure="BUY", momentum="ACCELERATING_BUY", pattern="BUY", book=True):
    context = AnalysisContext()
    context.price_action.bias = pa_bias
    context.order_flow.pressure = flow_pressure
    context.order_flow.flow_momentum = momentum
    context.order_flow.pattern_direction = pattern
    context.order_flow.structure_alignment = "ALIGNED"
    context.order_flow.structural_pattern_confidence = 0.8
    if book:
        context.book_depth = _book()
        BookDepthAnalysis().executar(context)
    return context


def test_buy_chain_reaches_confirmed_confluence():
    context = _prepare_context()
    snap = MicrostructureConfluenceAudit().analyze(context)
    assert snap.state == "CONFIRMED"
    assert snap.direction == "BUY"


def test_buy_chain_counts_book_as_correlated_when_delta_agrees():
    context = _prepare_context()
    snap = MicrostructureConfluenceAudit().analyze(context)
    assert snap.independent_evidence_count == 2
    assert snap.correlated_evidence_count >= 1


def test_correlated_book_prevents_strong_candidate():
    context = _prepare_context()
    snap = MicrostructureConfluenceAudit().analyze(context)
    decision = MicrostructureEligibilityPolicy().evaluate(snap)
    assert decision.state in {"PROMISING", "OBSERVABLE"}
    assert decision.state != "STRONG_CANDIDATE"


def test_independent_book_can_reach_three_sources():
    context = _prepare_context(flow_pressure="BALANCED", momentum="ACCELERATING_BUY", pattern="BUY")
    context.book_depth_analysis.duplicate_evidence_risk = False
    snap = MicrostructureConfluenceAudit().analyze(context)
    assert snap.independent_evidence_count == 3
    assert snap.confluence_quality == "HIGH"


def test_three_independent_high_confidence_can_be_strong_candidate():
    context = _prepare_context(flow_pressure="BALANCED", momentum="ACCELERATING_BUY", pattern="BUY")
    context.book_depth_analysis.duplicate_evidence_risk = False
    context.book_depth_analysis.confidence = 1.0
    snap = MicrostructureConfluenceAudit().analyze(context)
    decision = MicrostructureEligibilityPolicy().evaluate(snap)
    assert decision.state == "STRONG_CANDIDATE"


def test_book_conflict_propagates_to_confluence_and_blocks_eligibility():
    context = _prepare_context(pa_bias="SELL", flow_pressure="SELL", momentum="ACCELERATING_SELL", pattern="SELL")
    context.book_depth = _book()
    BookDepthAnalysis().executar(context)
    snap = MicrostructureConfluenceAudit().analyze(context)
    decision = MicrostructureEligibilityPolicy().evaluate(snap)
    assert snap.state == "CONFLICT"
    assert snap.conflict_count >= 1
    assert decision.state == "NOT_ELIGIBLE"


def test_no_book_keeps_chain_operational_with_two_independent_sources():
    context = _prepare_context(book=False)
    snap = MicrostructureConfluenceAudit().analyze(context)
    assert snap.book_available is False
    assert snap.independent_evidence_count == 2
    assert snap.state == "CONFIRMED"


def test_no_price_action_bias_is_insufficient_data():
    context = _prepare_context(pa_bias="NONE")
    snap = MicrostructureConfluenceAudit().analyze(context)
    decision = MicrostructureEligibilityPolicy().evaluate(snap)
    assert snap.state == "INSUFFICIENT_DATA"
    assert decision.state == "NOT_ELIGIBLE"


def test_chain_is_passive_only_end_to_end():
    context = _prepare_context()
    before_score = context.score.to_dict()
    before_decision = context.decision.to_dict()
    snap = MicrostructureConfluenceAudit().analyze(context)
    decision = MicrostructureEligibilityPolicy().evaluate(snap)
    assert snap.passive_only is True
    assert decision.passive_only is True
    assert context.score.to_dict() == before_score
    assert context.decision.to_dict() == before_decision


def test_book_analysis_uses_current_cycle_price_action_bias():
    context = AnalysisContext()
    context.price_action.bias = "BUY"
    context.order_flow.pressure = "SELL"
    context.book_depth = _book()
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.price_action_alignment == "ALIGNED"
    assert context.book_depth_analysis.order_flow_alignment == "CONFLICT"
