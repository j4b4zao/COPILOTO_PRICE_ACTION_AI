from analysis.replay.book_diagnostics_core_integration_contracts import (
    BookDiagnosticsCoreIntegrationContractFactory,
    ChecklistIntegrationContract,
    ContextIntegrationContract,
    EvidenceIntegrationContract,
)


def _event(target):
    return {
        "version": "RC26-CONTROLLED-INTEGRATION-ADAPTER",
        "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
        "target_layer": target,
        "raw_value": 1.0,
        "weight": 0.2,
        "weighted_value": 0.2,
        "metadata": {"session": "OPENING"},
        "controlled_integration": True,
    }


def _expect_error(exc_type, fn):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_builds_evidence_contract():
    contract = BookDiagnosticsCoreIntegrationContractFactory().build(
        _event("EVIDENCE"),
        semantic={"evidence_key": "book.clean_context", "confidence": 0.8},
    )
    assert isinstance(contract, EvidenceIntegrationContract)
    assert contract.weighted_value == 0.2
    assert contract.readonly is True
    assert contract.affects_decision is False


def test_builds_context_contract():
    contract = BookDiagnosticsCoreIntegrationContractFactory().build(
        _event("CONTEXT"),
        semantic={"context_key": "book.market_context", "state": "SUPPORTIVE"},
    )
    assert isinstance(contract, ContextIntegrationContract)
    assert contract.state == "SUPPORTIVE"
    assert contract.affects_decision is False


def test_builds_checklist_contract():
    contract = BookDiagnosticsCoreIntegrationContractFactory().build(
        _event("CHECKLIST"),
        semantic={
            "checklist_key": "book.tight_range",
            "passed": False,
            "severity": "CAUTION",
            "message": "Tight range detected",
        },
    )
    assert isinstance(contract, ChecklistIntegrationContract)
    assert contract.passed is False
    assert contract.severity == "CAUTION"
    assert contract.affects_decision is False


def test_rejects_risk_target():
    _expect_error(
        PermissionError,
        lambda: BookDiagnosticsCoreIntegrationContractFactory().build(_event("RISK")),
    )


def test_requires_controlled_integration_source():
    event = _event("EVIDENCE")
    event["controlled_integration"] = False
    _expect_error(
        PermissionError,
        lambda: BookDiagnosticsCoreIntegrationContractFactory().build(
            event,
            semantic={"evidence_key": "x"},
        ),
    )


def test_validates_evidence_confidence():
    _expect_error(
        ValueError,
        lambda: BookDiagnosticsCoreIntegrationContractFactory().build(
            _event("EVIDENCE"),
            semantic={"evidence_key": "x", "confidence": 1.2},
        ),
    )


def test_validates_checklist_severity():
    _expect_error(
        ValueError,
        lambda: BookDiagnosticsCoreIntegrationContractFactory().build(
            _event("CHECKLIST"),
            semantic={"checklist_key": "x", "severity": "CRITICAL"},
        ),
    )


if __name__ == "__main__":
    test_builds_evidence_contract()
    test_builds_context_contract()
    test_builds_checklist_contract()
    test_rejects_risk_target()
    test_requires_controlled_integration_source()
    test_validates_evidence_confidence()
    test_validates_checklist_severity()
    print("RC27 core integration contracts: OK")
