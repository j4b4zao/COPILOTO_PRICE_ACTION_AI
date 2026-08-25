"""Exportação JSON readonly do dashboard psicológico (RC25)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json

from psychology.trader_psychology_dashboard_projection import (
    TraderPsychologyDashboardProjection,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologyDashboardExportMessage:
    code: str
    text: str
    category: str


@dataclass(frozen=True, slots=True)
class TraderPsychologyDashboardExport:
    schema_version: str
    generated_at: str
    status: str
    headline: str
    total_cycles: int
    neutral_cycles: int
    attention_cycles: int
    pause_recommended_cycles: int
    linked_evidence_cycles: int
    evidence_trade_count: int
    dominant_signal_code: str | None
    dominant_signal_count: int
    voice_readiness_status: str
    voice_ready: bool
    voice_delivered_cycles: int
    voice_suppressed_cycles: int
    voice_failed_cycles: int
    review_messages: tuple[
        TraderPsychologyDashboardExportMessage,
        ...,
    ]
    latest_sequence: int | None
    updated_at: str | None
    total_observations: int = 0
    longest_unchanged_observations: int = 0
    session_date: str | None = None
    session_timezone: str | None = None
    session_id: str | None = None
    prior_session_entries_ignored: int = 0
    prior_session_observations_ignored: int = 0
    observed_span_seconds: float = 0.0
    started_at_local: str | None = None
    updated_at_local: str | None = None
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


class TraderPsychologyDashboardExporter:
    """Cria documento versionado; não escreve arquivos."""

    NAME = "TraderPsychologyDashboardExporter"
    VERSION = "RC31"
    SCHEMA_VERSION = "TRADER_PSYCHOLOGY_DASHBOARD_V1"

    def __init__(self, *, clock=None):
        self.clock = clock or (
            lambda: datetime.now(timezone.utc)
        )
        if not callable(self.clock):
            raise TypeError("clock deve ser chamável.")

    def export(self, projection, *, generated_at=None):
        if not isinstance(
            projection,
            TraderPsychologyDashboardProjection,
        ):
            raise TypeError(
                "projection deve ser "
                "TraderPsychologyDashboardProjection."
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
        updated_at = projection.updated_at
        if updated_at is not None:
            updated_at = self._aware_datetime(
                "projection.updated_at",
                updated_at,
            )

        return TraderPsychologyDashboardExport(
            schema_version=self.SCHEMA_VERSION,
            generated_at=timestamp.isoformat(),
            status=projection.status,
            headline=projection.headline,
            total_cycles=projection.total_cycles,
            neutral_cycles=projection.neutral_cycles,
            attention_cycles=projection.attention_cycles,
            pause_recommended_cycles=(
                projection.pause_recommended_cycles
            ),
            linked_evidence_cycles=(
                projection.linked_evidence_cycles
            ),
            evidence_trade_count=(
                projection.evidence_trade_count
            ),
            dominant_signal_code=(
                projection.dominant_signal_code
            ),
            dominant_signal_count=(
                projection.dominant_signal_count
            ),
            voice_readiness_status=(
                projection.voice_readiness_status
            ),
            voice_ready=projection.voice_ready,
            voice_delivered_cycles=(
                projection.voice_delivered_cycles
            ),
            voice_suppressed_cycles=(
                projection.voice_suppressed_cycles
            ),
            voice_failed_cycles=(
                projection.voice_failed_cycles
            ),
            review_messages=tuple(
                TraderPsychologyDashboardExportMessage(
                    code=message.code,
                    text=message.text,
                    category=message.category,
                )
                for message in projection.review_messages
            ),
            latest_sequence=projection.latest_sequence,
            updated_at=(
                updated_at.isoformat()
                if updated_at is not None
                else None
            ),
            total_observations=projection.total_observations,
            longest_unchanged_observations=(
                projection.longest_unchanged_observations
            ),
            session_date=projection.session_date,
            session_timezone=projection.session_timezone,
            session_id=projection.session_id,
            prior_session_entries_ignored=(
                projection.prior_session_entries_ignored
            ),
            prior_session_observations_ignored=(
                projection.prior_session_observations_ignored
            ),
            observed_span_seconds=(
                projection.observed_span_seconds
            ),
            started_at_local=projection.started_at_local,
            updated_at_local=projection.updated_at_local,
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
