from types import SimpleNamespace

from analysis.replay.microstructure_confluence import MicrostructureConfluenceAudit


def _context(
    pa_bias="BUY",
    pressure="BUY",
    momentum="PERSISTENT_BUY",
    pattern="BUY",
    alignment="ALIGNED",
    structural_confidence=0.8,
    book_valid=True,
    book_pressure="BID_DOMINANT",
    concentration_bias="BID_DOMINANT",
    book_confidence=0.8,
    book_duplicate=False,
):
    return SimpleNamespace(
        price_action=SimpleNamespace(bias=pa_bias),
        order_flow=SimpleNamespace(
            pressure=pressure,
            flow_momentum=momentum,
            pattern_direction=pattern,
            structure_alignment=alignment,
            structural_pattern_confidence=structural_confidence,
        ),
        book_depth_analysis=SimpleNamespace(
            valid=book_valid,
            pressure=book_pressure,
            concentration_bias=concentration_bias,
            confidence=book_confidence,
            duplicate_evidence_risk=book_duplicate,
        ),
    )


def test_three_independent_sources_produce_high_quality():
    result = MicrostructureConfluenceAudit().analyze(_context())
    assert result.state == "CONFIRMED"
    assert result.independent_evidence_count == 3
    assert result.confluence_quality == "HIGH"


def test_correlated_book_does_not_increase_independent_count():
    result = MicrostructureConfluenceAudit().analyze(_context(book_duplicate=True))
    assert result.independent_evidence_count == 2
    assert result.correlated_evidence_count >= 1
    assert result.confluence_quality == "MEDIUM"


def test_delta_subsignals_count_as_single_independent_family():
    result = MicrostructureConfluenceAudit().analyze(_context())
    assert result.flow_direction == "BUY"
    assert result.independent_evidence_count == 3
    assert result.correlated_evidence_count == 1


def test_book_conflict_forces_conflict_state():
    result = MicrostructureConfluenceAudit().analyze(
        _context(book_pressure="ASK_DOMINANT", concentration_bias="ASK_DOMINANT")
    )
    assert result.state == "CONFLICT"
    assert result.conflict_count == 1
    assert result.confluence_quality == "CONFLICT"


def test_order_flow_conflict_forces_conflict_state():
    result = MicrostructureConfluenceAudit().analyze(
        _context(pressure="SELL", momentum="PERSISTENT_SELL", pattern="SELL")
    )
    assert result.state == "CONFLICT"
    assert result.direction == "SELL"


def test_book_unavailable_preserves_price_action_plus_flow_confirmation():
    result = MicrostructureConfluenceAudit().analyze(_context(book_valid=False))
    assert result.book_available is False
    assert result.independent_evidence_count == 2
    assert result.confluence_quality == "MEDIUM"


def test_book_only_can_confirm_price_action_when_flow_is_mixed():
    result = MicrostructureConfluenceAudit().analyze(
        _context(pressure="BUY", momentum="PERSISTENT_SELL", pattern="NONE")
    )
    assert result.flow_direction == "NONE"
    assert result.state == "CONFIRMED"
    assert result.independent_evidence_count == 2


def test_independent_book_adds_more_confidence_than_correlated_book():
    independent = MicrostructureConfluenceAudit().analyze(_context(book_duplicate=False))
    correlated = MicrostructureConfluenceAudit().analyze(_context(book_duplicate=True))
    assert independent.confidence > correlated.confidence


def test_no_price_action_bias_remains_insufficient():
    result = MicrostructureConfluenceAudit().analyze(_context(pa_bias="NONE"))
    assert result.state == "INSUFFICIENT_DATA"
    assert result.independent_evidence_count == 0
    assert result.confidence == 0.0


def test_snapshot_remains_passive_and_readonly_contract():
    result = MicrostructureConfluenceAudit().analyze(_context())
    assert result.passive_only is True
    data = result.to_dict()
    assert data["book_available"] is True
    assert data["book_direction"] == "BUY"
    assert data["independent_evidence_count"] == 3
