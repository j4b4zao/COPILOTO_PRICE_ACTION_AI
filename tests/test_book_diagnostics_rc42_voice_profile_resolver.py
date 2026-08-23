from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_event import BookDiagnosticsVoiceEventFactory
from analysis.replay.book_diagnostics_voice_profile_resolver import (
    BookDiagnosticsVoiceProfileResolver,
    validate_resolved_voice_profile,
)
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _message(priority="NORMAL"):
    return {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "should_emit": True,
        "priority": priority,
        "reason": "MESSAGE_APPROVED",
        "message": "Leitura de mercado configurada.",
        "fingerprint": "rc42-test",
        "cooldown_seconds": 0,
        "readonly": True,
        "affects_decision": False,
    }


def _approved(priority="NORMAL"):
    return {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "approved": True,
        "text": "Leitura de mercado configurada.",
        "priority": priority,
        "readonly": True,
        "affects_decision": False,
    }


def test_resolver_uses_rc40_defaults():
    profile = BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig())
    assert profile.language == "pt-BR"
    assert profile.voice_profile == "BRITISH_CALM_PRECISE_ASSISTANT"
    assert profile.speech_rate == 1.0
    assert profile.words_per_minute == 145
    assert profile.readonly is True
    assert profile.affects_decision is False


def test_resolver_applies_custom_language_profile_and_rate():
    config = VoiceConfig(language="en-GB", voice_profile="BRITISH_NEUTRAL", speech_rate=1.2)
    profile = BookDiagnosticsVoiceProfileResolver().resolve(config)
    assert profile.language == "en-GB"
    assert profile.voice_profile == "BRITISH_NEUTRAL"
    assert profile.speech_rate == 1.2
    assert profile.words_per_minute == 174


def test_resolver_clamps_wpm_to_rc31_supported_range():
    slow = BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig(speech_rate=0.5))
    fast = BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig(speech_rate=2.0))
    assert slow.words_per_minute == 90
    assert fast.words_per_minute == 220


def test_resolved_profile_validation_rejects_wrong_version():
    profile = BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig()).to_dict()
    profile["version"] = "RC41"
    try:
        validate_resolved_voice_profile(profile)
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_rc31_factory_preserves_default_compatibility():
    event = BookDiagnosticsVoiceEventFactory().build(_approved())
    assert event.language == "pt-BR"
    assert event.voice_profile == "BRITISH_CALM_PRECISE_ASSISTANT"
    assert event.speech_rate == 1.0


def test_rc31_factory_uses_resolved_profile():
    config = VoiceConfig(language="en-GB", voice_profile="PROFILE_X", speech_rate=1.1)
    profile = BookDiagnosticsVoiceProfileResolver().resolve(config)
    event = BookDiagnosticsVoiceEventFactory(profile=profile).build(_approved())
    assert event.language == "en-GB"
    assert event.voice_profile == "PROFILE_X"
    assert event.speech_rate == 1.1


def test_rc42_changes_estimated_duration_with_speech_rate():
    slow = BookDiagnosticsVoiceEventFactory(
        profile=BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig(speech_rate=0.7))
    ).build(_approved())
    fast = BookDiagnosticsVoiceEventFactory(
        profile=BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig(speech_rate=1.4))
    ).build(_approved())
    assert slow.estimated_duration_seconds > fast.estimated_duration_seconds


def test_urgent_interrupt_respects_rc40_policy_disabled():
    profile = BookDiagnosticsVoiceProfileResolver().resolve(
        VoiceConfig(allow_urgent_interrupt=False)
    )
    event = BookDiagnosticsVoiceEventFactory(profile=profile).build(_approved("URGENT"))
    assert event.interrupt_allowed is False


def test_urgent_interrupt_respects_rc40_policy_enabled():
    profile = BookDiagnosticsVoiceProfileResolver().resolve(
        VoiceConfig(allow_urgent_interrupt=True)
    )
    event = BookDiagnosticsVoiceEventFactory(profile=profile).build(_approved("URGENT"))
    assert event.interrupt_allowed is True


def test_non_urgent_never_interrupts_even_when_policy_enabled():
    profile = BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig())
    event = BookDiagnosticsVoiceEventFactory(profile=profile).build(_approved("CAUTION"))
    assert event.interrupt_allowed is False


def test_service_propagates_profile_into_runtime_queue():
    config = VoiceConfig(
        enabled=True,
        language="en-GB",
        voice_profile="PROFILE_SERVICE",
        speech_rate=1.25,
    )
    service = BookDiagnosticsVoiceService(config=config)
    decision = service.submit_message(_message())
    assert decision.accepted is True
    queued = service.facade.runtime.queue.peek_next()
    assert queued["language"] == "en-GB"
    assert queued["voice_profile"] == "PROFILE_SERVICE"
    assert queued["speech_rate"] == 1.25


def test_service_propagates_interrupt_policy_into_runtime_queue():
    service = BookDiagnosticsVoiceService(
        config=VoiceConfig(enabled=True, allow_urgent_interrupt=False)
    )
    service.submit_message(_message("URGENT"))
    queued = service.facade.runtime.queue.peek_next()
    assert queued["interrupt_allowed"] is False


def test_profile_is_readonly_and_never_affects_decision():
    profile = BookDiagnosticsVoiceProfileResolver().resolve(VoiceConfig())
    assert profile.readonly is True
    assert profile.affects_decision is False
