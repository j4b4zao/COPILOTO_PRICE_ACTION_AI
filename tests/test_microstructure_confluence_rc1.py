from types import SimpleNamespace

from analysis.replay.microstructure_confluence import MicrostructureConfluenceAudit


def _context(pa_bias="BUY", pressure="BUY", momentum="PERSISTENT_BUY", pattern="BUY", alignment="ALIGNED", confidence=0.8):
    return SimpleNamespace(
        price_action=SimpleNamespace(bias=pa_bias),
        order_flow=SimpleNamespace(
            pressure=pressure,
            flow_momentum=momentum,
            pattern_direction=pattern,
            structure_alignment=alignment,
            structural_pattern_confidence=confidence,
        ),
    )


def test_confirmed_buy_confluence():
    result = MicrostructureConfluenceAudit().analyze(_context())
    assert result.state == "CONFIRMED"
    assert result.direction == "BUY"


def test_confirmed_sell_confluence():
    result = MicrostructureConfluenceAudit().analyze(
        _context(pa_bias="SELL", pressure="SELL", momentum="ACCELERATING_SELL", pattern="SELL")
    )
    assert result.state == "CONFIRMED"
    assert result.direction == "SELL"


def test_conflict_when_flow_opposes_price_action():
    result = MicrostructureConfluenceAudit().analyze(
        _context(pa_bias="BUY", pressure="SELL", momentum="PERSISTENT_SELL", pattern="SELL")
    )
    assert result.state == "CONFLICT"
    assert result.direction == "SELL"


def test_no_price_action_bias_is_insufficient():
    result = MicrostructureConfluenceAudit().analyze(_context(pa_bias="NONE"))
    assert result.state == "INSUFFICIENT_DATA"
    assert result.confidence == 0.0


def test_mixed_flow_vote_is_insufficient():
    result = MicrostructureConfluenceAudit().analyze(
        _context(pressure="BUY", momentum="PERSISTENT_SELL", pattern="NONE")
    )
    assert result.state == "INSUFFICIENT_DATA"


def test_acceleration_increases_confidence_over_fading():
    accelerating = MicrostructureConfluenceAudit().analyze(
        _context(momentum="ACCELERATING_BUY")
    )
    fading = MicrostructureConfluenceAudit().analyze(
        _context(momentum="FADING_BUY")
    )
    assert accelerating.confidence > fading.confidence


def test_structural_conflict_reduces_confidence():
    aligned = MicrostructureConfluenceAudit().analyze(_context(alignment="ALIGNED", confidence=0.8))
    conflict = MicrostructureConfluenceAudit().analyze(_context(alignment="CONFLICT", confidence=0.8))
    assert aligned.confidence > conflict.confidence


def test_book_is_explicitly_unavailable_until_real_depth_exists():
    result = MicrostructureConfluenceAudit().analyze(_context())
    assert result.book_available is False


def test_duplicate_delta_evidence_is_flagged():
    result = MicrostructureConfluenceAudit().analyze(_context())
    assert result.duplicate_evidence_risk is True


def test_snapshot_is_passive_and_readonly_contract():
    result = MicrostructureConfluenceAudit().analyze(_context())
    assert result.passive_only is True
    data = result.to_dict()
    assert data["price_action_bias"] == "BUY"
    assert data["book_available"] is False
