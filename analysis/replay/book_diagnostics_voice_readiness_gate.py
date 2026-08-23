"""
BookDiagnostics RC49 - Voice Readiness Gate.

Bloqueia qualquer futura ativacao operacional da voz ate que diagnostico e teste
controlado estejam explicitamente aprovados. Esta camada permanece somente de
apresentacao e nunca altera Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class VoiceReadinessGateSnapshot:
    version: str
    diagnostics_ready: bool
    controlled_test_passed: bool
    operational_voice_allowed: bool
    reason: str
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceReadinessGate:
    VERSION = "RC49-VOICE-READINESS-GATE"

    def evaluate(self, *, diagnostics, controlled_test=None) -> VoiceReadinessGateSnapshot:
        d = self._payload(diagnostics)
        self._validate_diagnostics(d)

        diagnostics_ready = bool(d.get("ready_for_real_audio", False))
        if not diagnostics_ready:
            return self._snapshot(False, False, False, "DIAGNOSTICS_NOT_READY")

        if controlled_test is None:
            return self._snapshot(True, False, False, "CONTROLLED_TEST_REQUIRED")

        t = self._payload(controlled_test)
        self._validate_controlled_test(t)
        test_passed = (
            bool(t.get("executed", False))
            and bool(t.get("completed", False))
            and not str(t.get("error", "") or "").strip()
        )

        if not test_passed:
            return self._snapshot(True, False, False, "CONTROLLED_TEST_NOT_PASSED")

        return self._snapshot(True, True, True, "READY")

    def require_operational_ready(self, *, diagnostics, controlled_test=None) -> VoiceReadinessGateSnapshot:
        snapshot = self.evaluate(diagnostics=diagnostics, controlled_test=controlled_test)
        if not snapshot.operational_voice_allowed:
            raise PermissionError(f"operational voice blocked: {snapshot.reason}")
        return snapshot

    def _snapshot(
        self,
        diagnostics_ready: bool,
        controlled_test_passed: bool,
        operational_voice_allowed: bool,
        reason: str,
    ) -> VoiceReadinessGateSnapshot:
        return VoiceReadinessGateSnapshot(
            version=self.VERSION,
            diagnostics_ready=diagnostics_ready,
            controlled_test_passed=controlled_test_passed,
            operational_voice_allowed=operational_voice_allowed,
            reason=reason,
        )

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    @staticmethod
    def _validate_diagnostics(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC45-VOICE-CAPABILITY-DIAGNOSTICS":
            raise PermissionError("RC49 requires RC45 diagnostics")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid diagnostics contract")

    @staticmethod
    def _validate_controlled_test(payload: dict) -> None:
        if str(payload.get("version", "")) != "RC47-CONTROLLED-REAL-AUDIO-TEST":
            raise PermissionError("RC49 requires RC47 controlled audio result")
        if not bool(payload.get("readonly", False)) or bool(payload.get("affects_decision", True)):
            raise PermissionError("invalid controlled test contract")
