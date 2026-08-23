import pytest

from analysis.replay.book_diagnostics_voice_config import VoiceConfig, validate_voice_config
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def test_default_config_is_safe_and_disabled():
    config = VoiceConfig()
    assert config.enabled is False
    assert config.backend == "NULL_TTS"
    assert config.language == "pt-BR"
    assert config.readonly is True
    assert config.affects_decision is False


def test_validate_returns_normalized_config():
    config = validate_voice_config(VoiceConfig(backend="null_tts"))
    assert config.backend == "NULL_TTS"


def test_with_updates_preserves_contract():
    config = VoiceConfig().with_updates(enabled=True, speech_rate=1.15)
    assert config.enabled is True
    assert config.speech_rate == 1.15

@pytest.mark.parametrize("rate", [0.49, 2.01])
def test_invalid_speech_rate_is_rejected(rate):
    with pytest.raises(ValueError):
        validate_voice_config(VoiceConfig(speech_rate=rate))

@pytest.mark.parametrize("size", [0, 101])
def test_invalid_queue_size_is_rejected(size):
    with pytest.raises(ValueError):
        validate_voice_config(VoiceConfig(queue_max_size=size))


def test_empty_language_is_rejected():
    with pytest.raises(ValueError):
        validate_voice_config(VoiceConfig(language=""))


def test_empty_profile_is_rejected():
    with pytest.raises(ValueError):
        validate_voice_config(VoiceConfig(voice_profile=""))


def test_decision_affecting_config_is_rejected():
    payload = VoiceConfig().to_dict()
    payload["affects_decision"] = True
    with pytest.raises(PermissionError):
        validate_voice_config(payload)


def test_service_uses_config_enabled_state():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=True))
    snap = service.snapshot()
    assert snap.enabled is True
    assert snap.config_version == "RC40-VOICE-CONFIGURATION-CONTRACT"


def test_explicit_enabled_override_remains_backward_compatible():
    service = BookDiagnosticsVoiceService(enabled=True, config=VoiceConfig(enabled=False))
    assert service.enabled is True


def test_enable_disable_updates_config_state():
    service = BookDiagnosticsVoiceService(config=VoiceConfig())
    service.enable()
    assert service.config.enabled is True
    service.disable()
    assert service.config.enabled is False
