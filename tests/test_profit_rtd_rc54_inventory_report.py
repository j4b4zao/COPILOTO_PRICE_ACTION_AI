from __future__ import annotations

import json

import tools.profit_rtd_rc54_inventory_report as inventory


def test_discover_sessions_returns_sorted_matching_files(tmp_path):
    (tmp_path / "profit_rtd_rc54_3_2_b.json").write_text("{}", encoding="utf-8")
    (tmp_path / "profit_rtd_rc54_3_2_a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ignore.json").write_text("{}", encoding="utf-8")
    found = inventory.discover_sessions(tmp_path)
    assert [path.name for path in found] == [
        "profit_rtd_rc54_3_2_a.json",
        "profit_rtd_rc54_3_2_b.json",
    ]


def test_missing_directory_returns_no_sessions(tmp_path):
    report = inventory.build_report(tmp_path / "missing")
    assert report["status"] == "NO_SESSIONS_DISCOVERED"
    assert report["discovered_sessions"] == 0
    assert report["freeze_allowed"] is False
    assert report["oos_allowed"] is False


def test_clean_inventory_reports_all_accepted(tmp_path, monkeypatch):
    path = tmp_path / "profit_rtd_rc54_3_2_a.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(inventory, "recompose", lambda paths, inventory_mode: {
        "inventory_summary": {
            "discovered_sessions": 1,
            "accepted_selection_sessions": 1,
            "rejected_sessions": 0,
            "rejection_reasons": {},
        },
        "manifest": [{"path": str(path), "eligible": True, "reasons": []}],
        "accepted_selection_paths": [str(path)],
        "verdict": "ROBUSTNESS_PENDING",
        "manifest_valid": True,
    })
    report = inventory.build_report(tmp_path)
    assert report["status"] == "CLEAN"
    assert report["accepted_selection_sessions"] == 1
    assert report["quarantined_sessions"] == []


def test_inventory_exposes_temporal_overlap_quarantine(tmp_path, monkeypatch):
    path = tmp_path / "profit_rtd_rc54_3_2_overlap.json"
    path.write_text("{}", encoding="utf-8")
    rejected = {
        "path": str(path),
        "eligible": False,
        "reasons": ["TEMPORAL_OVERLAP"],
        "overlaps_with": "accepted.json",
    }
    monkeypatch.setattr(inventory, "recompose", lambda paths, inventory_mode: {
        "inventory_summary": {
            "discovered_sessions": 1,
            "accepted_selection_sessions": 0,
            "rejected_sessions": 1,
            "rejection_reasons": {"TEMPORAL_OVERLAP": 1},
        },
        "manifest": [rejected],
        "accepted_selection_paths": [],
        "verdict": "INVENTORY_RECOMPOSED_WITH_EXCLUSIONS",
        "manifest_valid": False,
    })
    report = inventory.build_report(tmp_path)
    assert report["status"] == "CLEAN_WITH_QUARANTINE"
    assert report["rejection_reasons"] == {"TEMPORAL_OVERLAP": 1}
    assert report["quarantined_sessions"][0]["overlaps_with"] == "accepted.json"


def test_inventory_preserves_recomposer_rejection_reasons(tmp_path, monkeypatch):
    path = tmp_path / "profit_rtd_rc54_3_2_bad.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(inventory, "recompose", lambda paths, inventory_mode: {
        "inventory_summary": {
            "discovered_sessions": 1,
            "accepted_selection_sessions": 0,
            "rejected_sessions": 1,
            "rejection_reasons": {"DATA_READY_NOT_TRUE": 1},
        },
        "manifest": [{"path": str(path), "eligible": False, "reasons": ["DATA_READY_NOT_TRUE"]}],
        "accepted_selection_paths": [],
        "verdict": "INVENTORY_RECOMPOSED_WITH_EXCLUSIONS",
        "manifest_valid": False,
    })
    report = inventory.build_report(tmp_path)
    assert report["rejection_reasons"] == {"DATA_READY_NOT_TRUE": 1}


def test_inventory_is_never_freeze_or_oos_authority(tmp_path, monkeypatch):
    path = tmp_path / "profit_rtd_rc54_3_2_a.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(inventory, "recompose", lambda paths, inventory_mode: {
        "inventory_summary": {
            "discovered_sessions": 1,
            "accepted_selection_sessions": 1,
            "rejected_sessions": 0,
            "rejection_reasons": {},
        },
        "manifest": [{"path": str(path), "eligible": True, "reasons": []}],
        "accepted_selection_paths": [str(path)],
        "verdict": "SELECTION_ROBUSTNESS_CONFIRMED",
        "manifest_valid": True,
    })
    report = inventory.build_report(tmp_path)
    assert report["freeze_allowed"] is False
    assert report["oos_allowed"] is False
    assert report["predictive_claim_allowed"] is False


def test_operational_influence_flags_are_false(tmp_path):
    report = inventory.build_report(tmp_path / "missing")
    for key in (
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
    ):
        assert report[key] is False


def test_main_writes_json_report(tmp_path, monkeypatch):
    output = tmp_path / "inventory.json"
    monkeypatch.setattr(inventory, "build_report", lambda directory, pattern=inventory.DEFAULT_PATTERN: {
        "report": inventory.VERSION,
        "status": "NO_SESSIONS_DISCOVERED",
    })
    assert inventory.main([str(tmp_path), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["report"] == inventory.VERSION
