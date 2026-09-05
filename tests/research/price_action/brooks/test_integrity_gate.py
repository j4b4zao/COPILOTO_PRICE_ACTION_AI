from types import SimpleNamespace

import tools.profit_rtd_brooks_integrity_gate as gate


def test_real_integrity_gate_passes():
    result = gate.run_integrity_gate()
    assert result["status"] == "PASS"
    assert result["failed_check_count"] == 0
    assert result["expected_module_count"] == 18


def test_global_gate_safety_is_fail_closed():
    result = gate.run_integrity_gate()
    assert result["research_only"] is True
    assert result["observational_only"] is True
    for flag in gate.FORBIDDEN_TRUE_FLAGS:
        assert result[flag] is False


def test_result_safety_rejects_operational_influence_dict():
    check = gate._result_safety("x", {"score_influence_allowed": True})
    assert check.passed is False
    assert "score_influence_allowed" in check.detail


def test_result_safety_rejects_operational_influence_object():
    check = gate._result_safety("x", SimpleNamespace(order_execution_allowed=True))
    assert check.passed is False
    assert "order_execution_allowed" in check.detail


def test_result_safety_accepts_absent_or_false_flags():
    assert gate._result_safety("x", {}).passed is True
    assert gate._result_safety("x", SimpleNamespace(score_influence_allowed=False)).passed is True


def test_auditor_contract_accepts_payload_and_sessions():
    module = SimpleNamespace(audit_payload=lambda payload: payload, audit_sessions=lambda payloads: payloads)
    assert gate._auditor_contract("x", module).passed is True


def test_auditor_contract_accepts_path_audit_adapter_family():
    module = SimpleNamespace(audit=lambda paths: paths)
    assert gate._auditor_contract("x", module).passed is True


def test_auditor_contract_rejects_incomplete_module():
    module = SimpleNamespace(audit_payload=lambda payload: payload)
    assert gate._auditor_contract("x", module).passed is False
