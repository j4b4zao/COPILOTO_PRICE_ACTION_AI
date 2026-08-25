import core.system_initializer as module
from core.system_initializer import SystemInitializer


class Dummy:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class DummyPipeline(Dummy):
    pass


def _patch_runtime_dependencies(monkeypatch):
    names = (
        "ConnectionManager",
        "Collector",
        "EventBus",
        "DataValidator",
        "RiskManager",
        "MarketFilter",
        "TradeQuality",
        "SignalGenerator",
        "ExecutionEngine",
        "Monitor",
        "AlertManager",
        "TradeLogger",
    )
    for name in names:
        monkeypatch.setattr(module, name, Dummy)
    monkeypatch.setattr(module, "AnalysisPipeline", DummyPipeline)


def test_initializer_default_keeps_voice_disabled():
    system = SystemInitializer()
    assert system.voice_enabled is False
    assert system.voice is None


def test_initializer_accepts_voice_enabled_without_breaking_signature():
    system = SystemInitializer(voice_enabled=True)
    assert system.voice_enabled is True
    assert system.voice is None


def test_inicializar_creates_disabled_voice_service_by_default(monkeypatch):
    _patch_runtime_dependencies(monkeypatch)
    system = SystemInitializer().inicializar()
    assert system.voice is not None
    assert system.voice.enabled is False
    assert system.voice.snapshot().backend == "DISABLED"
    assert isinstance(system.pipeline, DummyPipeline)
    assert system.pipeline.kwargs["event_bus"] is system.event_bus


def test_inicializar_can_enable_safe_null_tts_voice_service(monkeypatch):
    _patch_runtime_dependencies(monkeypatch)
    system = SystemInitializer(voice_enabled=True).inicializar()
    snap = system.voice.snapshot()
    assert snap.enabled is True
    assert snap.available is True
    assert snap.backend == "NULL_TTS"
    assert snap.backend_healthy is True
    assert snap.affects_decision is False


def test_voice_integration_does_not_replace_existing_modules(monkeypatch):
    _patch_runtime_dependencies(monkeypatch)
    system = SystemInitializer(voice_enabled=True).inicializar()
    assert isinstance(system.connection, Dummy)
    assert isinstance(system.collector, Dummy)
    assert isinstance(system.validator, Dummy)
    assert isinstance(system.risk, Dummy)
    assert isinstance(system.signal, Dummy)
    assert isinstance(system.execution, Dummy)
    assert isinstance(system.monitor, Dummy)
    assert isinstance(system.alert, Dummy)
    assert isinstance(system.logger, Dummy)
