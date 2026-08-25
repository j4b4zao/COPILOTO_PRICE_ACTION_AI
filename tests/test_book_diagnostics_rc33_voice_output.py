import pytest

from analysis.replay.book_diagnostics_voice_event import BookDiagnosticsVoiceEventFactory
from analysis.replay.book_diagnostics_voice_output import (
    BookDiagnosticsVoiceOutputAdapter,
    NullVoiceOutputSink,
)


def _approved(priority="NORMAL", text="Mercado em observacao."):
    return {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "approved": True,
        "text": text,
        "priority": priority,
        "readonly": True,
        "affects_decision": False,
    }


def _event(priority="NORMAL", text="Mercado em observacao."):
    return BookDiagnosticsVoiceEventFactory().build(_approved(priority, text))


class RecordingSink:
    def __init__(self):
        self.commands = []

    def submit(self, command):
        self.commands.append(command)


def test_prepare_creates_structured_speak_command():
    command = BookDiagnosticsVoiceOutputAdapter().prepare(_event())
    assert command.version == "RC33-VOICE-OUTPUT-ADAPTER"
    assert command.command == "SPEAK"
    assert command.readonly is True
    assert command.affects_decision is False


def test_normal_event_does_not_interrupt():
    command = BookDiagnosticsVoiceOutputAdapter().prepare(_event("NORMAL"))
    assert command.interrupt is False


def test_caution_event_does_not_interrupt():
    command = BookDiagnosticsVoiceOutputAdapter().prepare(_event("CAUTION"))
    assert command.interrupt is False


def test_urgent_event_can_interrupt():
    command = BookDiagnosticsVoiceOutputAdapter().prepare(_event("URGENT"))
    assert command.interrupt is True


def test_dispatch_sends_command_to_sink():
    sink = RecordingSink()
    adapter = BookDiagnosticsVoiceOutputAdapter(sink=sink)
    command = adapter.dispatch(_event())
    assert sink.commands == [command]


def test_default_sink_is_safe_noop():
    adapter = BookDiagnosticsVoiceOutputAdapter()
    assert isinstance(adapter.sink, NullVoiceOutputSink)
    command = adapter.dispatch(_event())
    assert command.command == "SPEAK"


def test_rejects_wrong_source_version():
    payload = _event().to_dict()
    payload["version"] = "OTHER"
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceOutputAdapter().prepare(payload)


def test_rejects_non_readonly_event():
    payload = _event().to_dict()
    payload["readonly"] = False
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceOutputAdapter().prepare(payload)


def test_rejects_decision_affecting_event():
    payload = _event().to_dict()
    payload["affects_decision"] = True
    with pytest.raises(PermissionError):
        BookDiagnosticsVoiceOutputAdapter().prepare(payload)


def test_rejects_empty_text():
    payload = _event().to_dict()
    payload["text"] = "   "
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceOutputAdapter().prepare(payload)


def test_rejects_invalid_priority():
    payload = _event().to_dict()
    payload["priority"] = "CRITICAL"
    with pytest.raises(ValueError):
        BookDiagnosticsVoiceOutputAdapter().prepare(payload)


def test_preserves_voice_profile_and_language():
    event = _event()
    command = BookDiagnosticsVoiceOutputAdapter().prepare(event)
    assert command.voice_profile == event.voice_profile
    assert command.language == "pt-BR"
    assert command.speech_rate == event.speech_rate


def test_dispatch_next_consumes_queue_priority_order():
    from analysis.replay.book_diagnostics_voice_queue import BookDiagnosticsVoiceQueue

    queue = BookDiagnosticsVoiceQueue()
    queue.enqueue(_event("NORMAL", "Normal"))
    queue.enqueue(_event("URGENT", "Urgente"))

    sink = RecordingSink()
    adapter = BookDiagnosticsVoiceOutputAdapter(sink=sink)
    command = adapter.dispatch_next(queue)

    assert command.priority == "URGENT"
    assert command.text == "Urgente"
    assert len(sink.commands) == 1


def test_dispatch_next_empty_queue_returns_none():
    from analysis.replay.book_diagnostics_voice_queue import BookDiagnosticsVoiceQueue

    queue = BookDiagnosticsVoiceQueue()
    assert BookDiagnosticsVoiceOutputAdapter().dispatch_next(queue) is None
