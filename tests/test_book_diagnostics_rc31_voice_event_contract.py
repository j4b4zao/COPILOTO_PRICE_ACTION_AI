from types import SimpleNamespace

from analysis.replay.book_diagnostics_voice_event_contract import (
    BookDiagnosticsVoiceEventFactory,
)


def _approved(priority="NORMAL", message="Leitura do mercado: contexto estável."):
    return SimpleNamespace(
        to_dict=lambda: {
            "version": "RC30-ASSISTANT-MESSAGE-POLICY",
            "should_emit": True,
            "priority": priority,
            "reason": "MESSAGE_APPROVED",
            "message": message,
            "fingerprint": "abc123",
            "cooldown_seconds": 30,
            "readonly": True,
            "affects_decision": False,
        }
    )


def test_build_normal_voice_event():
    event = BookDiagnosticsVoiceEventFactory().build(
        _approved(),
        now="2026-08-22T20:00:00-03:00",
    )
    assert event.version == "RC31-VOICE-EVENT-CONTRACT"
    assert event.priority == "NORMAL"
    assert event.interrupt_allowed is False
    assert event.voice_profile == "REFINED_BRITISH_AI_ASSISTANT"
    assert event.locale == "pt-BR"
    assert event.readonly is True
    assert event.affects_decision is False
    assert event.requires_tts_adapter is True
    assert event.event_id.startswith("voice_")


def test_urgent_event_can_interrupt():
    event = BookDiagnosticsVoiceEventFactory().build(_approved("URGENT", "Atenção: volatilidade elevada."))
    assert event.interrupt_allowed is True
    assert event.volume == 1.0
    assert event.rate > 1.0


def test_caution_event_uses_calm_prosody():
    event = BookDiagnosticsVoiceEventFactory().build(_approved("CAUTION", "Cautela: aguarde confirmação."))
    assert event.interrupt_allowed is False
    assert event.rate < 1.0
    assert event.pitch < 0.0


def test_duration_is_positive_and_scales_with_text():
    factory = BookDiagnosticsVoiceEventFactory(words_per_minute=120)
    short = factory.build(_approved(message="Mercado calmo."), now="2026-08-22T20:00:00+00:00")
    long = factory.build(
        _approved(message="Mercado com tendência forte, porém comprimido e exigindo confirmação antes de uma nova entrada."),
        now="2026-08-22T20:00:01+00:00",
    )
    assert short.estimated_duration_seconds >= 1.0
    assert long.estimated_duration_seconds > short.estimated_duration_seconds


def test_block_unapproved_message():
    payload = _approved().to_dict()
    payload["should_emit"] = False
    try:
        BookDiagnosticsVoiceEventFactory().build(payload)
    except PermissionError:
        pass
    else:
        raise AssertionError("unapproved RC30 message should be blocked")


def test_block_decision_affecting_message():
    payload = _approved().to_dict()
    payload["affects_decision"] = True
    try:
        BookDiagnosticsVoiceEventFactory().build(payload)
    except PermissionError:
        pass
    else:
        raise AssertionError("decision-affecting message should be blocked")


def test_reject_wrong_source_version():
    payload = _approved().to_dict()
    payload["version"] = "OTHER"
    try:
        BookDiagnosticsVoiceEventFactory().build(payload)
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong source version should be rejected")


def test_invalid_speech_rate_configuration():
    try:
        BookDiagnosticsVoiceEventFactory(words_per_minute=20)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid WPM should be rejected")


if __name__ == "__main__":
    test_build_normal_voice_event()
    test_urgent_event_can_interrupt()
    test_caution_event_uses_calm_prosody()
    test_duration_is_positive_and_scales_with_text()
    test_block_unapproved_message()
    test_block_decision_affecting_message()
    test_reject_wrong_source_version()
    test_invalid_speech_rate_configuration()
    print("RC31 voice event contract tests: OK")
