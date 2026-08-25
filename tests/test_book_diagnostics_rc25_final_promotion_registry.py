from tempfile import TemporaryDirectory
from pathlib import Path

from analysis.replay.book_diagnostics_final_promotion_registry import (
    BookDiagnosticsFinalPromotionRegistry,
)


class FakeReview:
    def __init__(self, recommendation="PROMOTE", runtime_active=False, manual_required=True):
        self.payload = {
            "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
            "target_layer": "CONTEXT",
            "recommendation": recommendation,
            "manual_approval_required": manual_required,
            "runtime_active": runtime_active,
        }

    def to_dict(self):
        return dict(self.payload)


def _registry_with_record():
    registry = BookDiagnosticsFinalPromotionRegistry()
    registry.register_review(
        FakeReview(),
        approved_weight=0.10,
        source_version="RC24",
        rollback_plan={"max_stop_first_rate": 0.50},
        timestamp="2026-08-22T20:00:00+00:00",
    )
    return registry


def _expect_exception(exc_type, fn):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_register_promote_review_starts_pending_and_inactive():
    registry = _registry_with_record()
    record = registry.get("CLEAN_DIRECTIONAL_CONTEXT")
    assert record.status == "PENDING_FINAL_APPROVAL"
    assert record.runtime_active is False
    assert record.approved_weight == 0.10


def test_non_promote_review_is_rejected():
    registry = BookDiagnosticsFinalPromotionRegistry()
    _expect_exception(
        PermissionError,
        lambda: registry.register_review(
            FakeReview(recommendation="EXTEND_PROBATION"),
            approved_weight=0.10,
            source_version="RC24",
            rollback_plan={"x": 1},
        ),
    )


def test_runtime_active_review_is_rejected():
    registry = BookDiagnosticsFinalPromotionRegistry()
    _expect_exception(
        PermissionError,
        lambda: registry.register_review(
            FakeReview(runtime_active=True),
            approved_weight=0.10,
            source_version="RC24",
            rollback_plan={"x": 1},
        ),
    )


def test_final_approval_requires_named_actor_and_keeps_runtime_off():
    registry = _registry_with_record()
    _expect_exception(
        ValueError,
        lambda: registry.approve("CLEAN_DIRECTIONAL_CONTEXT", approved_by=""),
    )
    record = registry.approve(
        "CLEAN_DIRECTIONAL_CONTEXT",
        approved_by="manual-reviewer",
        note="validated",
    )
    assert record.status == "APPROVED_FOR_INTEGRATION"
    assert record.approved_by == "manual-reviewer"
    assert record.runtime_active is False


def test_revoke_keeps_runtime_off():
    registry = _registry_with_record()
    record = registry.revoke("CLEAN_DIRECTIONAL_CONTEXT", note="degradation")
    assert record.status == "REVOKED"
    assert record.runtime_active is False


def test_json_roundtrip_preserves_safe_record():
    registry = _registry_with_record()
    registry.approve("CLEAN_DIRECTIONAL_CONTEXT", approved_by="reviewer")
    with TemporaryDirectory() as temp:
        path = Path(temp) / "final_registry.json"
        registry.save_json(path)
        loaded = BookDiagnosticsFinalPromotionRegistry.load_json(path)
        record = loaded.get("CLEAN_DIRECTIONAL_CONTEXT")
        assert record.status == "APPROVED_FOR_INTEGRATION"
        assert record.runtime_active is False


def test_loader_rejects_runtime_active_payload():
    with TemporaryDirectory() as temp:
        path = Path(temp) / "unsafe.json"
        path.write_text(
            '{"records":[{"book_state":"X","target_layer":"CONTEXT","approved_weight":0.1,"source_version":"RC24","rollback_plan":{"x":1},"status":"APPROVED_FOR_INTEGRATION","approved_by":"r","approval_note":"","created_at":"t","updated_at":"t","runtime_active":true,"history":[]}]}',
            encoding="utf-8",
        )
        _expect_exception(
            ValueError,
            lambda: BookDiagnosticsFinalPromotionRegistry.load_json(path),
        )


if __name__ == "__main__":
    test_register_promote_review_starts_pending_and_inactive()
    test_non_promote_review_is_rejected()
    test_runtime_active_review_is_rejected()
    test_final_approval_requires_named_actor_and_keeps_runtime_off()
    test_revoke_keeps_runtime_off()
    test_json_roundtrip_preserves_safe_record()
    test_loader_rejects_runtime_active_payload()
