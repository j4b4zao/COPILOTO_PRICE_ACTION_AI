"""
BookDiagnostics RC39/RC40 - Voice Service Integration.

Expõe a fachada RC38 como serviço opcional e usa o contrato RC40 como fonte
central de configuração. Continua sem alterar Strategy, Score, Risk, Decision
ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_voice_config import VoiceConfig, validate_voice_config
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

    def __init__(self, *, enabled: bool | None = None, config: VoiceConfig | None = None, facade=None):
        base = validate_voice_config(config or VoiceConfig())
        if enabled is not None:
            base = base.with_updates(enabled=bool(enabled))
        self.config = base
        self.enabled = base.enabled
        self._facade = facade
        if self.enabled and self._facade is None:
            self._facade = BookDiagnosticsVoiceRuntimeFacade()

    @property
    def available(self) -> bool:
        return self._facade is not None

    @property
    def facade(self):
        if not self.enabled:
            raise RuntimeError("voice service is disabled")
        if self._facade is None:
            self._facade = BookDiagnosticsVoiceRuntimeFacade()
        return self._facade

    def enable(self):
        self.config = self.config.with_updates(enabled=True)
        self.enabled = True
        if self._facade is None:
            self._facade = BookDiagnosticsVoiceRuntimeFacade()
        return self.snapshot()

    def disable(self, *, reset: bool = True):
        if reset and self._facade is not None:
            self._facade.reset()
        self.config = self.config.with_updates(enabled=False)
        self.enabled = False
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
        return self.snapshot()

    def snapshot(self) -> VoiceServiceSnapshot:
        common = dict(
            version=self.VERSION,
            enabled=self.enabled,
            config_version=self.config.version,
            language=self.config.language,
            voice_profile=self.config.voice_profile,
            speech_rate=self.config.speech_rate,
        )
        if self._facade is None:
            return VoiceServiceSnapshot(available=False, queue_size=0, session_state="IDLE", backend="DISABLED", backend_healthy=False, last_status=None, last_error=None, **common)
        payload = self._facade.snapshot().to_dict()
        self._validate_facade_snapshot(payload)
        return VoiceServiceSnapshot(available=True, queue_size=int(payload["queue_size"]), session_state=str(payload["session_state"]), backend=str(payload["backend"]), backend_healthy=bool(payload["backend_healthy"]), last_status=payload.get("last_status"), last_error=payload.get("last_error"), **common)

    def _require_enabled(self):
        if not self.enabled:
            raise RuntimeError("voice service is disabled")

    @staticmethod
    def _validate_facade_snapshot(payload: dict):
        if str(payload.get("version", "")) != "RC38-VOICE-RUNTIME-FACADE":
            raise PermissionError("RC39 requires RC38 facade snapshot")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid facade snapshot")
