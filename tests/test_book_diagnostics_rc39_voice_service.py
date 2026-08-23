import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _message(**changes):
    payload = {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "should_emit": True,
        "priority": "NORMAL",
        "reason": "MESSAGE_APPROVED",
        "message": "Leitura do mercado pronta para observacao.",
        "fingerprint": "abc123",
        "cooldown_seconds": 180,
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def test_service_is_disabled_by_default():
    service = BookDiagnosticsVoiceService()
    snap = service.snapshot()
    assert snap.version == "RC39-VOICE-SERVICE-INTEGRATION"
    assert snap.enabled is False
    assert snap.available is False
    assert snap.backend == "DISABLED"
    assert snap.session_state == "IDLE"
    assert snap.readonly is True
    assert snap.affects_decision is False


def test_disabled_service_rejects_submit():
    service = BookDiagnosticsVoiceService()
    with pytest.raises(RuntimeError):
        service.submit_message(_message())


def test_enable_lazily_creates_facade():
    service = BookDiagnosticsVoiceService()
    snap = service.enable()
    assert snap.enabled is True
    assert snap.available is True
    assert snap.backend == "NULL_TTS"
    assert snap.backend_healthy is True


def test_enabled_service_accepts_rc30_message():
    service = BookDiagnosticsVoiceService(enabled=True)
    decision = service.submit_message(_message())
    assert decision.accepted is True
    assert decision.emitted is True
    assert service.snapshot().queue_size == 1


def test_submit_and_process_uses_null_tts_safely():
    service = BookDiagnosticsVoiceService(enabled=True)
    decision, result = service.submit_and_process(_message())
    assert decision.accepted is True
    assert result.accepted is True
    assert result.completed is True
    snap = service.snapshot()
    assert snap.queue_size == 0
    assert snap.session_state == "IDLE"
    assert snap.last_status == "COMPLETED"


def test_suppressed_message_does_not_enter_queue():
    service = BookDiagnosticsVoiceService(enabled=True)
    decision = service.submit_message(
        _message(should_emit=False, reason="DUPLICATE_WITHIN_COOLDOWN")
    )
    assert decision.accepted is False
    assert decision.emitted is False
    assert service.snapshot().queue_size == 0


def test_disable_resets_and_blocks_future_use():
    service = BookDiagnosticsVoiceService(enabled=True)
    service.submit_message(_message())
    snap = service.disable()
    assert snap.enabled is False
    assert snap.available is True
    assert snap.queue_size == 0
    with pytest.raises(RuntimeError):
        service.process_next()


def test_reenable_preserves_safe_facade():
    service = BookDiagnosticsVoiceService(enabled=True)
    service.disable()
    snap = service.enable()
    assert snap.enabled is True
    assert snap.backend == "NULL_TTS"
    assert snap.session_state == "IDLE"


def test_reset_is_safe_when_disabled_and_unavailable():
    service = BookDiagnosticsVoiceService()
    snap = service.reset()
    assert snap.enabled is False
    assert snap.available is False


def test_wrong_rc30_version_is_rejected_when_enabled():
    service = BookDiagnosticsVoiceService(enabled=True)
    with pytest.raises(PermissionError):
        service.submit_message(_message(version="RC29"))


def test_decision_affecting_input_is_rejected():
    service = BookDiagnosticsVoiceService(enabled=True)
    with pytest.raises(PermissionError):
        service.submit_message(_message(affects_decision=True))


def test_non_readonly_input_is_rejected():
    service = BookDiagnosticsVoiceService(enabled=True)
    with pytest.raises(PermissionError):
        service.submit_message(_message(readonly=False))


def test_service_snapshot_never_affects_decision():
    service = BookDiagnosticsVoiceService(enabled=True)
    snap = service.snapshot()
    assert snap.readonly is True
    assert snap.affects_decision is False
