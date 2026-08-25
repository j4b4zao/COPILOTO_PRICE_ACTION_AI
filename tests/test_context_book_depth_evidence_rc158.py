from types import SimpleNamespace

from brain.context_engine import ContextEngine
from models.book_depth_analysis_result import BookDepthAnalysisResult
from models.trade_checklist import TradeChecklist


def _narrative():
    return SimpleNamespace(strengths=[], weaknesses=[])


def _book(*, pressure="BID_DOMINANT", confidence=0.8, valid=True, duplicate=False):
    result = BookDepthAnalysisResult()
    result.valid = valid
    result.pressure = pressure
    result.imbalance = 0.4 if pressure == "BID_DOMINANT" else -0.4 if pressure == "ASK_DOMINANT" else 0.0
    result.spread_ratio = 0.0005
    result.concentration_bias = pressure if pressure in {"BID_DOMINANT", "ASK_DOMINANT"} else "BALANCED"
    result.confidence = confidence
    result.duplicate_evidence_risk = duplicate
    return result


def test_unavailable_book_is_informational_only():
    checklist = TradeChecklist()
    narrative = _narrative()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, _book(valid=False), narrative
    )
    assert checklist.book_depth_status == "UNAVAILABLE"
    assert checklist.book_depth_ready is False
    assert narrative.weaknesses


def test_bid_dominant_aligns_with_buy_bias():
    checklist = TradeChecklist()
    narrative = _narrative()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, _book(), narrative
    )
    assert checklist.book_depth_aligned is True
    assert checklist.book_depth_status == "ALIGNED"
    assert narrative.strengths


def test_ask_dominant_aligns_with_sell_bias():
    checklist = TradeChecklist()
    narrative = _narrative()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="SELL"), checklist, _book(pressure="ASK_DOMINANT"), narrative
    )
    assert checklist.book_depth_aligned is True
    assert checklist.book_depth_status == "ALIGNED"


def test_book_conflict_is_reported():
    checklist = TradeChecklist()
    narrative = _narrative()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, _book(pressure="ASK_DOMINANT"), narrative
    )
    assert checklist.book_depth_conflict is True
    assert checklist.book_depth_status == "CONFLICT"
    assert narrative.weaknesses


def test_balanced_book_is_neutral():
    checklist = TradeChecklist()
    narrative = _narrative()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, _book(pressure="BALANCED"), narrative
    )
    assert checklist.book_depth_status == "NEUTRAL"
    assert not checklist.book_depth_aligned
    assert not checklist.book_depth_conflict


def test_directional_book_without_operational_bias_is_observational():
    checklist = TradeChecklist()
    narrative = _narrative()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="NONE"), checklist, _book(), narrative
    )
    assert checklist.book_depth_status == "NO_OPERATIONAL_BIAS"
    assert not checklist.book_depth_aligned
    assert not checklist.book_depth_conflict


def test_duplicate_evidence_risk_is_exposed():
    checklist = TradeChecklist()
    narrative = _narrative()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, _book(duplicate=True), narrative
    )
    assert checklist.book_depth_duplicate_evidence_risk is True
    assert any("duplicidade" in message for message in narrative.weaknesses)


def test_book_metrics_are_clamped_for_checklist():
    book = _book(confidence=3.0)
    book.imbalance = 4.0
    book.spread_ratio = -2.0
    checklist = TradeChecklist()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, book, _narrative()
    )
    assert checklist.book_depth_confidence == 1.0
    assert checklist.book_depth_imbalance == 1.0
    assert checklist.book_depth_spread_ratio == 0.0


def test_book_fields_do_not_change_operational_checklist_score_or_completion():
    checklist = TradeChecklist()
    checklist.trend = True
    checklist.structure = True
    checklist.volume = True
    checklist.liquidity = True
    before_score = checklist.score
    before_completion = checklist.completion

    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, _book(), _narrative()
    )

    assert checklist.score == before_score
    assert checklist.completion == before_completion
    assert checklist.ready is True


def test_clear_resets_book_fields_without_changing_operational_contract():
    checklist = TradeChecklist()
    ContextEngine._append_book_depth_evidence(
        SimpleNamespace(bias="BUY"), checklist, _book(duplicate=True), _narrative()
    )
    checklist.clear()
    assert checklist.book_depth_ready is False
    assert checklist.book_depth_status == "UNAVAILABLE"
    assert checklist.book_depth_confidence == 0.0
    assert checklist.book_depth_duplicate_evidence_risk is False
    assert checklist.score == 0
