import pytest

from analysis.replay.book_diagnostics_tts_backend import TTSResult
from analysis.replay.book_diagnostics_tts_backend_registry import (
    BookDiagnosticsTTSBackendRegistry,
)
from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


class FakeBackend:
    name = "FAKE_TTS"

    def speak(self, command):
        return TTSResult(
            version="RC35-TTS-BACKEND-CONTRACT",
            backend=self.name,
            event_id=command["event_id"],
            accepted=True,
            completed=True,
            interrupted=False,
            error="",
        )

    def stop(self, event_id=None):
        return True

    def healthcheck(self):
        return True


def test_registry_starts_with_null_tts():
    registry = BookDiagnosticsTTSBackendRegistry()
    assert registry.names() == ("NULL_TTS",)
    assert registry.contains("null_tts") is True


def test_registry_snapshot_is_readonly_and_safe():
    snap = BookDiagnosticsTTSBackendRegistry().snapshot()
    assert snap.version == "RC41-TTS-BACKEND-REGISTRY"
    assert snap.default_backend == "NULL_TTS"
    assert snap.readonly is True
    assert snap.affects_decision is False


def test_create_default_backend_returns_null_tts():
    backend = BookDiagnosticsTTSBackendRegistry().create()
    assert backend.name == "NULL_TTS"
    assert backend.healthcheck() is True


def test_register_and_create_custom_backend():
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("fake_tts", FakeBackend)
    backend = registry.create("FAKE_TTS")
    assert isinstance(backend, FakeBackend)


def test_duplicate_registration_requires_replace():
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("FAKE_TTS", FakeBackend)
    with pytest.raises(ValueError):
        registry.register("fake_tts", FakeBackend)


def test_replace_registration_is_allowed():
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("FAKE_TTS", FakeBackend)
    registry.register("FAKE_TTS", FakeBackend, replace=True)
    assert registry.create("FAKE_TTS").name == "FAKE_TTS"


def test_unknown_backend_is_rejected():
    with pytest.raises(LookupError):
        BookDiagnosticsTTSBackendRegistry().create("UNKNOWN")


def test_null_tts_cannot_be_unregistered():
    with pytest.raises(PermissionError):
        BookDiagnosticsTTSBackendRegistry().unregister("NULL_TTS")


def test_custom_backend_can_be_unregistered():
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("FAKE_TTS", FakeBackend)
    assert registry.unregister("FAKE_TTS") is True
    assert registry.contains("FAKE_TTS") is False


def test_factory_must_be_callable():
    with pytest.raises(TypeError):
        BookDiagnosticsTTSBackendRegistry().register("BAD", object())


def test_backend_contract_is_validated():
    class BrokenBackend:
        name = "BROKEN"

    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("BROKEN", BrokenBackend)
    with pytest.raises(TypeError):
        registry.create("BROKEN")


def test_backend_name_must_match_registry_key():
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("OTHER", FakeBackend)
    with pytest.raises(ValueError):
        registry.create("OTHER")


def test_voice_service_resolves_backend_from_rc40_config():
    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("FAKE_TTS", FakeBackend)
    config = VoiceConfig(enabled=True, backend="FAKE_TTS")

    service = BookDiagnosticsVoiceService(config=config, backend_registry=registry)
    snap = service.snapshot()

    assert snap.enabled is True
    assert snap.backend == "FAKE_TTS"
    assert snap.backend_healthy is True


def test_disabled_service_does_not_resolve_unknown_backend_until_enabled():
    config = VoiceConfig(enabled=False, backend="FUTURE_TTS")
    service = BookDiagnosticsVoiceService(config=config)
    assert service.snapshot().backend == "DISABLED"

    with pytest.raises(LookupError):
        service.enable()


def test_service_applies_rc40_queue_capacity():
    config = VoiceConfig(enabled=True, queue_max_size=3)
    service = BookDiagnosticsVoiceService(config=config)
    assert service.facade.runtime.queue.max_size == 3
