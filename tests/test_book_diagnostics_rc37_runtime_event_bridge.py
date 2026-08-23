import pytest

from analysis.replay.book_diagnostics_runtime_event_bridge import (
    BookDiagnosticsRuntimeEventBridge,
)


def _decision(**changes):
    payload = {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "should_emit": True,
        "priority": "NORMAL",
        "reason": "MESSAGE_APPROVED",
        "message": "Leitura do mercado: contexto estavel.",
        "fingerprint": "abc123",
        "cooldown_seconds": 180,
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def test_bridge_accepts_real_rc30_contract():
    bridge = BookDiagnosticsRuntimeEventBridge()
    result = bridge.submit(_decision())
    assert result.accepted is True
    assert result.emitted is True
    assert result.event_id.startswith("voice-")
    assert result.queue_size == 1
    assert result.readonly is True
    assert result.affects_decision is False


def test_bridge_maps_message_to_rc31_text_and_processes():
    bridge = BookDiagnosticsRuntimeEventBridge()
    decision, tts = bridge.submit_and_process(_decision())
    assert decision.accepted is True
    assert tts.accepted is True
    assert tts.completed is True
    assert bridge.snapshot().last_status == "COMPLETED"


def test_suppressed_rc30_message_is_not_enqueued():
    bridge = BookDiagnosticsRuntimeEventBridge()
    result = bridge.submit(_decision(should_emit=False, reason="DUPLICATE_WITHIN_COOLDOWN"))
    assert result.accepted is False
    assert result.emitted is False
    assert result.event_id is None
    assert result.queue_size == 0


def test_urgent_priority_is_preserved():
    bridge = BookDiagnosticsRuntimeEventBridge()
    result = bridge.submit(_decision(priority="URGENT", message="Atenção: risco elevado."))
    assert result.priority == "URGENT"
    assert bridge.runtime.queue.peek_next()["priority"] == "URGENT"
    assert bridge.runtime.queue.peek_next()["interrupt_allowed"] is True


def test_caution_priority_is_preserved():
    bridge = BookDiagnosticsRuntimeEventBridge()
    result = bridge.submit(_decision(priority="CAUTION"))
    assert result.priority == "CAUTION"
    assert bridge.runtime.queue.peek_next()["priority"] == "CAUTION"


def test_duplicate_voice_event_is_rejected_by_queue():
    bridge = BookDiagnosticsRuntimeEventBridge()
    first = bridge.submit(_decision())
    second = bridge.submit(_decision())
    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "duplicate_event"


def test_wrong_version_is_rejected():
    with pytest.raises(PermissionError):
        BookDiagnosticsRuntimeEventBridge().submit(_decision(version="RC29"))


def test_non_readonly_input_is_rejected():
    with pytest.raises(PermissionError):
        BookDiagnosticsRuntimeEventBridge().submit(_decision(readonly=False))


def test_decision_affecting_input_is_rejected():
    with pytest.raises(PermissionError):
        BookDiagnosticsRuntimeEventBridge().submit(_decision(affects_decision=True))


def test_invalid_priority_is_rejected():
    with pytest.raises(ValueError):
        BookDiagnosticsRuntimeEventBridge().submit(_decision(priority="CRITICAL"))


def test_empty_approved_message_is_rejected():
    with pytest.raises(ValueError):
        BookDiagnosticsRuntimeEventBridge().submit(_decision(message="   "))


def test_snapshot_remains_readonly_and_operationally_isolated():
    bridge = BookDiagnosticsRuntimeEventBridge()
    bridge.submit(_decision())
    snap = bridge.snapshot()
    assert snap.readonly is True
    assert snap.affects_decision is False
