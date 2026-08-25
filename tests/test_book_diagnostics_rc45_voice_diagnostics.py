from analysis.replay.book_diagnostics_tts_backend import TTSResult
from analysis.replay.book_diagnostics_tts_backend_registry import BookDiagnosticsTTSBackendRegistry
from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_diagnostics import BookDiagnosticsVoiceDiagnostics


class _Selection:
    selected_voice = "Test Voice"
    reason = "LANGUAGE_MATCH"


class HealthyVoiceBackend:
    name = "HEALTHY"

    def speak(self, command):
        return TTSResult("RC35-TTS-BACKEND-CONTRACT", self.name, command["event_id"], True, True, False, "")

    def stop(self, event_id=None):
        return False

    def healthcheck(self):
        return True

    def available_voices(self):
        return (object(), object())

    def select_voice(self, *, voice_profile, language):
        return _Selection()


class UnhealthyBackend(HealthyVoiceBackend):
    name = "UNHEALTHY"

    def healthcheck(self):
        return False


class BrokenHealthBackend(HealthyVoiceBackend):
    name = "BROKEN_HEALTH"

    def healthcheck(self):
        raise RuntimeError("boom")


class BrokenDiscoveryBackend(HealthyVoiceBackend):
    name = "BROKEN_DISCOVERY"

    def available_voices(self):
        raise RuntimeError("discovery")


class BrokenSelectionBackend(HealthyVoiceBackend):
    name = "BROKEN_SELECTION"

    def select_voice(self, *, voice_profile, language):
        raise RuntimeError("selection")


def _registry_with(name, factory):
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register(name, factory)
    return registry


def test_default_null_tts_is_not_ready_for_real_audio():
    snap = BookDiagnosticsVoiceDiagnostics().inspect()
    assert snap.configured_backend == "NULL_TTS"
    assert snap.backend_registered is True
    assert snap.backend_instantiable is True
    assert snap.backend_healthy is True
    assert snap.ready_for_real_audio is False
    assert snap.readonly is True
    assert snap.affects_decision is False


def test_unknown_backend_is_reported_without_exception():
    snap = BookDiagnosticsVoiceDiagnostics(config=VoiceConfig(backend="UNKNOWN")).inspect()
    assert snap.backend_registered is False
    assert snap.backend_instantiable is False
    assert "unknown TTS backend" in snap.error


def test_healthy_real_backend_requires_service_enabled():
    registry = _registry_with("HEALTHY", HealthyVoiceBackend)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=False, backend="HEALTHY"), backend_registry=registry
    ).inspect()
    assert snap.backend_healthy is True
    assert snap.ready_for_real_audio is False


def test_healthy_enabled_real_backend_with_voice_is_ready():
    registry = _registry_with("HEALTHY", HealthyVoiceBackend)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=True, backend="HEALTHY"), backend_registry=registry
    ).inspect()
    assert snap.available_voice_count == 2
    assert snap.selected_voice == "Test Voice"
    assert snap.selection_reason == "LANGUAGE_MATCH"
    assert snap.ready_for_real_audio is True


def test_unhealthy_backend_is_not_ready():
    registry = _registry_with("UNHEALTHY", UnhealthyBackend)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=True, backend="UNHEALTHY"), backend_registry=registry
    ).inspect()
    assert snap.backend_healthy is False
    assert snap.ready_for_real_audio is False


def test_healthcheck_exception_is_converted_to_diagnostic_error():
    registry = _registry_with("BROKEN_HEALTH", BrokenHealthBackend)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=True, backend="BROKEN_HEALTH"), backend_registry=registry
    ).inspect()
    assert snap.backend_instantiable is True
    assert snap.backend_healthy is False
    assert "healthcheck failed" in snap.error


def test_discovery_exception_is_converted_to_diagnostic_error():
    registry = _registry_with("BROKEN_DISCOVERY", BrokenDiscoveryBackend)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=True, backend="BROKEN_DISCOVERY"), backend_registry=registry
    ).inspect()
    assert "voice discovery failed" in snap.error
    assert snap.ready_for_real_audio is False


def test_selection_exception_is_converted_to_diagnostic_error():
    registry = _registry_with("BROKEN_SELECTION", BrokenSelectionBackend)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=True, backend="BROKEN_SELECTION"), backend_registry=registry
    ).inspect()
    assert "voice selection failed" in snap.error
    assert snap.ready_for_real_audio is False


def test_snapshot_preserves_requested_language_profile_and_rate():
    registry = _registry_with("HEALTHY", HealthyVoiceBackend)
    config = VoiceConfig(enabled=True, backend="HEALTHY", language="en-GB", voice_profile="CUSTOM", speech_rate=1.25)
    snap = BookDiagnosticsVoiceDiagnostics(config=config, backend_registry=registry).inspect()
    assert snap.language == "en-GB"
    assert snap.voice_profile == "CUSTOM"
    assert snap.speech_rate == 1.25


def test_diagnostics_does_not_call_speak():
    class NoSpeakBackend(HealthyVoiceBackend):
        name = "NO_SPEAK"
        def speak(self, command):
            raise AssertionError("speak must not be called by diagnostics")
    registry = _registry_with("NO_SPEAK", NoSpeakBackend)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=True, backend="NO_SPEAK"), backend_registry=registry
    ).inspect()
    assert snap.ready_for_real_audio is True


def test_backend_factory_failure_is_reported():
    registry = BookDiagnosticsTTSBackendRegistry()
    def broken_factory():
        raise RuntimeError("factory failed")
    registry.register("BROKEN_FACTORY", broken_factory)
    snap = BookDiagnosticsVoiceDiagnostics(
        config=VoiceConfig(enabled=True, backend="BROKEN_FACTORY"), backend_registry=registry
    ).inspect()
    assert snap.backend_registered is True
    assert snap.backend_instantiable is False
    assert "factory failed" in snap.error


def test_to_dict_keeps_readonly_contract():
    payload = BookDiagnosticsVoiceDiagnostics().inspect().to_dict()
    assert payload["version"] == "RC45-VOICE-CAPABILITY-DIAGNOSTICS"
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False
