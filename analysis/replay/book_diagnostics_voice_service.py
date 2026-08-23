"""
BookDiagnostics RC39/RC40/RC41/RC42/RC46/RC47/RC50/RC54 - Voice Service Integration.

Expoe a fachada RC38 como servico opcional, usa RC40 como configuracao,
RC41 para resolver o backend, RC42 para aplicar idioma, perfil, velocidade,
RC46 para diagnosticos seguros, RC47 para teste real de audio somente por
chamada explicita, RC50 para expor a trava RC49 no servico e RC54 para
expor o orquestrador RC53 sem conectar automaticamente ao app.main.
Nao altera o nucleo operacional.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_runtime_event_bridge import BookDiagnosticsRuntimeEventBridge
from analysis.replay.book_diagnostics_tts_backend import BookDiagnosticsTTSGateway
from analysis.replay.book_diagnostics_tts_backend_registry import (
    BookDiagnosticsTTSBackendRegistry,
    get_default_tts_backend_registry,
)
from analysis.replay.book_diagnostics_tts_runtime import BookDiagnosticsTTSRuntimeCoordinator
from analysis.replay.book_diagnostics_voice_audio_test import BookDiagnosticsControlledAudioTest
from analysis.replay.book_diagnostics_voice_config import VoiceConfig, validate_voice_config
from analysis.replay.book_diagnostics_voice_diagnostics import BookDiagnosticsVoiceDiagnostics
from analysis.replay.book_diagnostics_voice_event import BookDiagnosticsVoiceEventFactory
from analysis.replay.book_diagnostics_voice_orchestrator import BookDiagnosticsVoiceOrchestrator
from analysis.replay.book_diagnostics_voice_profile_resolver import BookDiagnosticsVoiceProfileResolver
from analysis.replay.book_diagnostics_voice_queue import BookDiagnosticsVoiceQueue
from analysis.replay.book_diagnostics_voice_readiness_gate import BookDiagnosticsVoiceReadinessGate
from analysis.replay.book_diagnostics_voice_runtime_facade import BookDiagnosticsVoiceRuntimeFacade


@dataclass(slots=True, frozen=True)
class VoiceServiceSnapshot:
    version: str
    enabled: bool
    available: bool
    queue_size: int
    session_state: str
    backend: str
    backend_healthy: bool
    last_status: str | None
    last_error: str | None
    config_version: str
    language: str
    voice_profile: str
    speech_rate: float
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceService:
    VERSION = "RC39-VOICE-SERVICE-INTEGRATION"

    def __init__(self, *, enabled: bool | None = None, config: VoiceConfig | None = None, facade=None, backend_registry: BookDiagnosticsTTSBackendRegistry | None = None):
        base = validate_voice_config(config or VoiceConfig())
        if enabled is not None:
            base = base.with_updates(enabled=bool(enabled))
        self.config = base
        self.enabled = base.enabled
        self.backend_registry = backend_registry or get_default_tts_backend_registry()
        self._facade = facade
        self._last_controlled_audio_test = None
        self._readiness_gate = BookDiagnosticsVoiceReadinessGate()
        self._orchestrator = None
        if self.enabled and self._facade is None:
            self._facade = self._build_facade()

    @property
    def available(self) -> bool:
        return self._facade is not None

    @property
    def facade(self):
        if not self.enabled:
            raise RuntimeError("voice service is disabled")
        if self._facade is None:
            self._facade = self._build_facade()
        return self._facade

    @property
    def orchestrator(self) -> BookDiagnosticsVoiceOrchestrator:
        """Expoe RC53 de forma lazy, sem qualquer chamada automatica pelo bot."""
        if self._orchestrator is None:
            self._orchestrator = BookDiagnosticsVoiceOrchestrator.from_voice_service(self)
        return self._orchestrator

    def enable(self):
        self.config = self.config.with_updates(enabled=True)
        self.enabled = True
        if self._facade is None:
            self._facade = self._build_facade()
        return self.snapshot()

    def disable(self, *, reset: bool = True):
        if reset and self._facade is not None:
            self._facade.reset()
        if reset and self._orchestrator is not None:
            self._orchestrator.reset()
        self.config = self.config.with_updates(enabled=False)
        self.enabled = False
        return self.snapshot()

    def diagnostics(self):
        return BookDiagnosticsVoiceDiagnostics(
            config=self.config,
            backend_registry=self.backend_registry,
        ).inspect()

    def test_audio(self, *, text: str | None = None):
        """Executa RC47 somente por chamada explicita e registra o ultimo resultado."""
        result = BookDiagnosticsControlledAudioTest(
            config=self.config,
            backend_registry=self.backend_registry,
        ).run(text=text)
        self._last_controlled_audio_test = result
        return result

    def readiness(self, *, controlled_test=None):
        """Avalia RC49 usando o diagnostico atual e o ultimo RC47 quando disponivel."""
        test_result = controlled_test if controlled_test is not None else self._last_controlled_audio_test
        return self._readiness_gate.evaluate(
            diagnostics=self.diagnostics(),
            controlled_test=test_result,
        )

    def require_operational_ready(self, *, controlled_test=None):
        """Bloqueia qualquer futura voz operacional ate RC45 + RC47 estarem aprovados."""
        test_result = controlled_test if controlled_test is not None else self._last_controlled_audio_test
        return self._readiness_gate.require_operational_ready(
            diagnostics=self.diagnostics(),
            controlled_test=test_result,
        )

    def clear_audio_validation(self):
        """Invalida explicitamente a aprovacao RC47 previamente armazenada."""
        self._last_controlled_audio_test = None
        return self.readiness()

    def check_projection(self, projection, *, now=None):
        """Aplica RC53 em modo consulta; nunca despacha voz."""
        return self.orchestrator.check(projection, now=now)

    def dispatch_projection(self, projection, *, now=None):
        """Aplica RC53 em modo dispatch, ainda protegido por RC49/RC50/RC51."""
        return self.orchestrator.dispatch(projection, now=now)

    def reset_orchestrator(self):
        """Limpa apenas cooldown/deduplicacao RC30 mantidos pelo RC53."""
        if self._orchestrator is not None:
            self._orchestrator.reset()
        return self.snapshot()

    def submit_message(self, message_decision):
        self._require_enabled(); return self.facade.submit_message(message_decision)

    def submit_and_process(self, message_decision):
        self._require_enabled(); return self.facade.submit_and_process(message_decision)

    def process_next(self):
        self._require_enabled(); return self.facade.process_next()

    def complete_active(self, *, event_id: str | None = None):
        self._require_enabled(); return self.facade.complete_active(event_id=event_id)

    def fail_active(self, error: str, *, event_id: str | None = None):
        self._require_enabled(); return self.facade.fail_active(error, event_id=event_id)

    def stop_active(self) -> bool:
        self._require_enabled(); return self.facade.stop_active()

    def reset(self):
        if self._facade is not None:
            self._facade.reset()
        if self._orchestrator is not None:
            self._orchestrator.reset()
        return self.snapshot()

    def snapshot(self) -> VoiceServiceSnapshot:
        common = dict(version=self.VERSION, enabled=self.enabled, config_version=self.config.version, language=self.config.language, voice_profile=self.config.voice_profile, speech_rate=self.config.speech_rate)
        if self._facade is None:
            return VoiceServiceSnapshot(available=False, queue_size=0, session_state="IDLE", backend="DISABLED", backend_healthy=False, last_status=None, last_error=None, **common)
        payload = self._facade.snapshot().to_dict()
        self._validate_facade_snapshot(payload)
        return VoiceServiceSnapshot(available=True, queue_size=int(payload["queue_size"]), session_state=str(payload["session_state"]), backend=str(payload["backend"]), backend_healthy=bool(payload["backend_healthy"]), last_status=payload.get("last_status"), last_error=payload.get("last_error"), **common)

    def _build_facade(self) -> BookDiagnosticsVoiceRuntimeFacade:
        backend = self.backend_registry.create(self.config.backend)
        gateway = BookDiagnosticsTTSGateway(backend=backend)
        queue = BookDiagnosticsVoiceQueue(max_size=self.config.queue_max_size)
        runtime = BookDiagnosticsTTSRuntimeCoordinator(queue=queue, gateway=gateway)
        profile = BookDiagnosticsVoiceProfileResolver().resolve(self.config)
        factory = BookDiagnosticsVoiceEventFactory(profile=profile)
        bridge = BookDiagnosticsRuntimeEventBridge(factory=factory, runtime=runtime)
        return BookDiagnosticsVoiceRuntimeFacade(bridge=bridge)

    def _require_enabled(self):
        if not self.enabled:
            raise RuntimeError("voice service is disabled")

    @staticmethod
    def _validate_facade_snapshot(payload: dict):
        if str(payload.get("version", "")) != "RC38-VOICE-RUNTIME-FACADE":
            raise PermissionError("RC39 requires RC38 facade snapshot")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid facade snapshot")
