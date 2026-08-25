"""Apresentação auditável de evidências no coaching e na voz (RC15)."""

from __future__ import annotations

from dataclasses import replace

from psychology.trader_psychology_evidence_correlator import (
    PsychologyEvidenceLink,
    TraderPsychologyEvidenceReport,
)
from psychology.trader_psychology_runtime import (
    TraderPsychologyRuntimeResult,
)


class TraderPsychologyEvidencePresenter:
    """Anota resultados já produzidos sem reenviar voz nem alterar operações."""

    NAME = "TraderPsychologyEvidencePresenter"
    VERSION = "RC15"

    def enrich(self, runtime_result, evidence_report):
        if not isinstance(
            runtime_result,
            TraderPsychologyRuntimeResult,
        ):
            raise TypeError(
                "runtime_result deve ser TraderPsychologyRuntimeResult."
            )
        if not isinstance(
            evidence_report,
            TraderPsychologyEvidenceReport,
        ):
            raise TypeError(
                "evidence_report deve ser TraderPsychologyEvidenceReport."
            )

        coaching_messages = tuple(
            self._enrich_message(message, evidence_report.links)
            for message in runtime_result.coaching.messages
        )
        deliveries = tuple(
            self._enrich_delivery(delivery, evidence_report.links)
            for delivery in runtime_result.voice.deliveries
        )

        coaching = replace(
            runtime_result.coaching,
            messages=coaching_messages,
        )
        voice = replace(
            runtime_result.voice,
            deliveries=deliveries,
        )
        return replace(
            runtime_result,
            coaching=coaching,
            voice=voice,
            evidence=evidence_report,
        )

    def _enrich_message(self, message, links):
        matched = self._matching_links(message.code, links)
        return replace(
            message,
            evidence_linked=bool(matched),
            evidence_audit_sequences=self._sequences(matched),
            evidence_trade_ids=self._trade_ids(matched),
        )

    def _enrich_delivery(self, delivery, links):
        matched = self._matching_links(delivery.code, links)
        return replace(
            delivery,
            evidence_linked=bool(matched),
            evidence_audit_sequences=self._sequences(matched),
            evidence_trade_ids=self._trade_ids(matched),
        )

    @staticmethod
    def _matching_links(code, links):
        if code == "PAUSE_RECOMMENDED":
            return tuple(
                link for link in links if link.source_kind == "PAUSE"
            )
        return tuple(
            link
            for link in links
            if link.source_kind == "SIGNAL" and link.code == code
        )

    @staticmethod
    def _sequences(links):
        return tuple(
            dict.fromkeys(
                sequence
                for link in links
                for sequence in link.audit_sequences
            )
        )

    @staticmethod
    def _trade_ids(links):
        return tuple(
            dict.fromkeys(
                trade_id
                for link in links
                for trade_id in link.trade_ids
            )
        )
