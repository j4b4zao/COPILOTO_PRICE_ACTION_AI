"""Leitura, validação e snapshot profundamente readonly do catálogo psicológico (RC44)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
import json


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionCatalogFileReadResult:
    status: str
    source: str
    schema_version: str
    total_sessions: int
    latest_session_id: str | None
    payload: Mapping[str, object]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologySessionCatalogFileReader:
    """Lê documentos de catálogo V1 sem permitir mutação do snapshot retornado."""

    NAME = "TraderPsychologySessionCatalogFileReader"
    VERSION = "RC44"
    SCHEMA_VERSION = "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"

    def read(self, source):
        path = Path(source)
        if not path.is_absolute():
            raise ValueError("source deve ser caminho absoluto.")
        if path.suffix.casefold() != ".json":
            raise ValueError("source deve terminar em .json.")
        if path.is_symlink():
            raise ValueError("source não pode ser link simbólico.")
        if not path.exists():
            raise FileNotFoundError("Arquivo de catálogo não existe.")
        if not path.is_file():
            raise ValueError("source deve apontar para arquivo regular.")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Arquivo de catálogo JSON inválido.") from exc

        self._validate_payload(payload)
        readonly_payload = self._deep_freeze(payload)
        return TraderPsychologySessionCatalogFileReadResult(
            status="READ",
            source=str(path),
            schema_version=payload["schema_version"],
            total_sessions=payload["total_sessions"],
            latest_session_id=payload["latest_session_id"],
            payload=readonly_payload,
        )

    def _validate_payload(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Catálogo deve ser objeto JSON.")
        required = {
            "schema_version",
            "generated_at",
            "status",
            "total_sessions",
            "latest_session_id",
            "sessions",
            "observational_only",
            "score_influence_allowed",
            "order_execution_allowed",
            "operational_block_allowed",
        }
        if not required.issubset(payload):
            raise ValueError("Catálogo incompleto.")
        if payload["schema_version"] != self.SCHEMA_VERSION:
            raise ValueError("Schema de catálogo incompatível.")
        if not isinstance(payload["sessions"], list):
            raise ValueError("sessions deve ser lista.")
        if isinstance(payload["total_sessions"], bool) or not isinstance(
            payload["total_sessions"], int
        ):
            raise ValueError("total_sessions deve ser inteiro.")
        if payload["total_sessions"] < 0:
            raise ValueError("total_sessions não pode ser negativo.")
        if payload["total_sessions"] != len(payload["sessions"]):
            raise ValueError("Contagem de sessões inconsistente.")
        if payload["status"] not in {"EMPTY", "AVAILABLE"}:
            raise ValueError("status de catálogo inválido.")
        if payload["status"] == "EMPTY" and payload["total_sessions"] != 0:
            raise ValueError("Catálogo EMPTY deve ter zero sessões.")
        if payload["status"] == "AVAILABLE" and payload["total_sessions"] == 0:
            raise ValueError("Catálogo AVAILABLE deve conter sessões.")
        if payload["latest_session_id"] is not None and not isinstance(
            payload["latest_session_id"], str
        ):
            raise ValueError("latest_session_id deve ser texto ou None.")
        if payload["observational_only"] is not True:
            raise ValueError("Catálogo deve permanecer observacional.")
        if payload["score_influence_allowed"] is not False:
            raise ValueError("Catálogo não pode influenciar score.")
        if payload["order_execution_allowed"] is not False:
            raise ValueError("Catálogo não pode executar ordens.")
        if payload["operational_block_allowed"] is not False:
            raise ValueError("Catálogo não pode bloquear operação.")

    @classmethod
    def _deep_freeze(cls, value):
        if isinstance(value, dict):
            return MappingProxyType(
                {
                    key: cls._deep_freeze(item)
                    for key, item in value.items()
                }
            )
        if isinstance(value, list):
            return tuple(cls._deep_freeze(item) for item in value)
        return value
