from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from analysis.replay.book_diagnostics_candidate_registry import BookDiagnosticsCandidateRegistry
from analysis.replay.book_diagnostics_shadow_mode import BookDiagnosticsShadowMode


STATE = "CLEAN_DIRECTIONAL_CONTEXT"


def _report():
    return SimpleNamespace(
        to_dict=lambda: {
            "book_state": STATE,
            "evidence_status": "READY_FOR_MANUAL_REVIEW",
            "sample_count": 100,
            "promotion_gate": {"status": "CANDIDATE_FOR_PROMOTION"},
            "walk_forward": {"walk_forward_stable": True},
        }
    )


def _registry(*, approved=True):
    registry = BookDiagnosticsCandidateRegistry()
    registry.register_evidence(_report(), timestamp="2026-08-22T10:00:00+00:00")
    if approved:
        registry.approve_for_shadow(
            STATE,
            note="RC18 passive shadow authorization",
            timestamp="2026-08-22T10:05:00+00:00",
        )
    return registry


def test_non_approved_candidate_is_blocked():
    shadow = BookDiagnosticsShadowMode(_registry(approved=False))
    blocked = False
    try:
        shadow.observe(
            book_state=STATE,
            shadow_action="BUY",
            official_action="WAIT",
        )
    except PermissionError:
        blocked = True
    assert blocked is True
    assert shadow.all() == []


def test_approved_candidate_records_passive_observation():
    shadow = BookDiagnosticsShadowMode(_registry())
    metadata = {"session": "OPEN", "regime": "TREND"}
    observation = shadow.observe(
        book_state=STATE,
        shadow_action="BUY",
        official_action="WAIT",
        market_price=172400.0,
        metadata=metadata,
        timestamp="2026-08-22T10:10:00+00:00",
    )
    metadata["session"] = "MUTATED"

    assert observation.book_state == STATE
    assert observation.shadow_action == "BUY"
    assert observation.official_action == "WAIT"
    assert observation.agreement is False
    assert observation.market_price == 172400.0
    assert observation.metadata["session"] == "OPEN"
    assert len(shadow.all()) == 1


def test_metrics_compare_shadow_with_official_without_promoting():
    registry = _registry()
    shadow = BookDiagnosticsShadowMode(registry)
    shadow.observe(book_state=STATE, shadow_action="BUY", official_action="BUY")
    shadow.observe(book_state=STATE, shadow_action="SELL", official_action="WAIT")
    shadow.observe(book_state=STATE, shadow_action="WAIT", official_action="SELL")

    metrics = shadow.metrics(STATE)
    record = registry.get(STATE)

    assert metrics["observations"] == 3
    assert metrics["shadow_directional"] == 2
    assert metrics["agreements"] == 1
    assert metrics["agreement_rate"] == 1 / 3
    assert metrics["official_wait_shadow_directional"] == 1
    assert metrics["shadow_wait_official_directional"] == 1
    assert record is not None
    assert record.status == "APPROVED_FOR_SHADOW"


def test_invalid_action_and_price_are_rejected():
    shadow = BookDiagnosticsShadowMode(_registry())

    invalid_action = False
    try:
        shadow.observe(book_state=STATE, shadow_action="EXECUTE", official_action="WAIT")
    except ValueError:
        invalid_action = True
    assert invalid_action is True

    invalid_price = False
    try:
        shadow.observe(
            book_state=STATE,
            shadow_action="BUY",
            official_action="WAIT",
            market_price=0,
        )
    except ValueError:
        invalid_price = True
    assert invalid_price is True
    assert shadow.all() == []


def test_json_round_trip_preserves_shadow_observations():
    registry = _registry()
    shadow = BookDiagnosticsShadowMode(registry)
    shadow.observe(
        book_state=STATE,
        shadow_action="BUY",
        official_action="WAIT",
        market_price=172400,
        metadata={"regime": "TREND"},
        timestamp="2026-08-22T10:10:00+00:00",
    )

    with TemporaryDirectory() as temp_dir:
        path = shadow.save_json(Path(temp_dir) / "shadow.json")
        loaded = BookDiagnosticsShadowMode.load_json(path, registry=registry)
        rows = loaded.all()

    assert len(rows) == 1
    assert rows[0]["book_state"] == STATE
    assert rows[0]["shadow_action"] == "BUY"
    assert rows[0]["official_action"] == "WAIT"
    assert rows[0]["metadata"]["regime"] == "TREND"


def test_load_requires_current_shadow_authorization():
    registry = _registry()
    shadow = BookDiagnosticsShadowMode(registry)
    shadow.observe(book_state=STATE, shadow_action="BUY", official_action="WAIT")

    with TemporaryDirectory() as temp_dir:
        path = shadow.save_json(Path(temp_dir) / "shadow.json")
        registry.reject(STATE, note="authorization revoked")
        blocked = False
        try:
            BookDiagnosticsShadowMode.load_json(path, registry=registry)
        except PermissionError:
            blocked = True

    assert blocked is True


if __name__ == "__main__":
    test_non_approved_candidate_is_blocked()
    test_approved_candidate_records_passive_observation()
    test_metrics_compare_shadow_with_official_without_promoting()
    test_invalid_action_and_price_are_rejected()
    test_json_round_trip_preserves_shadow_observations()
    test_load_requires_current_shadow_authorization()
    print("OK - BookDiagnostics Shadow Mode RC18")
