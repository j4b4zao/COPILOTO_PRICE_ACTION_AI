"""
Historical Microstructure Confluence Report RC1.

Consolida resultados produzidos pelo HistoricalMicrostructureBridge.

Objetivos:
- medir alinhamento PA + Order Flow;
- medir alinhamento PA + Book;
- medir alinhamento PA + Order Flow + Book;
- medir conflitos;
- medir ausência de evidência;
- preservar separação entre evidência independente e correlacionada.

Este módulo é exclusivamente observacional.

Não altera:
- Score;
- Risk;
- Decision;
- Alert;
- execução de ordens.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable, Any


@dataclass(slots=True)
class HistoricalMicrostructureConfluenceReport:
    version: str

    samples: int

    pa_flow_aligned: int
    pa_book_aligned: int
    pa_flow_book_aligned: int

    pa_flow_conflict: int
    pa_book_conflict: int

    flow_book_aligned: int
    flow_book_conflict: int

    confirmed: int
    conflict: int
    insufficient_data: int

    independent_evidence: dict
    correlated_evidence: dict
    conflict_counts: dict

    eligibility: dict
    eligibility_reasons: dict

    order_flow_pressure: dict
    book_pressure: dict

    observational_only: bool = True
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    alert_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class HistoricalMicrostructureConfluenceReporter:

    VERSION = "RC1-HISTORICAL-MICROSTRUCTURE-CONFLUENCE-REPORT"

    @staticmethod
    def _direction(value: Any) -> str:
        value = str(value or "").upper()

        if value in {"BUY", "BID_DOMINANT"}:
            return "BUY"

        if value in {"SELL", "ASK_DOMINANT"}:
            return "SELL"

        return "NONE"

    def build(
        self,
        results: Iterable[Any],
    ) -> HistoricalMicrostructureConfluenceReport:

        samples = 0

        pa_flow_aligned = 0
        pa_book_aligned = 0
        pa_flow_book_aligned = 0

        pa_flow_conflict = 0
        pa_book_conflict = 0

        flow_book_aligned = 0
        flow_book_conflict = 0

        confluence_states = Counter()

        independent = Counter()
        correlated = Counter()
        conflicts = Counter()

        eligibility = Counter()
        eligibility_reasons = Counter()

        order_flow_pressure = Counter()
        book_pressure = Counter()

        for result in results:

            samples += 1

            pa = self._direction(
                getattr(result, "price_action_bias", "NONE")
            )

            flow = self._direction(
                getattr(result, "order_flow_pressure", "NONE")
            )

            book = self._direction(
                getattr(result, "book_pressure", "NONE")
            )

            order_flow_pressure[
                str(getattr(result, "order_flow_pressure", "NONE"))
            ] += 1

            book_pressure[
                str(getattr(result, "book_pressure", "NONE"))
            ] += 1

            if pa != "NONE" and flow != "NONE":
                if pa == flow:
                    pa_flow_aligned += 1
                else:
                    pa_flow_conflict += 1

            if pa != "NONE" and book != "NONE":
                if pa == book:
                    pa_book_aligned += 1
                else:
                    pa_book_conflict += 1

            if flow != "NONE" and book != "NONE":
                if flow == book:
                    flow_book_aligned += 1
                else:
                    flow_book_conflict += 1

            if (
                pa != "NONE"
                and flow != "NONE"
                and book != "NONE"
                and pa == flow == book
            ):
                pa_flow_book_aligned += 1

            confluence = getattr(result, "confluence", {}) or {}
            eligible = getattr(result, "eligibility", {}) or {}

            state = str(
                confluence.get("state", "UNKNOWN")
            )

            confluence_states[state] += 1

            independent[
                int(
                    confluence.get(
                        "independent_evidence_count",
                        0,
                    )
                )
            ] += 1

            correlated[
                int(
                    confluence.get(
                        "correlated_evidence_count",
                        0,
                    )
                )
            ] += 1

            conflicts[
                int(
                    confluence.get(
                        "conflict_count",
                        0,
                    )
                )
            ] += 1

            eligibility[
                str(eligible.get("state", "UNKNOWN"))
            ] += 1

            eligibility_reasons[
                str(eligible.get("reason", "UNKNOWN"))
            ] += 1

        return HistoricalMicrostructureConfluenceReport(
            version=self.VERSION,

            samples=samples,

            pa_flow_aligned=pa_flow_aligned,
            pa_book_aligned=pa_book_aligned,
            pa_flow_book_aligned=pa_flow_book_aligned,

            pa_flow_conflict=pa_flow_conflict,
            pa_book_conflict=pa_book_conflict,

            flow_book_aligned=flow_book_aligned,
            flow_book_conflict=flow_book_conflict,

            confirmed=confluence_states["CONFIRMED"],
            conflict=confluence_states["CONFLICT"],
            insufficient_data=confluence_states[
                "INSUFFICIENT_DATA"
            ],

            independent_evidence=dict(
                sorted(independent.items())
            ),

            correlated_evidence=dict(
                sorted(correlated.items())
            ),

            conflict_counts=dict(
                sorted(conflicts.items())
            ),

            eligibility=dict(eligibility),
            eligibility_reasons=dict(
                eligibility_reasons
            ),

            order_flow_pressure=dict(
                order_flow_pressure
            ),

            book_pressure=dict(
                book_pressure
            ),

            observational_only=True,
            score_influence_allowed=False,
            risk_influence_allowed=False,
            decision_influence_allowed=False,
            alert_influence_allowed=False,
            order_execution_allowed=False,
        )
