import pytest

from analysis.replay.book_diagnostics_voice_session import (
    BookDiagnosticsVoiceSessionController,
)


def _command(**changes):
    payload = {
        "version": "RC33-VOICE-OUTPUT-ADAPTER",
        "command": "SPEAK",
        "event_id": "voice-1",
        "text": "Mercado em observacao.",
        "priority": "NORMAL",
        "interrupt": False,
        "voice_profile": "BRITISH_CALM_PRECISE_ASSISTANT",
        "language": "pt-BR",
        "speech_rate": 1.0,
        "estimated_duration_seconds": 2.0,
        "source_version": "RC31-VOICE-EVENT-CONTRACT",
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def test_initial_state_is_idle_and_readonly():
    controller = BookDiagnosticsVoiceSessionController()
    snap = controller.snapshot()
    assert snap.state == "IDLE"
    assert snap.active_event_id is None
    assert snap.readonly is True
    assert snap.affects_decision is False


def test_start_enters_speaking():
    controller = BookDiagnosticsVoiceSessionController()
    snap = controller.start(_command())
    assert snap.state == "SPEAKING"
    assert snap.active_event_id == "voice-1"
    assert snap.active_priority == "NORMAL"


def test_complete_returns_to_idle():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command())
    snap = controller.complete(event_id="voice-1")
    assert snap.state == "IDLE"
    assert snap.last_outcome == "COMPLETED"


def test_fail_moves_to_failed_state():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command())
    snap = controller.fail("tts backend unavailable", event_id="voice-1")
    assert snap.state == "FAILED"
    assert snap.last_outcome == "FAILED"
    assert snap.error == "tts backend unavailable"


def test_reset_recovers_failed_session_to_idle():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command())
    controller.fail("error")
    snap = controller.reset()
    assert snap.state == "IDLE"
    assert snap.error is None


def test_normal_command_cannot_interrupt_active_session():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command(event_id="voice-a"))
    with pytest.raises(RuntimeError):
        controller.start(_command(event_id="voice-b"))


def test_caution_command_cannot_interrupt_active_session():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command(event_id="voice-a"))
    with pytest.raises(RuntimeError):
        controller.start(_command(event_id="voice-b", priority="CAUTION"))


def test_urgent_interrupt_command_replaces_active_session():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command(event_id="voice-a"))
    snap = controller.start(
        _command(event_id="voice-b", priority="URGENT", interrupt=True)
    )
    assert snap.state == "SPEAKING"
    assert snap.active_event_id == "voice-b"
    assert snap.last_outcome == "INTERRUPTED"
    assert snap.interruptible is True


def test_same_event_cannot_interrupt_itself():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command(event_id="voice-a"))
    with pytest.raises(RuntimeError):
        controller.start(
            _command(event_id="voice-a", priority="URGENT", interrupt=True)
        )


def test_rejects_non_rc33_command():
    controller = BookDiagnosticsVoiceSessionController()
    with pytest.raises(PermissionError):
        controller.start(_command(version="RC32-VOICE-QUEUE-POLICY"))


def test_rejects_decision_affecting_command():
    controller = BookDiagnosticsVoiceSessionController()
    with pytest.raises(PermissionError):
        controller.start(_command(affects_decision=True))


def test_rejects_non_readonly_command():
    controller = BookDiagnosticsVoiceSessionController()
    with pytest.raises(PermissionError):
        controller.start(_command(readonly=False))


def test_rejects_interrupt_flag_for_non_urgent_command():
    controller = BookDiagnosticsVoiceSessionController()
    with pytest.raises(ValueError):
        controller.start(_command(priority="NORMAL", interrupt=True))


def test_complete_requires_matching_active_event():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command(event_id="voice-a"))
    with pytest.raises(RuntimeError):
        controller.complete(event_id="voice-b")


def test_fail_requires_nonempty_error():
    controller = BookDiagnosticsVoiceSessionController()
    controller.start(_command())
    with pytest.raises(ValueError):
        controller.fail("   ")
