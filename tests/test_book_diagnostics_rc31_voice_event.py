from analysis.replay.book_diagnostics_voice_event import BookDiagnosticsVoiceEventFactory
from analysis.replay.book_diagnostics_voice_profile_resolver import ResolvedVoiceProfile


def _profile(words_per_minute=145):
    return ResolvedVoiceProfile(
        version="RC42-VOICE-PROFILE-RESOLVER",
        language="pt-BR",
        voice_profile="BRITISH_CALM_PRECISE_ASSISTANT",
        speech_rate=words_per_minute / 145,
        words_per_minute=words_per_minute,
        allow_urgent_interrupt=True,
    )


def _message(priority="NORMAL", text="Leitura do mercado. Contexto estavel para observacao.", **changes):
    payload = {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "approved": True,
        "text": text,
        "priority": priority,
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def _raises(error_type, fn):
    try:
        fn()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


def test_normal_message_builds_non_interrupting_event():
    event = BookDiagnosticsVoiceEventFactory().build(_message())
    assert event.priority == "NORMAL"
    assert event.interrupt_allowed is False
    assert event.voice_profile == "BRITISH_CALM_PRECISE_ASSISTANT"
    assert event.language == "pt-BR"
    assert event.readonly is True
    assert event.affects_decision is False


def test_urgent_message_can_interrupt():
    event = BookDiagnosticsVoiceEventFactory().build(_message("URGENT", "Atencao. Risco contextual elevado."))
    assert event.interrupt_allowed is True


def test_event_id_is_deterministic_for_same_message():
    factory = BookDiagnosticsVoiceEventFactory()
    first = factory.build(_message())
    second = factory.build(_message())
    assert first.event_id == second.event_id


def test_different_text_changes_event_id():
    factory = BookDiagnosticsVoiceEventFactory()
    first = factory.build(_message(text="Mensagem um."))
    second = factory.build(_message(text="Mensagem dois."))
    assert first.event_id != second.event_id


def test_duration_is_positive_and_rate_configurable():
    event = BookDiagnosticsVoiceEventFactory(profile=_profile(120)).build(
        _message(text="Esta e uma mensagem um pouco mais longa para estimar a duracao da fala.")
    )
    assert event.estimated_duration_seconds > 1.0
    assert event.speech_rate < 1.0


def test_suppressed_rc30_message_is_rejected():
    _raises(PermissionError, lambda: BookDiagnosticsVoiceEventFactory().build(_message(approved=False)))


def test_wrong_source_is_rejected():
    _raises(PermissionError, lambda: BookDiagnosticsVoiceEventFactory().build(_message(version="OTHER")))


def test_decision_affecting_message_is_rejected():
    _raises(PermissionError, lambda: BookDiagnosticsVoiceEventFactory().build(_message(affects_decision=True)))


def test_invalid_speech_rate_is_rejected():
    _raises(ValueError, lambda: BookDiagnosticsVoiceEventFactory(profile=_profile(250)))


if __name__ == "__main__":
    test_normal_message_builds_non_interrupting_event()
    test_urgent_message_can_interrupt()
    test_event_id_is_deterministic_for_same_message()
    test_different_text_changes_event_id()
    test_duration_is_positive_and_rate_configurable()
    test_suppressed_rc30_message_is_rejected()
    test_wrong_source_is_rejected()
    test_decision_affecting_message_is_rejected()
    test_invalid_speech_rate_is_rejected()
    print("RC31 voice event tests: OK")
