from dataclasses import dataclass

import pytest

from analysis.replay.book_diagnostics_tts_backend_registry import BookDiagnosticsTTSBackendRegistry
from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


@dataclass(frozen=True)
class _Result:
    version: str = "RC47-CONTROLLED-REAL-AUDIO-TEST"
    executed: bool = True
    completed: bool = True
    error: str = ""
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self):
        return self.__dict__.copy()


class _ReadyBackend:
    name = "READY_TTS"

    def speak(self, command):
        raise AssertionError("RC50 tests must not speak")

    def stop(self, event_id=None):
        return False

    def healthcheck(self):
        return True


class _NotReadyBackend(_ReadyBackend):
    name = "NOT_READY_TTS"

    def healthcheck(self):
        return False


def _service(name="READY_TTS"):
    registry = BookDiagnosticsTTSBackendRegistry()
    backend_cls = _ReadyBackend if name == "READY_TTS" else _NotReadyBackend
    registry.register(name, backend_cls)
    config = VoiceConfig(enabled=True, backend=name)
    return BookDiagnosticsVoiceService(config=config, backend_registry=registry)


def test_readiness_blocks_without_controlled_test(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": True,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    snap = service.readiness()
    assert snap.operational_voice_allowed is False
    assert snap.reason == "CONTROLLED_TEST_REQUIRED"


def test_readiness_accepts_explicit_passed_result(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": True,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    snap = service.readiness(controlled_test=_Result())
    assert snap.operational_voice_allowed is True
    assert snap.reason == "READY"


def test_require_operational_ready_raises_when_blocked(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": False,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    with pytest.raises(PermissionError):
        service.require_operational_ready()


def test_require_operational_ready_returns_ready(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": True,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    snap = service.require_operational_ready(controlled_test=_Result())
    assert snap.operational_voice_allowed is True


def test_test_audio_result_is_remembered(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": True,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    fake = _Result()
    monkeypatch.setattr(
        "analysis.replay.book_diagnostics_voice_service.BookDiagnosticsControlledAudioTest.run",
        lambda self, text=None: fake,
    )
    service.test_audio()
    assert service.readiness().operational_voice_allowed is True


def test_clear_audio_validation_relocks(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": True,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    service._last_controlled_audio_test = _Result()
    assert service.readiness().operational_voice_allowed is True
    snap = service.clear_audio_validation()
    assert snap.operational_voice_allowed is False
    assert snap.reason == "CONTROLLED_TEST_REQUIRED"


def test_failed_controlled_test_does_not_unlock(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": True,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    failed = _Result(completed=False, error="failure")
    snap = service.readiness(controlled_test=failed)
    assert snap.operational_voice_allowed is False
    assert snap.reason == "CONTROLLED_TEST_NOT_PASSED"


def test_readiness_snapshot_is_observational(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": True,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    payload = service.readiness(controlled_test=_Result()).to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_readiness_does_not_change_enabled_state(monkeypatch):
    service = _service()
    before = service.enabled
    monkeypatch.setattr(service, "diagnostics", lambda: type("D", (), {
        "to_dict": lambda self: {
            "version": "RC45-VOICE-CAPABILITY-DIAGNOSTICS",
            "ready_for_real_audio": False,
            "readonly": True,
            "affects_decision": False,
        }
    })())
    service.readiness()
    assert service.enabled is before


def test_not_ready_backend_remains_blocked():
    service = _service("NOT_READY_TTS")
    snap = service.readiness(controlled_test=_Result())
    assert snap.operational_voice_allowed is False
