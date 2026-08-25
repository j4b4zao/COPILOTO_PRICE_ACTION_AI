from types import SimpleNamespace

from brain.context_engine import ContextEngine
from models.market_narrative import MarketNarrative
from models.trade_checklist import TradeChecklist


def _result(bias="BUY"):
    return SimpleNamespace(bias=bias)


def _order_flow(direction="BUY", alignment="ALIGNED", confidence=0.8):
    return SimpleNamespace(
        valid=True,
        flow_momentum="MIXED",
        delta_persistence=0.0,
        delta_acceleration=0.0,
        delta_impulse_ratio=0.0,
        pattern_direction=direction,
        structure_alignment=alignment,
        structural_pattern_confidence=confidence,
    )


def _run(direction="BUY", alignment="ALIGNED", confidence=0.8, bias="BUY"):
    checklist = TradeChecklist()
    narrative = MarketNarrative()
    ContextEngine._append_order_flow_evidence(
        _result(bias), checklist, _order_flow(direction, alignment, confidence), narrative
    )
    return checklist, narrative


def test_aligned_pattern_is_exposed_in_checklist():
    checklist, _ = _run()
    assert checklist.order_flow_pattern_direction == "BUY"
    assert checklist.order_flow_structure_alignment == "ALIGNED"
    assert checklist.order_flow_structural_confidence == 0.8


def test_aligned_pattern_matching_bias_is_strength():
    _, narrative = _run(direction="BUY", alignment="ALIGNED", bias="BUY")
    assert any("confirma a estrutura" in text for text in narrative.strengths)


def test_aligned_pattern_opposite_bias_is_weakness():
    _, narrative = _run(direction="SELL", alignment="ALIGNED", bias="BUY")
    assert any("direção oposta" in text for text in narrative.weaknesses)


def test_structure_conflict_is_weakness():
    _, narrative = _run(alignment="CONFLICT", confidence=0.48)
    assert any("conflita com a estrutura" in text for text in narrative.weaknesses)


def test_neutral_structure_is_weakness():
    _, narrative = _run(alignment="NEUTRAL", confidence=0.6)
    assert any("estrutura neutra/lateral" in text for text in narrative.weaknesses)


def test_unavailable_structure_is_weakness():
    _, narrative = _run(alignment="UNAVAILABLE")
    assert any("sem estrutura disponível" in text for text in narrative.weaknesses)


def test_none_direction_adds_no_structural_message():
    checklist, narrative = _run(direction="NONE", alignment="NEUTRAL")
    assert checklist.order_flow_pattern_direction == "NONE"
    assert not any("Absorção/exaustão" in text for text in narrative.strengths + narrative.weaknesses)


def test_structural_confidence_is_clamped():
    checklist, _ = _run(confidence=2.0)
    assert checklist.order_flow_structural_confidence == 1.0
    checklist, _ = _run(confidence=-1.0)
    assert checklist.order_flow_structural_confidence == 0.0


def test_new_fields_do_not_change_checklist_score_or_completion():
    checklist = TradeChecklist()
    before_score = checklist.score
    before_completion = checklist.completion
    checklist.order_flow_pattern_direction = "BUY"
    checklist.order_flow_structure_alignment = "ALIGNED"
    checklist.order_flow_structural_confidence = 1.0
    assert checklist.score == before_score
    assert checklist.completion == before_completion


def test_clear_resets_new_fields():
    checklist, _ = _run()
    checklist.clear()
    assert checklist.order_flow_pattern_direction == "NONE"
    assert checklist.order_flow_structure_alignment == "UNAVAILABLE"
    assert checklist.order_flow_structural_confidence == 0.0
