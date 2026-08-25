"""Fachada readonly para leitura verificada do catálogo psicológico (RC46)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.trader_psychology_session_catalog_file_reader import (
    TraderPsychologySessionCatalogFileReadResult,
    TraderPsychologySessionCatalogFileReader,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionCatalogIntegrityReceipt:
    status: str
    source: str
    sha256: str
    byte_size: int
    schema_version: str
    total_sessions: int
    latest_session_id: str | None
    integrity_verified: bool
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologySessionCatalogIntegrityFacade:
    """Expõe verificação explícita sem hidratar estado nem alterar o arquivo."""

    NAME = "TraderPsychologySessionCatalogIntegrityFacade"
    VERSION = "RC46"

    def __init__(self, reader=None):
        self.reader = reader or TraderPsychologySessionCatalogFileReader()

    def read(self, source, *, expected_sha256=None):
        result = self.reader.read(
            source,
            expected_sha256=expected_sha256,
        )
        return self._receipt(result)

    @staticmethod
    def _receipt(result: TraderPsychologySessionCatalogFileReadResult):
        return TraderPsychologySessionCatalogIntegrityReceipt(
            status=result.status,
            source=result.source,
            sha256=result.sha256,
            byte_size=result.byte_size,
            schema_version=result.schema_version,
            total_sessions=result.total_sessions,
            latest_session_id=result.latest_session_id,
            integrity_verified=result.integrity_verified,
        )
