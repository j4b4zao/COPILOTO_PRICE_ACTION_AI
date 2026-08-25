"""Projeção readonly da Psicologia para dashboard (RC24)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from psychology.psychology_voice_readiness import (
    PsychologyVoiceReadinessSnapshot,
)
from psychology.trader_psychology_session_review import (
    TraderPsychologySessionReview,
)
from psychology.trader_psychology_session_summary import (
    TraderPsychologySessionSummary,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologyDashboardMessage:
    code: str
    text: str
    category: str


@dataclass(frozen=True, slots=True)
class TraderPsychologyDashboardProjection:
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
        TraderPsychologyDashboardMessage,
        ...,
    ]
    latest_sequence: int | None
    updated_at: datetime | None
    total_observations: int = 0
    longest_unchanged_observations: int = 0
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologyDashboardProjector:
    """Combina somente contratos psicológicos readonly."""

    NAME = "TraderPsychologyDashboardProjector"
    VERSION = "RC24"

    def project(self, *, summary, review, voice_readiness):
        if not isinstance(
            summary,
            TraderPsychologySessionSummary,
        ):
            raise TypeError(
                "summary deve ser "
                "TraderPsychologySessionSummary."
            )
        if not isinstance(
            review,
            TraderPsychologySessionReview,
        ):
            raise TypeError(
                "review deve ser TraderPsychologySessionReview."
            )
        if not isinstance(
            voice_readiness,
            PsychologyVoiceReadinessSnapshot,
        ):
            raise TypeError(
                "voice_readiness deve ser "
                "PsychologyVoiceReadinessSnapshot."
            )
        if review.source_total_cycles != summary.total_cycles:
            raise ValueError(
                "review e summary pertencem a sessões diferentes."
            )

        dominant_count = next(
            (
                count
                for code, count in summary.signal_counts
                if code == summary.dominant_signal_code
            ),
            0,
        )
        if summary.status == "EMPTY":
            status = "EMPTY"
            headline = "Aguardando dados psicológicos da sessão."
        elif summary.pause_recommended_cycles:
            status = "PAUSE_OBSERVED"
            headline = (
                "A sessão possui recomendações de pausa registradas."
            )
        elif summary.attention_cycles:
            status = "ATTENTION_OBSERVED"
            headline = (
                "A sessão possui padrões psicológicos para revisão."
            )
        else:
            status = "NEUTRAL"
            headline = (
                "Nenhum padrão psicológico recorrente foi registrado."
            )

        return TraderPsychologyDashboardProjection(
            status=status,
            headline=headline,
            total_cycles=summary.total_cycles,
            neutral_cycles=summary.neutral_cycles,
            attention_cycles=summary.attention_cycles,
            pause_recommended_cycles=(
                summary.pause_recommended_cycles
            ),
            linked_evidence_cycles=(
                summary.linked_evidence_cycles
            ),
            evidence_trade_count=len(
                summary.unique_evidence_trade_ids
            ),
            dominant_signal_code=(
                summary.dominant_signal_code
            ),
            dominant_signal_count=dominant_count,
            voice_readiness_status=voice_readiness.status,
            voice_ready=voice_readiness.ready,
            voice_delivered_cycles=(
                summary.voice_delivered_cycles
            ),
            voice_suppressed_cycles=(
                summary.voice_suppressed_cycles
            ),
            voice_failed_cycles=summary.voice_failed_cycles,
            review_messages=tuple(
                TraderPsychologyDashboardMessage(
                    code=message.code,
                    text=message.text,
                    category=message.category,
                )
                for message in review.messages
            ),
            latest_sequence=summary.last_sequence,
            updated_at=summary.updated_at,
            total_observations=summary.total_observations,
            longest_unchanged_observations=(
                summary.longest_unchanged_observations
            ),
        )
