import json
from tempfile import TemporaryDirectory
from pathlib import Path

from analysis.replay.book_diagnostics_promotion_approval_registry import (
    BookDiagnosticsPromotionApprovalRegistry,
)


def _contract(**overrides):
    data = {
        "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
        "target_layer": "CONTEXT",
        "initial_weight": 0.10,
        "probation_samples": 40,
        "status": "DRAFT_FOR_MANUAL_APPROVAL",
        "runtime_active": False,
        "manual_approval_required": True,
    }
    data.update(overrides)
    return data


def _expect(exception, fn):
    try:
        fn()
    except exception:
        return
    raise AssertionError(f"expected {exception.__name__}")


def test_register_contract_is_pending_and_runtime_inactive():
    registry = BookDiagnosticsPromotionApprovalRegistry()
    record = registry.register_contract(_contract(), timestamp="2026-08-22T20:00:00+00:00")
    assert record.status == "PENDING_MANUAL_APPROVAL"
    assert record.runtime_active is False
    assert record.history[-1]["action"] == "CONTRACT_REGISTERED"


def test_manual_approval_prepares_probation_without_runtime_activation():
    registry = BookDiagnosticsPromotionApprovalRegistry()
    registry.register_contract(_contract())
    record = registry.approve_for_probation(
        "CLEAN_DIRECTIONAL_CONTEXT",
        approved_by="operator",
        note="approved for controlled probation",
    )
    assert record.status == "APPROVED_FOR_PROBATION"
    assert record.approved_by == "operator"
    assert record.runtime_active is False
    assert record.history[-1]["action"] == "MANUAL_APPROVAL_FOR_PROBATION"


def test_approval_requires_named_approver():
    registry = BookDiagnosticsPromotionApprovalRegistry()
    registry.register_contract(_contract())
    _expect(
        ValueError,
        lambda: registry.approve_for_probation(
            "CLEAN_DIRECTIONAL_CONTEXT",
            approved_by="",
        ),
    )


def test_runtime_active_contract_is_rejected():
    registry = BookDiagnosticsPromotionApprovalRegistry()
    _expect(
        PermissionError,
        lambda: registry.register_contract(_contract(runtime_active=True)),
    )


def test_non_draft_contract_is_rejected():
    registry = BookDiagnosticsPromotionApprovalRegistry()
    _expect(
        PermissionError,
        lambda: registry.register_contract(_contract(status="ACTIVE")),
    )


def test_revocation_keeps_runtime_inactive():
    registry = BookDiagnosticsPromotionApprovalRegistry()
    registry.register_contract(_contract())
    registry.approve_for_probation("CLEAN_DIRECTIONAL_CONTEXT", approved_by="operator")
    record = registry.revoke("CLEAN_DIRECTIONAL_CONTEXT", note="evidence degraded")
    assert record.status == "REVOKED"
    assert record.runtime_active is False
    assert record.history[-1]["action"] == "MANUAL_REVOCATION"


def test_json_round_trip_preserves_approval_history():
    registry = BookDiagnosticsPromotionApprovalRegistry()
    registry.register_contract(_contract())
    registry.approve_for_probation("CLEAN_DIRECTIONAL_CONTEXT", approved_by="operator")

    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "approvals.json"
        registry.save_json(path)
        restored = BookDiagnosticsPromotionApprovalRegistry.load_json(path)

    record = restored.get("CLEAN_DIRECTIONAL_CONTEXT")
    assert record.status == "APPROVED_FOR_PROBATION"
    assert record.runtime_active is False
    assert len(record.history) == 2


def test_loader_rejects_runtime_active_payload():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.json"
        payload = {
            "version": "RC22-PROMOTION-APPROVAL-REGISTRY",
            "records": [{
                "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
                "target_layer": "CONTEXT",
                "initial_weight": 0.1,
                "probation_samples": 40,
                "status": "APPROVED_FOR_PROBATION",
                "approved_by": "operator",
                "approval_note": "",
                "created_at": "x",
                "updated_at": "x",
                "runtime_active": True,
                "history": [],
            }],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        _expect(
            ValueError,
            lambda: BookDiagnosticsPromotionApprovalRegistry.load_json(path),
        )
