from analysis.replay.book_diagnostics_voice_status_retention_health import (
    BookDiagnosticsVoiceStatusRetentionHealthReporter,
)


def _inspection(**overrides):
    payload = {
        "version": "RC70-VOICE-STATUS-RETENTION-INSPECTION",
        "directory": "/tmp/voice",
        "prefix": "voice_status",
        "keep": 20,
        "directory_exists": True,
        "existing_files": (),
        "retained_files": (),
        "would_remove_files": (),
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(overrides)
    return payload


def test_rc73_empty_status():
    result = BookDiagnosticsVoiceStatusRetentionHealthReporter().build(_inspection())
    assert result.status == "EMPTY"
    assert result.existing_count == 0
    assert result.would_remove_count == 0


def test_rc73_missing_directory_is_empty():
    result = BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
        _inspection(directory_exists=False)
    )
    assert result.status == "EMPTY"
    assert result.directory_exists is False


def test_rc73_within_limit_status():
    files = ("a.json", "b.json")
    result = BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
        _inspection(existing_files=files, retained_files=files)
    )
    assert result.status == "WITHIN_LIMIT"
    assert result.retained_count == 2


def test_rc73_over_limit_status():
    result = BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
        _inspection(
            keep=2,
            existing_files=("a", "b", "c"),
            retained_files=("a", "b"),
            would_remove_files=("c",),
        )
    )
    assert result.status == "OVER_LIMIT"
    assert result.would_remove_count == 1


def test_rc73_is_readonly_and_does_not_affect_decision():
    result = BookDiagnosticsVoiceStatusRetentionHealthReporter().build(_inspection())
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc73_preserves_directory_prefix_and_keep():
    result = BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
        _inspection(directory="C:/logs/voice", prefix="custom", keep=7)
    )
    assert result.directory == "C:/logs/voice"
    assert result.prefix == "custom"
    assert result.keep == 7


def test_rc73_rejects_wrong_source_version():
    try:
        BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
            _inspection(version="WRONG")
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_rc73_rejects_non_readonly_source():
    try:
        BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
            _inspection(readonly=False)
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_rc73_rejects_invalid_keep():
    try:
        BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
            _inspection(keep=0)
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_rc73_rejects_inconsistent_counts():
    try:
        BookDiagnosticsVoiceStatusRetentionHealthReporter().build(
            _inspection(existing_files=("a", "b"), retained_files=("a",), would_remove_files=())
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
