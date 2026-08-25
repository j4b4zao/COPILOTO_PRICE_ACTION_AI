"""Pré-voo offline para captura Trading Economics (RC18)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from economic_context.trading_economics_controlled_pipeline import (
    TradingEconomicsControlledPipeline,
)


@dataclass(frozen=True, slots=True)
class TradingEconomicsPreflightReport:
    approved: bool
    status: str
    package_name: str
    session_id_valid: bool
    config_ready: bool
    capture_enabled: bool
    destination_valid: bool
    destination_available: bool
    limits_valid: bool
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False


class TradingEconomicsCapturePreflight:
    """Valida prontidão sem chamar transporte nem criar diretórios/arquivos."""

    NAME = "TradingEconomicsCapturePreflight"
    VERSION = "RC18"
    MAX_RESPONSE_BYTES = 5_000_000

    def evaluate(self, pipeline, destination, *, session_id):
        if not isinstance(pipeline, TradingEconomicsControlledPipeline):
            raise TypeError("pipeline incompatível com o pré-voo.")

        path = Path(destination)
        session_valid = bool(str(session_id or "").strip())
        destination_valid = (
            bool(path.name)
            and path.name.endswith(".calendar-replay.json")
            and not path.is_dir()
        )
        destination_available = destination_valid and not path.exists()
        limits_valid = (
            0 < pipeline.config.timeout_seconds <= 30
            and 0 < pipeline.fetcher.max_response_bytes <= self.MAX_RESPONSE_BYTES
        )

        reasons = []
        if not pipeline.config.ready:
            reasons.append("CONFIG_NOT_READY")
        if not pipeline.capture_enabled:
            reasons.append("CAPTURE_DISABLED")
        if not session_valid:
            reasons.append("INVALID_SESSION_ID")
        if not destination_valid:
            reasons.append("INVALID_DESTINATION")
        elif not destination_available:
            reasons.append("DESTINATION_EXISTS")
        if not limits_valid:
            reasons.append("UNSAFE_LIMITS")

        approved = not reasons
        return TradingEconomicsPreflightReport(
            approved=approved,
            status="APPROVED" if approved else "BLOCKED",
            package_name=path.name if path.name else "",
            session_id_valid=session_valid,
            config_ready=pipeline.config.ready,
            capture_enabled=pipeline.capture_enabled,
            destination_valid=destination_valid,
            destination_available=destination_available,
            limits_valid=limits_valid,
            reasons=tuple(reasons),
        )
