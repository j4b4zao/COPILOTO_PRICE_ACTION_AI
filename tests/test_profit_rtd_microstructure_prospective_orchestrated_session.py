from contextlib import nullcontext
import json

import tools.profit_rtd_microstructure_prospective_orchestrated_session as runner


def _patch(monkeypatch, *, active=True, session=None):
    monkeypatch.setattr(runner, "_runner_lock", lambda *a, **k: nullcontext())
    monkeypatch.setattr(runner, "_call_with_output", lambda function, **kwargs: function(**{
        key: value for key, value in kwargs.items()
        if key not in {"concise_output", "progress_every"}
    }))
    monkeypatch.setattr(runner, "check_market_activity", lambda **kwargs: {
        "status": "MARKET_ACTIVITY_READY" if active else "MARKET_ACTIVITY_NOT_READY",
        "active": active, "reasons": [] if active else ["NO_NEW_M1_CANDLE_PROGRESS"],
    })
    monkeypatch.setattr(runner, "run_session", lambda *a, **k: session or {
        "status": "COMPLETED", "data_ready": True,
    })


def test_completes_only_after_ready_preflight(monkeypatch):
    _patch(monkeypatch)
    result = runner.run_orchestrated_prospective_session("winv26")
    assert result["status"] == "SESSION_COMPLETED"
    assert result["symbol"] == "WINV26"
    assert result["warmup_started"] is True
    assert result["score_influence_allowed"] is False


def test_market_not_ready_never_starts_warmup(monkeypatch):
    _patch(monkeypatch, active=False)
    monkeypatch.setattr(runner, "run_session", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    result = runner.run_orchestrated_prospective_session("WINV26")
    assert result["status"] == "ABORTED_MARKET_ACTIVITY_NOT_READY"
    assert result["warmup_started"] is False
    assert result["session"] is None


def test_context_abort_is_not_session_completed(monkeypatch):
    _patch(monkeypatch, session={"status": "ABORTED_CONTEXT_NOT_READY", "data_ready": False})
    result = runner.run_orchestrated_prospective_session("WINV26")
    assert result["status"] == "SESSION_ABORTED_AFTER_PREFLIGHT"
    assert result["session"]["status"] == "ABORTED_CONTEXT_NOT_READY"


def test_runner_collision_is_fail_closed(monkeypatch):
    def collision(*args, **kwargs):
        raise runner.RunnerAlreadyActiveError("busy")
    monkeypatch.setattr(runner, "_runner_lock", collision)
    result = runner.run_orchestrated_prospective_session("WINV26")
    assert result["status"] == "ABORTED_RUNNER_ALREADY_ACTIVE"
    assert result["session"] is None
    assert result["order_execution_allowed"] is False


def test_cli_prints_summary_without_raw_samples(monkeypatch, capsys):
    monkeypatch.setattr(runner, "run_orchestrated_prospective_session", lambda *a, **k: {
        "status": "SESSION_COMPLETED", "symbol": "WINV26",
        "preflight": {"active": True}, "warmup_started": True,
        "session": {
            "status": "COMPLETED", "data_ready": True,
            "analyzable_samples": 1, "samples": [{"secret_marker": "RAW_SAMPLE"}],
            "prospective_microstructure": {
                "captured_samples": 1, "sample_count_matches_source": True,
                "samples": [{"secret_marker": "RAW_SAMPLE"}],
                "report": {"samples": 1},
            },
        },
    })
    assert runner.main(["WINV26"]) == 0
    output = capsys.readouterr().out
    assert "RAW_SAMPLE" not in output
    assert json.loads(output)["captured_samples"] == 1
