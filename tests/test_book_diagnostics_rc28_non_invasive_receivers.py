from analysis.replay.book_diagnostics_core_integration_contracts import (
    BookDiagnosticsCoreIntegrationContractFactory,
)
from analysis.replay.book_diagnostics_non_invasive_receivers import (
    BookDiagnosticsNonInvasiveCoreReceivers,
)


def _contribution(target):
    return {
        "version": "RC26-CONTROLLED-INTEGRATION-ADAPTER",
        "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
        "target_layer": target,
        "weighted_value": 0.2,
        "metadata": {},
        "controlled_integration": True,
    }


def _expect_error(func, exc_type):
    try:
        func()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_receives_evidence_contract():
    factory = BookDiagnosticsCoreIntegrationContractFactory()
    contract = factory.build(
        _contribution("EVIDENCE"),
        semantic={"evidence_key": "book.clean_context", "confidence": 0.8},
    )
    receiver = BookDiagnosticsNonInvasiveCoreReceivers()
    receiver.receive(contract)
    snapshot = receiver.snapshot()
    assert "book.clean_context" in snapshot["evidence"]
    assert snapshot["affects_decision"] is False


def test_receives_context_contract():
    factory = BookDiagnosticsCoreIntegrationContractFactory()
    contract = factory.build(
        _contribution("CONTEXT"),
        semantic={"context_key": "book.market_context", "state": "CLEAN"},
    )
    receiver = BookDiagnosticsNonInvasiveCoreReceivers()
    receiver.receive(contract)
    assert receiver.snapshot()["context"]["book.market_context"]["state"] == "CLEAN"


def test_receives_checklist_and_exposes_dashboard_counts():
    factory = BookDiagnosticsCoreIntegrationContractFactory()
    contract = factory.build(
        _contribution("CHECKLIST"),
        semantic={
            "checklist_key": "book.range_warning",
            "passed": False,
            "severity": "CAUTION",
            "message": "tight range",
        },
    )
    receiver = BookDiagnosticsNonInvasiveCoreReceivers()
    receiver.receive(contract)
    view = receiver.dashboard_view()
    assert view["checklist_count"] == 1
    assert view["checklist_cautions"] == 1
    assert view["affects_decision"] is False


def test_rejects_decision_affecting_payload():
    receiver = BookDiagnosticsNonInvasiveCoreReceivers()
    payload = {
        "version": "RC27-CORE-INTEGRATION-CONTRACTS",
        "book_state": "STATE",
        "evidence_key": "x",
        "readonly": True,
        "affects_decision": True,
    }
    _expect_error(lambda: receiver.receive(payload), PermissionError)


def test_rejects_non_readonly_payload():
    receiver = BookDiagnosticsNonInvasiveCoreReceivers()
    payload = {
        "version": "RC27-CORE-INTEGRATION-CONTRACTS",
        "book_state": "STATE",
        "context_key": "x",
        "readonly": False,
        "affects_decision": False,
    }
    _expect_error(lambda: receiver.receive(payload), PermissionError)


def test_rejects_risk_target():
    receiver = BookDiagnosticsNonInvasiveCoreReceivers()
    _expect_error(lambda: receiver.receive({"target_layer": "RISK"}), PermissionError)


def test_clear_removes_read_models_only():
    factory = BookDiagnosticsCoreIntegrationContractFactory()
    contract = factory.build(
        _contribution("EVIDENCE"),
        semantic={"evidence_key": "book.test", "confidence": 1.0},
    )
    receiver = BookDiagnosticsNonInvasiveCoreReceivers()
    receiver.receive(contract)
    receiver.clear()
    snapshot = receiver.snapshot()
    assert snapshot["evidence"] == {}
    assert snapshot["context"] == {}
    assert snapshot["checklist"] == {}


if __name__ == "__main__":
    test_receives_evidence_contract()
    test_receives_context_contract()
    test_receives_checklist_and_exposes_dashboard_counts()
    test_rejects_decision_affecting_payload()
    test_rejects_non_readonly_payload()
    test_rejects_risk_target()
    test_clear_removes_read_models_only()
    print("RC28 non-invasive receiver tests: OK")
