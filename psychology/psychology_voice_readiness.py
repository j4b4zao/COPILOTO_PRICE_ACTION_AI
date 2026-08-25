"""Diagnóstico readonly de prontidão da voz psicológica (RC19)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.voice_assistant import VoiceAssistantConfig


@dataclass(frozen=True, slots=True)
class PsychologyVoiceReadinessSnapshot:
    status: str
    enabled: bool
    configured: bool
    healthcheck_supported: bool
    available: bool | None
    ready: bool
    sink_name: str
    backend_name: str
    reason: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class PsychologyVoiceReadiness:
    """Inspeciona configuração e saúde sem produzir áudio."""

    NAME = "PsychologyVoiceReadiness"
    VERSION = "RC19"

    def inspect(self, *, config, sink=None):
        if not isinstance(config, VoiceAssistantConfig):
            raise TypeError(
                "config deve ser VoiceAssistantConfig."
            )

        if not config.enabled:
            return self._snapshot(
                status="DISABLED",
                enabled=False,
                configured=sink is not None,
                healthcheck_supported=callable(
                    getattr(sink, "healthcheck", None)
                ),
                available=None,
                ready=False,
                sink=sink,
                reason="Voz psicológica desativada por configuração.",
            )

        if sink is None or not callable(
            getattr(sink, "speak", None)
        ):
            return self._snapshot(
                status="NOT_CONFIGURED",
                enabled=True,
                configured=False,
                healthcheck_supported=False,
                available=False,
                ready=False,
                sink=sink,
                reason="Sink de voz psicológica não configurado.",
            )

        healthcheck = getattr(sink, "healthcheck", None)
        if not callable(healthcheck):
            return self._snapshot(
                status="UNVERIFIED",
                enabled=True,
                configured=True,
                healthcheck_supported=False,
                available=None,
                ready=False,
                sink=sink,
                reason="Sink configurado sem healthcheck().",
            )

        try:
            available = bool(healthcheck())
        except Exception as exc:
            return self._snapshot(
                status="ERROR",
                enabled=True,
                configured=True,
                healthcheck_supported=True,
                available=False,
                ready=False,
                sink=sink,
                reason=(
                    "Healthcheck da voz falhou: "
                    f"{type(exc).__name__}."
                ),
            )

        return self._snapshot(
            status="READY" if available else "UNAVAILABLE",
            enabled=True,
            configured=True,
            healthcheck_supported=True,
            available=available,
            ready=available,
            sink=sink,
            reason=(
                "Voz psicológica pronta."
                if available
                else "Backend de voz psicológica indisponível."
            ),
        )

    @staticmethod
    def _snapshot(
        *,
        status,
        enabled,
        configured,
        healthcheck_supported,
        available,
        ready,
        sink,
        reason,
    ):
        backend = getattr(sink, "backend", None)
        return PsychologyVoiceReadinessSnapshot(
            status=status,
            enabled=enabled,
            configured=configured,
            healthcheck_supported=healthcheck_supported,
            available=available,
            ready=ready,
            sink_name=str(
                getattr(sink, "NAME", None)
                or getattr(sink, "name", None)
                or (type(sink).__name__ if sink is not None else "")
            ),
            backend_name=str(
                getattr(backend, "name", "")
                or getattr(sink, "backend_name", "")
                or ""
            ),
            reason=reason,
        )
