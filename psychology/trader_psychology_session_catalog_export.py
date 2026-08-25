"""Exportação JSON readonly do catálogo psicológico (RC39)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json

from psychology.trader_psychology_session_catalog import (
    TraderPsychologySessionCatalog,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionCatalogExportItem:
    session_id: str
    session_date: str
    session_timezone: str
    total_entries: int
    total_observations: int
    first_sequence: int
    last_sequence: int
    started_at: str
    updated_at: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionCatalogExport:
    schema_version: str
    generated_at: str
    status: str
    total_sessions: int
    latest_session_id: str | None
    sessions: tuple[
        TraderPsychologySessionCatalogExportItem,
        ...,
    ]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False

    def to_dict(self):
        return asdict(self)

    def to_json(self, *, indent=None):
        if indent is not None and (
            isinstance(indent, bool)
            or not isinstance(indent, int)
            or not 0 <= indent <= 8
        ):
            raise ValueError(
                "indent deve ser None ou inteiro entre 0 e 8."
            )
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=indent,
            separators=(
                (",", ":")
                if indent is None
                else None
            ),
        )


class TraderPsychologySessionCatalogExporter:
    """Serializa catálogo imutável; não escreve arquivos."""

    NAME = "TraderPsychologySessionCatalogExporter"
    VERSION = "RC39"
    SCHEMA_VERSION = (
        "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"
    )

    def __init__(self, *, clock=None):
        self.clock = clock or (
            lambda: datetime.now(timezone.utc)
        )
        if not callable(self.clock):
            raise TypeError("clock deve ser chamável.")

    def export(self, catalog, *, generated_at=None):
        if not isinstance(
            catalog,
            TraderPsychologySessionCatalog,
        ):
            raise TypeError(
                "catalog deve ser "
                "TraderPsychologySessionCatalog."
            )
        timestamp = (
            generated_at
            if generated_at is not None
            else self.clock()
        )
        timestamp = self._aware_datetime(
            "generated_at",
            timestamp,
        )
        return TraderPsychologySessionCatalogExport(
            schema_version=self.SCHEMA_VERSION,
            generated_at=timestamp.isoformat(),
            status=catalog.status,
            total_sessions=catalog.total_sessions,
            latest_session_id=catalog.latest_session_id,
            sessions=tuple(
                TraderPsychologySessionCatalogExportItem(
                    session_id=item.session_id,
                    session_date=item.session_date,
                    session_timezone=item.session_timezone,
                    total_entries=item.total_entries,
                    total_observations=item.total_observations,
                    first_sequence=item.first_sequence,
                    last_sequence=item.last_sequence,
                    started_at=self._aware_datetime(
                        "item.started_at",
                        item.started_at,
                    ).isoformat(),
                    updated_at=self._aware_datetime(
                        "item.updated_at",
                        item.updated_at,
                    ).isoformat(),
                )
                for item in catalog.sessions
            ),
        )

    @staticmethod
    def _aware_datetime(name, value):
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise TypeError(
                f"{name} deve ser datetime com timezone."
            )
        return value
