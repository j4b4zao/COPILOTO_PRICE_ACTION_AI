"""Runner observacional de payloads gravados do calendário econômico RC12."""

from __future__ import annotations

from dataclasses import dataclass

from economic_context.economic_calendar_payload_normalizer import (
    EconomicCalendarPayloadNormalizer,
)
from economic_context.economic_calendar_trial_gate import (
    EconomicCalendarTrialEvidence,
    EconomicCalendarTrialGate,
    EconomicCalendarTrialPolicy,
)
from economic_context.trading_economics_calendar_mapper import (
    TradingEconomicsCalendarMapper,
)


@dataclass(frozen=True, slots=True)
class EconomicCalendarReplaySession:
    session_id: str
    received_count: int
    mapped_count: int
    event_count: int
    expected_event_count: int
    rejected_count: int
    duplicate_count: int
    maximum_clock_error_seconds: int
    critical_events_checked: tuple[str, ...]
    secrets_exposed: bool
    observational_only: bool = True


@dataclass(frozen=True, slots=True)
class EconomicCalendarReplayReport:
    sessions: tuple[EconomicCalendarReplaySession, ...]
    evidence: EconomicCalendarTrialEvidence
    eligible_for_manual_review: bool
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False


class EconomicCalendarReplayTrialRunner:
    """Agrega replays offline; não possui transporte HTTP nem integração operacional."""

    NAME = "EconomicCalendarReplayTrialRunner"
    VERSION = "RC12"

    CRITICAL_ALIASES = {
        "COPOM": ("COPOM", "INTEREST RATE DECISION BRAZIL"),
        "IPCA": ("IPCA",),
        "NON_FARM_PAYROLLS": ("NON FARM PAYROLL", "NONFARM PAYROLL"),
        "US_CPI": ("US CPI", "UNITED STATES CPI", "CPI INFLATION"),
        "FOMC": ("FOMC", "FED INTEREST RATE DECISION"),
        "JOBLESS_CLAIMS": ("JOBLESS CLAIM", "UNEMPLOYMENT CLAIM"),
    }

    def __init__(self, *, policy=None, mapper=None, normalizer=None, gate=None):
        self.policy = policy or EconomicCalendarTrialPolicy()
        self.mapper = mapper or TradingEconomicsCalendarMapper(source_timezone="UTC")
        self.normalizer = normalizer or EconomicCalendarPayloadNormalizer()
        self.gate = gate or EconomicCalendarTrialGate()
        self._sessions = {}

    @property
    def sessions(self):
        return tuple(self._sessions.values())

    def add_session(
        self,
        *,
        session_id,
        payload,
        expected_event_count,
        maximum_clock_error_seconds,
        diagnostic_text="",
        forbidden_secret_values=(),
    ):
        session_id = str(session_id).strip()
        if not session_id:
            raise ValueError("session_id é obrigatório.")
        if session_id in self._sessions:
            raise ValueError("session_id duplicado.")
        expected_event_count = int(expected_event_count)
        clock_error = int(maximum_clock_error_seconds)
        if expected_event_count <= 0:
            raise ValueError("expected_event_count deve ser positivo.")
        if clock_error < 0:
            raise ValueError("maximum_clock_error_seconds não pode ser negativo.")

        raw_rows = tuple(payload)
        canonical = self.mapper.map(raw_rows)
        mapper_diagnostics = dict(self.mapper.last_diagnostics)
        normalized = self.normalizer.normalize(
            canonical,
            source="TRADING_ECONOMICS_REPLAY",
            default_timezone="UTC",
        )

        secret_values = tuple(
            str(value) for value in forbidden_secret_values if str(value)
        )
        diagnostic_text = str(diagnostic_text)
        secrets_exposed = any(value in diagnostic_text for value in secret_values)

        session = EconomicCalendarReplaySession(
            session_id=session_id,
            received_count=len(raw_rows),
            mapped_count=len(canonical),
            event_count=len(normalized.events),
            expected_event_count=expected_event_count,
            rejected_count=(
                int(mapper_diagnostics.get("rejected_count", 0) or 0)
                + normalized.rejected_count
            ),
            duplicate_count=normalized.duplicate_count,
            maximum_clock_error_seconds=clock_error,
            critical_events_checked=self._critical_events(normalized.events),
            secrets_exposed=secrets_exposed,
        )
        self._sessions[session_id] = session
        return session

    def report(self):
        sessions = self.sessions
        expected = sum(item.expected_event_count for item in sessions)
        received = sum(item.received_count for item in sessions)
        event_count = sum(item.event_count for item in sessions)
        rejected = sum(item.rejected_count for item in sessions)
        duplicates = sum(item.duplicate_count for item in sessions)

        evidence = EconomicCalendarTrialEvidence(
            completed_sessions=len(sessions),
            coverage_ratio=(min(event_count / expected, 1.0) if expected else 0.0),
            rejection_ratio=(rejected / received if received else 0.0),
            duplicate_ratio=(duplicates / received if received else 0.0),
            maximum_clock_error_seconds=max(
                (item.maximum_clock_error_seconds for item in sessions),
                default=0,
            ),
            critical_events_checked=tuple(sorted({
                event
                for session in sessions
                for event in session.critical_events_checked
            })),
            secrets_exposed=any(item.secrets_exposed for item in sessions),
        )
        decision = self.gate.evaluate(evidence, policy=self.policy)
        return EconomicCalendarReplayReport(
            sessions=sessions,
            evidence=evidence,
            eligible_for_manual_review=decision.eligible_for_manual_review,
            reasons=decision.reasons,
        )

    def clear(self):
        self._sessions.clear()

    @classmethod
    def _critical_events(cls, events):
        found = set()
        for event in events:
            title = " ".join(event.title.upper().replace("-", " ").split())
            for canonical, aliases in cls.CRITICAL_ALIASES.items():
                if any(alias in title for alias in aliases):
                    found.add(canonical)
        return tuple(sorted(found))
