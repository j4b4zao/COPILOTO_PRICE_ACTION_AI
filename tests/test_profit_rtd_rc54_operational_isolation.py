import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RC54_TOOLS = sorted((ROOT / "tools").glob("profit_rtd_rc54_*.py"))
READINESS_CONSUMERS = {
    "profit_rtd_rc54_3_3_readiness_drop_auditor.py",
    "profit_rtd_rc54_4_context_qualified_order_flow_auditor.py",
    "profit_rtd_rc54_5_multi_session_evidence_accumulator.py",
    "profit_rtd_rc54_7_session_consistency_robustness_auditor.py",
    "profit_rtd_rc54_8_oos_candidate_validator.py",
    "profit_rtd_rc54_offline_recomposer.py",
}
DATA_READY_GUARDS = {
    "profit_rtd_rc54_4_context_qualified_order_flow_auditor.py": "RC54_4_REQUIRES_DATA_READY_SESSION",
    "profit_rtd_rc54_5_multi_session_evidence_accumulator.py": "RC54_5_REQUIRES_DATA_READY_SESSION",
    "profit_rtd_rc54_5_5_session_readiness_report.py": "DATA_READY_NOT_TRUE",
    "profit_rtd_rc54_7_session_consistency_robustness_auditor.py": "RC54_7_REQUIRES_DATA_READY_SESSION",
    "profit_rtd_rc54_8_oos_candidate_validator.py": "RC54_8_REQUIRES_DATA_READY_SESSION",
    "profit_rtd_rc54_offline_recomposer.py": "DATA_READY_NOT_TRUE",
}

BLOCKED_MODULE_PARTS = {
    "score_engine",
    "risk_manager",
    "decision_engine",
    "execution_engine",
    "order_executor",
    "broker",
}
BLOCKED_SYMBOLS = {
    "ScoreEngine",
    "RiskManager",
    "DecisionEngine",
    "ExecutionEngine",
    "OrderExecutor",
    "execute_order",
    "send_order",
    "place_order",
    "submit_order",
}


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _get_key(node):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "get" or not node.args:
        return None
    key = node.args[0]
    return key.value if isinstance(key, ast.Constant) and isinstance(key.value, str) else None


def test_rc54_tools_are_isolated_from_operational_engines():
    assert RC54_TOOLS, "No RC54 tools found"
    violations = []

    for path in RC54_TOOLS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = set(alias.name.lower().split("."))
                    if parts & BLOCKED_MODULE_PARTS:
                        violations.append(f"{path.name}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").lower()
                parts = set(module.split("."))
                imported = {alias.name for alias in node.names}
                if parts & BLOCKED_MODULE_PARTS or imported & BLOCKED_SYMBOLS:
                    names = ", ".join(sorted(imported))
                    violations.append(f"{path.name}:{node.lineno} from {module} import {names}")
            elif isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name in BLOCKED_SYMBOLS:
                    violations.append(f"{path.name}:{node.lineno} call {name}")

    assert not violations, "RC54 operational isolation violated:\n" + "\n".join(violations)


def test_rc54_tools_declare_risk_isolation():
    missing = [
        path.name
        for path in RC54_TOOLS
        if "risk_influence_allowed" not in path.read_text(encoding="utf-8")
    ]
    assert not missing, "RC54 tools missing explicit risk isolation: " + ", ".join(missing)


def test_trade_context_readiness_has_canonical_precedence():
    violations = []
    for path in RC54_TOOLS:
        if path.name not in READINESS_CONSUMERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if _get_key(node) != "context_ready":
                continue
            parent = parents.get(node)
            if _get_key(parent) != "trade_context_ready":
                violations.append(f"{path.name}:{node.lineno} reads legacy context_ready directly")
    assert not violations, "Canonical trade readiness precedence violated:\n" + "\n".join(violations)


def test_evidence_consumers_declare_explicit_data_ready_guards():
    sources = {path.name: path.read_text(encoding="utf-8") for path in RC54_TOOLS}
    missing = [
        f"{name}:{guard}"
        for name, guard in DATA_READY_GUARDS.items()
        if guard not in sources.get(name, "")
    ]
    assert not missing, "RC54 explicit data readiness guards missing: " + ", ".join(missing)


def run():
    test_rc54_tools_are_isolated_from_operational_engines()
    test_rc54_tools_declare_risk_isolation()
    test_trade_context_readiness_has_canonical_precedence()
    test_evidence_consumers_declare_explicit_data_ready_guards()
    print("PROFIT_RTD_RC54_OPERATIONAL_ISOLATION=OK")


if __name__ == "__main__":
    run()
