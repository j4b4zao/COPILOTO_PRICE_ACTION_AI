"""Correlação explicável entre sinais e confirmações (RC13)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.trader_psychology_confirmation_audit import (
    ConfirmationAuditEntry,
)
from psychology.trader_psychology_runtime import (
    TraderPsychologyRuntimeResult,
)


@dataclass(frozen=True, slots=True)
class PsychologyEvidenceLink:
    source_kind: str
    code: str
    severity: str
    audit_sequences: tuple[int, ...]
    trade_ids: tuple[str, ...]
    fact_names: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class TraderPsychologyEvidenceReport:
    status: str
    links: tuple[PsychologyEvidenceLink, ...]
    unlinked_signal_codes: tuple[str, ...]
    unlinked_pause_reason_codes: tuple[str, ...]
    latest_audit_sequence: int | None
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologyEvidenceCorrelator:
    """Liga alertas a fatos aceitos sem modificar o runtime."""

    NAME = "TraderPsychologyEvidenceCorrelator"
    VERSION = "RC13"

    EXPLANATIONS = {
        "OVERTRADING": "Aberturas confirmadas na sessão.",
        "REVENGE_TRADING": "Loss confirmado seguido da abertura observada.",
        "STOP_SEQUENCE": "Fechamentos negativos consecutivos confirmados.",
        "FOMO": "Fatos explícitos da abertura mais recente.",
        "RUSHED_REENTRY": "Último loss e abertura posterior confirmados.",
        "OVERCONFIDENCE": "Quantidade atual e resultados positivos confirmados.",
        "OUTSIDE_PLAN": "Checklist explícito da abertura mais recente.",
        "EXTREME_DAILY_LOSS": "Fechamentos negativos confirmados na sessão.",
        "MANUAL_PAUSE": "Pausa manual não nasce de confirmação de trade.",
        "EXTREME_REVENGE_PATTERN": "Loss e aumento posterior confirmados.",
    }

    def correlate(self, runtime_result, audit_entries):
        if not isinstance(
            runtime_result,
            TraderPsychologyRuntimeResult,
        ):
            raise TypeError(
                "runtime_result deve ser "
                "TraderPsychologyRuntimeResult."
            )
        if not isinstance(audit_entries, (list, tuple)):
            raise TypeError("audit_entries deve ser lista ou tupla.")
        if any(
            not isinstance(entry, ConfirmationAuditEntry)
            for entry in audit_entries
        ):
            raise TypeError(
                "audit_entries contém entrada incompatível."
            )

        ordered = tuple(
            sorted(audit_entries, key=lambda entry: entry.sequence)
        )
        accepted = tuple(
            entry
            for entry in ordered
            if entry.accepted
            and entry.publication_published is True
        )
        links = []
        unlinked_signals = []

        for signal in runtime_result.psychology.signals:
            evidence = self._signal_entries(
                signal.code,
                runtime_result,
                accepted,
            )
            if not evidence:
                unlinked_signals.append(signal.code)
                continue
            links.append(
                self._link(
                    source_kind="SIGNAL",
                    code=signal.code,
                    severity=signal.severity,
                    entries=evidence,
                )
            )

        unlinked_pause = []
        for code in runtime_result.psychology.pause_reason_codes:
            evidence = self._pause_entries(
                code,
                runtime_result,
                accepted,
            )
            if not evidence:
                unlinked_pause.append(code)
                continue
            links.append(
                self._link(
                    source_kind="PAUSE",
                    code=code,
                    severity="EXTREME",
                    entries=evidence,
                )
            )

        return TraderPsychologyEvidenceReport(
            status="LINKED" if links else "NO_LINKED_EVIDENCE",
            links=tuple(links),
            unlinked_signal_codes=tuple(
                dict.fromkeys(unlinked_signals)
            ),
            unlinked_pause_reason_codes=tuple(
                dict.fromkeys(unlinked_pause)
            ),
            latest_audit_sequence=(
                ordered[-1].sequence if ordered else None
            ),
        )

    def _signal_entries(self, code, runtime, entries):
        opens = self._accepted(entries, "OPEN")
        closes = self._accepted(entries, "CLOSE")
        negative = tuple(
            entry
            for entry in closes
            if self._fact_number(entry, "result_r") < 0.0
        )
        positive = tuple(
            entry
            for entry in closes
            if self._fact_number(entry, "result_r") > 0.0
        )
        latest_open = opens[-1:] if opens else ()

        if code == "OVERTRADING":
            count = runtime.state.trades_today
            return opens[-count:] if count > 0 else ()
        if code == "REVENGE_TRADING":
            return self._latest_loss_and_open(
                negative,
                latest_open,
            )
        if code == "STOP_SEQUENCE":
            count = runtime.state.consecutive_losses
            return negative[-count:] if count > 0 else ()
        if code == "FOMO":
            if latest_open and (
                self._fact_bool(latest_open[-1], "chased_price")
                or self._fact_bool(
                    latest_open[-1],
                    "skipped_confirmation",
                )
            ):
                return latest_open
            return ()
        if code == "OUTSIDE_PLAN":
            if latest_open and not self._fact_bool(
                latest_open[-1],
                "plan_checklist_passed",
                default=True,
            ):
                return latest_open
            return ()
        if code == "RUSHED_REENTRY":
            return self._latest_loss_and_open(
                negative,
                latest_open,
            )
        if code == "OVERCONFIDENCE":
            return tuple(positive[-3:]) + tuple(latest_open)
        return ()

    def _pause_entries(self, code, runtime, entries):
        closes = self._accepted(entries, "CLOSE")
        negative = tuple(
            entry
            for entry in closes
            if self._fact_number(entry, "result_r") < 0.0
        )
        opens = self._accepted(entries, "OPEN")
        latest_open = opens[-1:] if opens else ()

        if code == "EXTREME_DAILY_LOSS":
            return negative
        if code == "STOP_SEQUENCE":
            count = runtime.state.consecutive_losses
            return negative[-count:] if count > 0 else ()
        if code == "EXTREME_REVENGE_PATTERN":
            return self._latest_loss_and_open(
                negative,
                latest_open,
            )
        return ()

    def _link(
        self,
        *,
        source_kind,
        code,
        severity,
        entries,
    ):
        entries = self._unique(entries)
        fact_names = tuple(
            dict.fromkeys(
                name
                for entry in entries
                for name, value in entry.facts
                if value not in (None, "<INVALID>")
            )
        )
        return PsychologyEvidenceLink(
            source_kind=source_kind,
            code=code,
            severity=severity,
            audit_sequences=tuple(
                entry.sequence for entry in entries
            ),
            trade_ids=tuple(
                dict.fromkeys(entry.trade_id for entry in entries)
            ),
            fact_names=fact_names,
            explanation=self.EXPLANATIONS.get(
                code,
                "Fatos confirmados da sessão.",
            ),
        )

    @staticmethod
    def _accepted(entries, action):
        return tuple(
            entry for entry in entries if entry.action == action
        )

    @staticmethod
    def _latest_loss_and_open(losses, latest_open):
        if not losses or not latest_open:
            return ()
        if losses[-1].sequence >= latest_open[-1].sequence:
            return ()
        return (losses[-1], latest_open[-1])

    @staticmethod
    def _unique(entries):
        seen = set()
        unique = []
        for entry in entries:
            if entry.sequence in seen:
                continue
            seen.add(entry.sequence)
            unique.append(entry)
        return tuple(unique)

    @staticmethod
    def _fact_bool(entry, name, *, default=False):
        value = dict(entry.facts).get(name, default)
        return value if isinstance(value, bool) else default

    @staticmethod
    def _fact_number(entry, name):
        value = dict(entry.facts).get(name)
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            return 0.0
        return float(value)
