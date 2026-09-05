"""Gate offline de integridade da camada Brooks research-only.

Nao coleta mercado, nao executa estrategia e nao altera Score, Risk, Decision,
Alert ou ordens. Verifica apenas que os componentes esperados continuam
presentes e que seus contratos publicos de isolamento permanecem coerentes.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, asdict


EXPECTED_MODULES = (
    "research.price_action.brooks.breakout_pullback",
    "research.price_action.brooks.trend_pullback",
    "research.price_action.brooks.failed_breakout",
    "research.price_action.brooks.major_trend_reversal",
    "research.price_action.brooks.wedge_three_pushes",
    "research.price_action.brooks.trading_range_reversal",
    "research.price_action.brooks.stop_target_rules",
    "research.price_action.brooks.registry",
    "tools.profit_rtd_brooks_breakout_pullback_audit",
    "tools.profit_rtd_brooks_trend_pullback_audit",
    "tools.profit_rtd_brooks_failed_breakout_audit",
    "tools.profit_rtd_brooks_major_trend_reversal_audit",
    "tools.profit_rtd_brooks_wedge_three_pushes_audit",
    "tools.profit_rtd_brooks_trading_range_reversal_audit",
    "tools.profit_rtd_brooks_research_evidence_suite",
    "tools.profit_rtd_brooks_selection_manifest",
    "tools.profit_rtd_brooks_selection_runner",
    "tools.profit_rtd_brooks_selection_launcher",
)

AUDITOR_MODULES = (
    "tools.profit_rtd_brooks_breakout_pullback_audit",
    "tools.profit_rtd_brooks_trend_pullback_audit",
    "tools.profit_rtd_brooks_failed_breakout_audit",
    "tools.profit_rtd_brooks_major_trend_reversal_audit",
    "tools.profit_rtd_brooks_wedge_three_pushes_audit",
    "tools.profit_rtd_brooks_trading_range_reversal_audit",
)

FORBIDDEN_TRUE_FLAGS = (
    "predictive_claim_allowed",
    "score_influence_allowed",
    "risk_influence_allowed",
    "decision_influence_allowed",
    "alert_influence_allowed",
    "order_execution_allowed",
    "promotion_allowed",
    "hypothesis_freeze_allowed",
)


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool
    detail: str = ""


def _import_check(module_name):
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - exercised through tests with monkeypatch
        return None, GateCheck(module_name, False, f"IMPORT_ERROR:{type(exc).__name__}:{exc}")
    return module, GateCheck(module_name, True, "IMPORT_OK")


def _auditor_contract(module_name, module):
    has_single = callable(getattr(module, "audit_payload", None)) or callable(getattr(module, "audit", None))
    has_multi = callable(getattr(module, "audit_sessions", None)) or callable(getattr(module, "audit", None))
    return GateCheck(
        f"{module_name}:AUDITOR_CONTRACT",
        bool(has_single and has_multi),
        f"single={has_single};multi={has_multi}",
    )


def _result_safety(name, result):
    failures = []
    if isinstance(result, dict):
        for flag in FORBIDDEN_TRUE_FLAGS:
            if result.get(flag) is True:
                failures.append(flag)
    else:
        for flag in FORBIDDEN_TRUE_FLAGS:
            if getattr(result, flag, False) is True:
                failures.append(flag)
    return GateCheck(
        f"{name}:SAFETY",
        not failures,
        "SAFE" if not failures else "FORBIDDEN_TRUE:" + ",".join(failures),
    )


def _registry_entries(registry_module):
    registry_type = getattr(registry_module, "BrooksResearchRegistry", None)
    if registry_type is None:
        return None
    entries_method = getattr(registry_type, "entries", None)
    if not callable(entries_method):
        return None
    try:
        entries = entries_method()
    except Exception:
        return None
    if not isinstance(entries, tuple):
        return None
    return entries


def run_integrity_gate():
    checks = []
    modules = {}
    for module_name in EXPECTED_MODULES:
        module, check = _import_check(module_name)
        checks.append(check)
        if module is not None:
            modules[module_name] = module

    for module_name in AUDITOR_MODULES:
        module = modules.get(module_name)
        if module is not None:
            checks.append(_auditor_contract(module_name, module))

    registry_module = modules.get("research.price_action.brooks.registry")
    if registry_module is not None:
        entries = _registry_entries(registry_module)
        expected_count = 7
        actual_count = len(entries) if entries is not None else "INVALID"
        checks.append(GateCheck(
            "BROOKS_RESEARCH_REGISTRY:COUNT",
            entries is not None and len(entries) == expected_count,
            f"expected={expected_count};actual={actual_count}",
        ))
        if entries is not None:
            for entry in entries:
                entry_name = getattr(entry, "name", "UNKNOWN")
                checks.append(_result_safety(f"REGISTRY:{entry_name}", entry))

    passed = all(check.passed for check in checks)
    return {
        "gate": "BROOKS_RESEARCH_INTEGRITY_GATE_V1",
        "status": "PASS" if passed else "FAIL",
        "expected_module_count": len(EXPECTED_MODULES),
        "check_count": len(checks),
        "failed_check_count": sum(not check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
        "hypothesis_freeze_allowed": False,
    }


def main():
    import json
    result = run_integrity_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
