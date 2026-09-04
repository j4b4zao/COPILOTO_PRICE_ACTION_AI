import json

from tools.profit_rtd_price_action_evidence_audit import audit


def _row(price, *, inside=False, trend="SIDEWAYS"):
    return {
        "last_price": price,
        "structure": {"trend": trend},
        "price_action": {
            "trend": trend,
            "inside_bar": inside,
            "brooks_signal_context": "WITH_TREND",
        },
    }


def test_audit_counts_only_false_to_true_edges_and_separates_horizons(tmp_path):
    path = tmp_path / "session.json"
    rows = [_row(100), _row(101, inside=True), _row(102, inside=True)]
    rows += [_row(103), _row(104, inside=True)]
    rows += [_row(105), _row(106), _row(107), _row(108), _row(109), _row(110)]
    path.write_text(json.dumps({"data_ready": True, "samples": rows}), encoding="utf-8")
    result = audit([path], minimum_sample=1, minimum_sessions=1)
    assert result["edge_occurrences"] == 2
    assert result["evidence_rows"] == 6
    assert {bucket["key"].rsplit("|", 1)[-1] for bucket in result["buckets"]} == {"H1", "H3", "H5"}
    assert result["volume_status"] == "NOT_CAPTURED_IN_RC54_SESSION_SCHEMA"
    assert all(bucket["sessions"] == 1 for bucket in result["buckets"])


def test_audit_rejects_session_without_data_ready(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"data_ready": False, "samples": [_row(100)]}), encoding="utf-8")
    result = audit([path])
    assert result["accepted_sessions"] == []
    assert result["rejected_sessions"] == ["bad.json"]
    assert result["status"] == "MORE_EVIDENCE_REQUIRED"
    assert result["score_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
