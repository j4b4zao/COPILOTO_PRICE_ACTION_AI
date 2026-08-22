from types import SimpleNamespace

import pytest

from analysis.replay.book_diagnostics_candidate_registry import (
    BookDiagnosticsCandidateRegistry,
)


def _report(
    *,
    state="CLEAN_DIRECTIONAL_CONTEXT",
    evidence_status="KEEP_RESEARCHING",
    gate_status="KEEP_OBSERVING",
    stable=False,
    samples=40,
):
    return SimpleNamespace(
        to_dict=lambda: {
            "book_state": state,
            "evidence_status": evidence_status,
            "sample_count": samples,
            "promotion_gate": {"status": gate_status},
            "walk_forward": {"walk_forward_stable": stable},
        }
    )


def test_new_candidate_starts_researching():
    registry = BookDiagnosticsCandidateRegistry()
    record = registry.register_evidence(_report(), timestamp="2026-08-22T10:00:00+00:00")
    assert record.status == "RESEARCHING"
    assert record.latest_sample_count == 40
    assert len(record.history) == 1


def test_ready_evidence_moves_candidate_to_manual_review():
    registry = BookDiagnosticsCandidateRegistry()
    record = registry.register_evidence(
        _report(
            evidence_status="READY_FOR_MANUAL_REVIEW",
            gate_status="CANDIDATE_FOR_PROMOTION",
            stable=True,
            samples=100,
        )
    )
    assert record.status == "MANUAL_REVIEW"


def test_shadow_approval_requires_manual_review():
    registry = BookDiagnosticsCandidateRegistry()
    registry.register_evidence(_report())
    with pytest.raises(ValueError):
        registry.approve_for_shadow("CLEAN_DIRECTIONAL_CONTEXT")


def test_manual_review_can_be_approved_for_shadow():
    registry = BookDiagnosticsCandidateRegistry()
    registry.register_evidence(
        _report(
            evidence_status="READY_FOR_MANUAL_REVIEW",
            gate_status="CANDIDATE_FOR_PROMOTION",
            stable=True,
            samples=100,
        )
    )
    record = registry.approve_for_shadow(
        "CLEAN_DIRECTIONAL_CONTEXT",
        note="approved for passive shadow observation",
    )
    assert record.status == "APPROVED_FOR_SHADOW"
    assert "passive shadow" in record.manual_notes


def test_gate_rejection_marks_candidate_rejected():
    registry = BookDiagnosticsCandidateRegistry()
    record = registry.register_evidence(
        _report(gate_status="REJECTED", evidence_status="KEEP_RESEARCHING")
    )
    assert record.status == "REJECTED"


def test_json_round_trip_preserves_history(tmp_path):
    registry = BookDiagnosticsCandidateRegistry()
    registry.register_evidence(
        _report(
            evidence_status="READY_FOR_MANUAL_REVIEW",
            gate_status="CANDIDATE_FOR_PROMOTION",
            stable=True,
            samples=90,
        ),
        timestamp="2026-08-22T10:00:00+00:00",
    )
    path = registry.save_json(tmp_path / "registry.json")
    loaded = BookDiagnosticsCandidateRegistry.load_json(path)
    record = loaded.get("CLEAN_DIRECTIONAL_CONTEXT")
    assert record is not None
    assert record.status == "MANUAL_REVIEW"
    assert record.latest_sample_count == 90
    assert len(record.history) == 1


def test_filter_by_status():
    registry = BookDiagnosticsCandidateRegistry()
    registry.register_evidence(_report(state="A"))
    registry.register_evidence(
        _report(state="B", gate_status="REJECTED")
    )
    researching = registry.by_status("RESEARCHING")
    rejected = registry.by_status("REJECTED")
    assert [item["book_state"] for item in researching] == ["A"]
    assert [item["book_state"] for item in rejected] == ["B"]
