"""Configuração segura e fail-closed da Trading Economics (RC15)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class TradingEconomicsConfig:
    """Configuração imutável; nunca contém o segredo em representações públicas."""

    api_key: str
    base_url: str = "https://api.tradingeconomics.com"
    enabled: bool = False
    timeout_seconds: float = 5.0

    ENV_API_KEY = "COPILOTO_TE_API_KEY"
    ENV_ENABLED = "COPILOTO_TE_ENABLED"
    ENV_BASE_URL = "COPILOTO_TE_BASE_URL"
    ENV_TIMEOUT = "COPILOTO_TE_TIMEOUT_SECONDS"

    def __post_init__(self):
        key = str(self.api_key or "").strip()
        base_url = str(self.base_url or "").strip().rstrip("/")
        timeout = float(self.timeout_seconds)

        if self.enabled and not key:
            raise ValueError("Trading Economics habilitada sem credencial.")
        if key and any(char.isspace() for char in key):
            raise ValueError("Credencial Trading Economics inválida.")
        if timeout <= 0 or timeout > 30:
            raise ValueError("Timeout deve estar entre 0 e 30 segundos.")

        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Base URL Trading Economics deve usar HTTPS sem credenciais.")

        object.__setattr__(self, "api_key", key)
        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "timeout_seconds", timeout)

    @classmethod
    def from_environment(cls, environment=None):
        """Carrega somente nomes dedicados; não consulta arquivos nem argumentos."""

        if environment is None:
            import os

            environment = os.environ

        enabled = cls._parse_enabled(environment.get(cls.ENV_ENABLED, "0"))
        timeout_raw = environment.get(cls.ENV_TIMEOUT, "5")
        try:
            timeout = float(timeout_raw)
        except (TypeError, ValueError):
            raise ValueError("Timeout Trading Economics inválido.") from None

        return cls(
            api_key=environment.get(cls.ENV_API_KEY, ""),
            base_url=environment.get(
                cls.ENV_BASE_URL,
                "https://api.tradingeconomics.com",
            ),
            enabled=enabled,
            timeout_seconds=timeout,
        )

    @staticmethod
    def _parse_enabled(value):
        normalized = str(value or "").strip().lower()
        if normalized in {"", "0", "false", "no", "off"}:
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
        raise ValueError("Flag Trading Economics inválida.")

    @property
    def ready(self):
        return self.enabled and bool(self.api_key)

    def authorization_value(self):
        """Entrega a credencial somente ao adaptador de transporte autorizado."""

        if not self.ready:
            raise PermissionError("Trading Economics não está habilitada.")
        return self.api_key

    def diagnostics(self):
        return {
            "provider": "TRADING_ECONOMICS",
            "enabled": self.enabled,
            "ready": self.ready,
            "base_host": urlsplit(self.base_url).hostname,
            "timeout_seconds": self.timeout_seconds,
            "credential_present": bool(self.api_key),
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        }

    def __repr__(self):
        return (
            "TradingEconomicsConfig("
            f"api_key='<redacted>', base_url={self.base_url!r}, "
            f"enabled={self.enabled!r}, timeout_seconds={self.timeout_seconds!r})"
        )
