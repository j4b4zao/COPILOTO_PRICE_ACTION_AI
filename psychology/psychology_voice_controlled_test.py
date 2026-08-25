"""Teste explícito e controlado da voz psicológica (RC20)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.psychology_voice_readiness import (
    PsychologyVoiceReadiness,
)
from psychology.voice_assistant import VoiceAssistantConfig


@dataclass(frozen=True, slots=True)
class PsychologyVoiceControlledTestResult:
    status: str
    confirmation_accepted: bool
    readiness_status: str
    attempted: bool
    delivered: bool
    error: str | None
    test_code: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class PsychologyVoiceControlledTest:
    """Executa somente uma frase fixa após confirmação literal."""

    NAME = "PsychologyVoiceControlledTest"
    VERSION = "RC20"
    CONFIRMATION = "CONFIRMAR_TESTE_VOZ_PSICOLOGIA"
    TEST_CODE = "PSYCHOLOGY_CONTROLLED_AUDIO_TEST"
    TEST_TEXT = (
        "Teste de voz do acompanhamento psicológico. "
        "Áudio funcionando."
    )

    def __init__(self, *, readiness=None):
        self.readiness = readiness or PsychologyVoiceReadiness()
        if not callable(getattr(self.readiness, "inspect", None)):
            raise TypeError("readiness deve expor inspect().")
        self.last_result = None

    def run(self, *, config, sink=None, confirmation=""):
        if not isinstance(config, VoiceAssistantConfig):
            raise TypeError(
                "config deve ser VoiceAssistantConfig."
            )
        confirmed = str(confirmation) == self.CONFIRMATION
        readiness = self.readiness.inspect(
            config=config,
            sink=sink,
        )

        if not confirmed:
            return self._finish(
                status="CONFIRMATION_REQUIRED",
                confirmation_accepted=False,
                readiness_status=readiness.status,
                attempted=False,
                delivered=False,
                error=None,
            )

        if not readiness.ready:
            return self._finish(
                status="NOT_READY",
                confirmation_accepted=True,
                readiness_status=readiness.status,
                attempted=False,
                delivered=False,
                error=None,
            )

        try:
            delivered = bool(sink.speak(
                text=self.TEST_TEXT,
                priority="NORMAL",
                code=self.TEST_CODE,
            ))
        except Exception as exc:
            return self._finish(
                status="FAILED",
                confirmation_accepted=True,
                readiness_status=readiness.status,
                attempted=True,
                delivered=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        return self._finish(
            status="DELIVERED" if delivered else "REJECTED",
            confirmation_accepted=True,
            readiness_status=readiness.status,
            attempted=True,
            delivered=delivered,
            error=None,
        )

    def _finish(
        self,
        *,
        status,
        confirmation_accepted,
        readiness_status,
        attempted,
        delivered,
        error,
    ):
        self.last_result = PsychologyVoiceControlledTestResult(
            status=status,
            confirmation_accepted=confirmation_accepted,
            readiness_status=readiness_status,
            attempted=attempted,
            delivered=delivered,
            error=error,
            test_code=self.TEST_CODE,
        )
        return self.last_result
