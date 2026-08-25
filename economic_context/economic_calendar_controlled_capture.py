"""Captura controlada para pacotes de replay do calendário econômico RC14."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from economic_context.economic_calendar_replay_package_store import (
    EconomicCalendarReplayPackageStore,
)
from economic_context.trading_economics_calendar_mapper import (
    TradingEconomicsCalendarMapper,
)


@dataclass(frozen=True, slots=True)
class EconomicCalendarCaptureResult:
    session_id: str
    package_path: str
    received_count: int
    mapped_count: int
    filtered_count: int
    checksum_sha256: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False


class EconomicCalendarControlledCapture:
    """Captura opt-in; transporte/credencial são externos e nunca persistidos."""

    NAME = "EconomicCalendarControlledCapture"
    VERSION = "RC14"

    def __init__(
        self,
        raw_fetcher,
        *,
        enabled=False,
        mapper=None,
        package_store=None,
        require_strict_payload=True,
    ):
        if not callable(raw_fetcher):
            raise TypeError("Captura requer raw_fetcher callable.")
        self.raw_fetcher = raw_fetcher
        self.enabled = bool(enabled)
        self.mapper = mapper or TradingEconomicsCalendarMapper(
            source_timezone="UTC"
        )
        self.package_store = package_store or EconomicCalendarReplayPackageStore()
        self.require_strict_payload = bool(require_strict_payload)
        self.last_diagnostics = {
            "status": "DISABLED" if not self.enabled else "NOT_RUN",
            "observational_only": True,
        }

    def capture(
        self,
        destination,
        *,
        session_id,
        captured_at,
        forbidden_secret_values=(),
    ):
        if not self.enabled:
            self.last_diagnostics = {
                "status": "DISABLED",
                "observational_only": True,
            }
            raise PermissionError("Captura do calendário está desativada.")

        try:
            payload = self.raw_fetcher(now=captured_at)
        except Exception as exc:
            self.last_diagnostics = {
                "status": "FETCH_ERROR",
                "error_type": type(exc).__name__,
                "observational_only": True,
            }
            raise RuntimeError("Falha segura na captura do calendário.") from None

        try:
            rows = tuple(payload)
        except TypeError:
            self.last_diagnostics = {
                "status": "INVALID_PAYLOAD",
                "error_type": "TypeError",
                "observational_only": True,
            }
            raise TypeError("Resposta do calendário deve ser iterável.") from None

        mapped = self.mapper.map(rows)
        diagnostics = dict(self.mapper.last_diagnostics)
        rejected = int(diagnostics.get("rejected_count", 0) or 0)
        if not mapped:
            self._invalid(diagnostics, "NO_BR_US_EVENTS")
            raise ValueError("Captura sem eventos válidos de Brasil/EUA.")
        if self.require_strict_payload and rejected:
            self._invalid(diagnostics, "PARTIAL_PAYLOAD_REJECTED")
            raise ValueError("Captura parcial rejeitada pela política estrita.")

        try:
            package = self.package_store.save(
                destination,
                session_id=session_id,
                captured_at=captured_at,
                payload=rows,
                forbidden_secret_values=forbidden_secret_values,
                overwrite=False,
            )
        except Exception as exc:
            self.last_diagnostics = {
                "status": "PACKAGE_REJECTED",
                "error_type": type(exc).__name__,
                "received_count": len(rows),
                "mapped_count": len(mapped),
                "observational_only": True,
            }
            raise

        result = EconomicCalendarCaptureResult(
            session_id=package.session_id,
            package_path=Path(destination).name,
            received_count=len(rows),
            mapped_count=len(mapped),
            filtered_count=int(diagnostics.get("filtered_count", 0) or 0),
            checksum_sha256=package.checksum_sha256,
        )
        self.last_diagnostics = {
            "status": "CAPTURED",
            "session_id": result.session_id,
            "package_name": result.package_path,
            "received_count": result.received_count,
            "mapped_count": result.mapped_count,
            "filtered_count": result.filtered_count,
            "observational_only": True,
        }
        return result

    def enable(self):
        self.enabled = True
        self.last_diagnostics = {
            "status": "NOT_RUN",
            "observational_only": True,
        }

    def disable(self):
        self.enabled = False
        self.last_diagnostics = {
            "status": "DISABLED",
            "observational_only": True,
        }

    def _invalid(self, diagnostics, reason):
        self.last_diagnostics = {
            "status": "INVALID_PAYLOAD",
            "reason": reason,
            "received_count": int(diagnostics.get("received_count", 0) or 0),
            "mapped_count": int(diagnostics.get("mapped_count", 0) or 0),
            "filtered_count": int(diagnostics.get("filtered_count", 0) or 0),
            "rejected_count": int(diagnostics.get("rejected_count", 0) or 0),
            "observational_only": True,
        }
