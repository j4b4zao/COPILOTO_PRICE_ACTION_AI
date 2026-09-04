"""Diario observacional encadeado para decisoes e revisoes de trading."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime


def _canonical(payload: dict) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class BookMethodologyJournalEntry:
    sequence: int
    decision_id: str
    recorded_at: str
    thesis: str
    invalidation: str
    disconfirming_evidence: tuple[str, ...]
    rule_violation_codes: tuple[str, ...]
    outcome_r: float | None
    violation_cost_r: float
    previous_hash: str | None
    entry_hash: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


@dataclass(frozen=True, slots=True)
class BookMethodologyJournalVerification:
    valid: bool
    entries: int
    first_invalid_sequence: int | None
    total_outcome_r: float
    total_violation_cost_r: float
    observational_only: bool = True
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class BookMethodologyJournal:
    NAME = "BookMethodologyJournal"
    VERSION = "RC1"

    @classmethod
    def append(
        cls,
        entries: tuple[BookMethodologyJournalEntry, ...],
        *,
        decision_id: str,
        recorded_at: datetime,
        thesis: str,
        invalidation: str,
        disconfirming_evidence: tuple[str, ...] = (),
        rule_violation_codes: tuple[str, ...] = (),
        outcome_r: float | None = None,
        violation_cost_r: float = 0.0,
    ) -> tuple[BookMethodologyJournalEntry, ...]:
        if not isinstance(entries, tuple):
            raise TypeError("entries deve ser tuple.")
        prior = cls.verify(entries)
        if not prior.valid:
            raise ValueError("nao e permitido anexar a uma cadeia invalida.")
        if not isinstance(recorded_at, datetime) or recorded_at.tzinfo is None:
            raise ValueError("recorded_at deve possuir timezone.")
        for name, value in (("decision_id", decision_id), ("thesis", thesis),
                            ("invalidation", invalidation)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} deve ser texto nao vazio.")
        for name, values in (("disconfirming_evidence", disconfirming_evidence),
                             ("rule_violation_codes", rule_violation_codes)):
            if not isinstance(values, tuple) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"{name} deve conter textos nao vazios.")
        if outcome_r is not None and not math.isfinite(float(outcome_r)):
            raise ValueError("outcome_r deve ser finito.")
        if not math.isfinite(float(violation_cost_r)) or violation_cost_r < 0:
            raise ValueError("violation_cost_r deve ser finito e nao negativo.")

        sequence = len(entries) + 1
        previous_hash = entries[-1].entry_hash if entries else None
        body = {
            "sequence": sequence,
            "decision_id": decision_id.strip(),
            "recorded_at": recorded_at.isoformat(),
            "thesis": thesis.strip(),
            "invalidation": invalidation.strip(),
            "disconfirming_evidence": list(disconfirming_evidence),
            "rule_violation_codes": list(dict.fromkeys(rule_violation_codes)),
            "outcome_r": None if outcome_r is None else float(outcome_r),
            "violation_cost_r": float(violation_cost_r),
            "previous_hash": previous_hash,
        }
        entry_hash = hashlib.sha256(_canonical(body)).hexdigest()
        entry_body = dict(body)
        entry_body["disconfirming_evidence"] = tuple(body["disconfirming_evidence"])
        entry_body["rule_violation_codes"] = tuple(body["rule_violation_codes"])
        return entries + (BookMethodologyJournalEntry(
            **entry_body, entry_hash=entry_hash
        ),)

    @classmethod
    def verify(
        cls, entries: tuple[BookMethodologyJournalEntry, ...]
    ) -> BookMethodologyJournalVerification:
        if not isinstance(entries, tuple):
            raise TypeError("entries deve ser tuple.")
        previous = None
        total_outcome = total_cost = 0.0
        first_invalid = None
        for expected, entry in enumerate(entries, 1):
            if not isinstance(entry, BookMethodologyJournalEntry):
                first_invalid = expected
                break
            raw = asdict(entry)
            claimed = raw.pop("entry_hash")
            for key in (
                "observational_only", "score_influence_allowed",
                "risk_influence_allowed", "decision_influence_allowed",
                "order_execution_allowed",
            ):
                raw.pop(key)
            raw["disconfirming_evidence"] = list(raw["disconfirming_evidence"])
            raw["rule_violation_codes"] = list(raw["rule_violation_codes"])
            valid = (
                entry.sequence == expected
                and entry.previous_hash == previous
                and hashlib.sha256(_canonical(raw)).hexdigest() == claimed
                and entry.observational_only is True
                and not any((entry.score_influence_allowed,
                             entry.risk_influence_allowed,
                             entry.decision_influence_allowed,
                             entry.order_execution_allowed))
            )
            if not valid:
                first_invalid = expected
                break
            previous = claimed
            total_outcome += entry.outcome_r or 0.0
            total_cost += entry.violation_cost_r
        return BookMethodologyJournalVerification(
            valid=first_invalid is None,
            entries=len(entries),
            first_invalid_sequence=first_invalid,
            total_outcome_r=total_outcome,
            total_violation_cost_r=total_cost,
        )
