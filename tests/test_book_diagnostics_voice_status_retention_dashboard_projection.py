from analysis.replay.book_diagnostics_voice_status_retention_dashboard_projection import (
    BookDiagnosticsVoiceStatusRetentionDashboardProjector,
)


def _health(**overrides):
    payload = {
        "version": "RC73-VOICE-STATUS-RETENTION-HEALTH",
        "status": "WITHIN_LIMIT",
        "summary": "Retention is within the configured limit with 2 snapshot(s).",
        "directory": "/tmp/voice",
        "directory_exists": True,
        "prefix": "voice_status",
        "keep": 20,
        "existing_count": 2,
        "retained_count": 2,
        "would_remove_count": 0,
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(overrides)
    return payload


def test_rc76_projects_empty():
    result = BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(
        _health(status="EMPTY", existing_count=0, retained_count=0, would_remove_count=0)
    )
    assert result.status == "EMPTY"
    assert result.label == "Sem snapshots"


def test_rc76_projects_within_limit():
    result = BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(_health())
    assert result.status == "WITHIN_LIMIT"
    assert result.label == "Retencao dentro do limite"


def test_rc76_projects_over_limit():
    result = BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(
        _health(status="OVER_LIMIT", existing_count=4, retained_count=2, would_remove_count=2)
    )
    assert result.status == "OVER_LIMIT"
    assert result.excess_count == 2


def test_rc76_preserves_context_fields():
    result = BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(_health())
    assert result.directory == "/tmp/voice"
    assert result.prefix == "voice_status"
    assert result.keep == 20


def test_rc76_is_readonly_and_decision_neutral():
    result = BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(_health())
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc76_rejects_wrong_source_version():
    try:
        BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(_health(version="RC72"))
        assert False
    except PermissionError:
        assert True


def test_rc76_rejects_mutable_source():
    try:
        BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(_health(readonly=False))
        assert False
    except PermissionError:
        assert True


def test_rc76_rejects_invalid_status():
    try:
        BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(_health(status="UNKNOWN"))
        assert False
    except ValueError:
        assert True


def test_rc76_rejects_invalid_keep():
    try:
        BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(_health(keep=0))
        assert False
    except ValueError:
        assert True


def test_rc76_rejects_inconsistent_counts():
    try:
        BookDiagnosticsVoiceStatusRetentionDashboardProjector().project(
            _health(existing_count=5, retained_count=2, would_remove_count=1)
        )
        assert False
    except ValueError:
        assert True
