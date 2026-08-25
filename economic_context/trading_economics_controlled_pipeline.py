"""Pipeline controlado Trading Economics para captura/replay (RC17)."""

from __future__ import annotations

from economic_context.economic_calendar_controlled_capture import (
    EconomicCalendarControlledCapture,
)
from economic_context.trading_economics_calendar_fetcher import (
    TradingEconomicsCalendarFetcher,
)
from economic_context.trading_economics_config import TradingEconomicsConfig


class TradingEconomicsControlledPipeline:
    """Une configuração, transporte e captura sob duas autorizações explícitas."""

    NAME = "TradingEconomicsControlledPipeline"
    VERSION = "RC17"

    def __init__(
        self,
        config,
        *,
        capture_enabled=False,
        transport=None,
        mapper=None,
        package_store=None,
        require_strict_payload=True,
        max_response_bytes=1_000_000,
    ):
        if not isinstance(config, TradingEconomicsConfig):
            raise TypeError("config deve ser TradingEconomicsConfig.")

        self.config = config
        self.fetcher = TradingEconomicsCalendarFetcher(
            config,
            transport=transport,
            max_response_bytes=max_response_bytes,
        )
        self.capture_engine = EconomicCalendarControlledCapture(
            self.fetcher,
            enabled=bool(capture_enabled and config.ready),
            mapper=mapper,
            package_store=package_store,
            require_strict_payload=require_strict_payload,
        )
        self.capture_enabled = bool(capture_enabled and config.ready)
        self.last_diagnostics = self._diagnostics(
            "READY" if self.capture_enabled else "DISABLED"
        )

    @classmethod
    def from_environment(cls, environment=None, **kwargs):
        return cls(
            TradingEconomicsConfig.from_environment(environment),
            **kwargs,
        )

    @property
    def ready(self):
        return self.config.ready and self.capture_enabled

    def enable_capture(self):
        if not self.config.ready:
            self.last_diagnostics = self._diagnostics("CONFIG_NOT_READY")
            raise PermissionError("Configuração Trading Economics não está pronta.")
        self.capture_enabled = True
        self.capture_engine.enable()
        self.last_diagnostics = self._diagnostics("READY")

    def disable_capture(self):
        self.capture_enabled = False
        self.capture_engine.disable()
        self.last_diagnostics = self._diagnostics("DISABLED")

    def capture(
        self,
        destination,
        *,
        session_id,
        captured_at,
        forbidden_secret_values=(),
    ):
        if not self.ready:
            self.last_diagnostics = self._diagnostics("DISABLED")
            raise PermissionError("Pipeline Trading Economics está desativado.")

        secrets = (
            self.config.authorization_value(),
            *tuple(forbidden_secret_values),
        )
        try:
            result = self.capture_engine.capture(
                destination,
                session_id=session_id,
                captured_at=captured_at,
                forbidden_secret_values=secrets,
            )
        except Exception:
            self.last_diagnostics = self._diagnostics(
                self.capture_engine.last_diagnostics.get(
                    "status",
                    "CAPTURE_ERROR",
                )
            )
            raise

        self.last_diagnostics = {
            **self._diagnostics("CAPTURED"),
            "session_id": result.session_id,
            "package_name": result.package_path,
            "received_count": result.received_count,
            "mapped_count": result.mapped_count,
            "filtered_count": result.filtered_count,
        }
        return result

    def _diagnostics(self, status):
        return {
            **self.config.diagnostics(),
            "status": status,
            "capture_enabled": self.capture_enabled,
            "pipeline_ready": self.ready,
        }
