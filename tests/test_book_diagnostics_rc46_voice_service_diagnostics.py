from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService
from analysis.replay.book_diagnostics_tts_backend_registry import BookDiagnosticsTTSBackendRegistry


class DiagnosticBackend:
    name = "DIAGNOSTIC_BACKEND"

    def __init__(self):
        self.spoken = False

    def speak(self, command):
        self.spoken = True
        raise AssertionError("diagnostics must not call speak")

    def stop(self, event_id=None):
        return False

    def healthcheck(self):
        return True


class BrokenHealthBackend(DiagnosticBackend):
    name = "BROKEN_HEALTH"

    def healthcheck(self):
        raise RuntimeError("health boom")


def _registry(*backends):
    registry = BookDiagnosticsTTSBackendRegistry()
    for backend_cls in backends:
        registry.register(backend_cls.name, backend_cls)
    return registry


def test_rc46_exposes_diagnostics_when_service_disabled():
    service = BookDiagnosticsVoiceService(config=VoiceConfig())
    result = service.diagnostics()
    assert result.version == "RC45-VOICE-CAPABILITY-DIAGNOSTICS"
    assert result.enabled is False
    assert result.configured_backend == "NULL_TTS"
    assert result.ready_for_real_audio is False
    assert result.readonly is True
    assert result.affects_decision is False


def test_rc46_diagnostics_does_not_enable_service():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    service.diagnostics()
    assert service.enabled is False
    assert service.available is False


def test_rc46_diagnostics_uses_service_registry():
    registry = _registry(DiagnosticBackend)
    config = VoiceConfig(enabled=True, backend="DIAGNOSTIC_BACKEND")
    service = BookDiagnosticsVoiceService(config=config, backend_registry=registry)
    result = service.diagnostics()
    assert result.backend_registered is True
    assert result.backend_instantiable is True
    assert result.backend_healthy is True
    assert result.ready_for_real_audio is True


def test_rc46_diagnostics_never_calls_speak():
    created = []

    def factory():
        backend = DiagnosticBackend()
        created.append(backend)
        return backend

    registry = BookDiagnosticsTTSBackendRegistry()
    registry.register("DIAGNOSTIC_BACKEND", factory)
    service = BookDiagnosticsVoiceService(
        config=VoiceConfig(enabled=True, backend="DIAGNOSTIC_BACKEND"),
        backend_registry=registry,
    )
    service.diagnostics()
    assert created
    assert all(backend.spoken is False for backend in created)


def test_rc46_unknown_backend_returns_controlled_diagnostic():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False, backend="MISSING_BACKEND"))
    result = service.diagnostics()
    assert result.backend_registered is False
    assert result.backend_instantiable is False
    assert result.ready_for_real_audio is False
    assert "unknown TTS backend" in str(result.error)


def test_rc46_healthcheck_failure_is_controlled():
    registry = _registry(BrokenHealthBackend)
    service = BookDiagnosticsVoiceService(
        config=VoiceConfig(enabled=True, backend="BROKEN_HEALTH"),
        backend_registry=registry,
    )
    result = service.diagnostics()
    assert result.backend_registered is True
    assert result.backend_instantiable is True
    assert result.backend_healthy is False
    assert result.ready_for_real_audio is False
    assert "healthcheck failed" in str(result.error)


def test_rc46_diagnostics_reflects_current_enable_state():
    service = BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False))
    before = service.diagnostics()
    service.enable()
    after = service.diagnostics()
    assert before.enabled is False
    assert after.enabled is True


def test_rc46_diagnostics_reflects_language_profile_and_rate():
    config = VoiceConfig(
        enabled=False,
        language="en-GB",
        voice_profile="BRITISH_CALM_PRECISE_ASSISTANT",
        speech_rate=1.25,
    )
    service = BookDiagnosticsVoiceService(config=config)
    result = service.diagnostics()
    assert result.language == "en-GB"
    assert result.voice_profile == "BRITISH_CALM_PRECISE_ASSISTANT"
    assert result.speech_rate == 1.25


def test_rc46_system_initializer_exposes_voice_diagnostics(monkeypatch):
    import core.system_initializer as module

    class Dummy:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(module, "ConnectionManager", Dummy)
    monkeypatch.setattr(module, "Collector", Dummy)
    monkeypatch.setattr(module, "EventBus", Dummy)
    monkeypatch.setattr(module, "DataValidator", Dummy)
    monkeypatch.setattr(module, "AnalysisPipeline", Dummy)
    monkeypatch.setattr(module, "RiskManager", Dummy)
    monkeypatch.setattr(module, "MarketFilter", Dummy)
    monkeypatch.setattr(module, "TradeQuality", Dummy)
    monkeypatch.setattr(module, "SignalGenerator", Dummy)
    monkeypatch.setattr(module, "ExecutionEngine", Dummy)
    monkeypatch.setattr(module, "Monitor", Dummy)
    monkeypatch.setattr(module, "AlertManager", Dummy)
    monkeypatch.setattr(module, "TradeLogger", Dummy)

    system = module.SystemInitializer().inicializar()
    result = system.voice.diagnostics()
    assert result.version == "RC45-VOICE-CAPABILITY-DIAGNOSTICS"
    assert result.enabled is False
    assert result.ready_for_real_audio is False


def test_rc46_diagnostics_does_not_mutate_operational_fields():
    service = BookDiagnosticsVoiceService(config=VoiceConfig())
    before = service.snapshot().to_dict()
    service.diagnostics()
    after = service.snapshot().to_dict()
    assert before == after
