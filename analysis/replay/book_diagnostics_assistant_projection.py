"""
BookDiagnostics RC29 - Assistant/Dashboard Projection.

Transforma o snapshot readonly do RC28 em uma projecao amigavel para
operador, dashboard e futura camada de voz. Esta camada nao altera nenhuma
decisao do nucleo e somente resume informacoes ja recebidas pelos read models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class AssistantDashboardProjection:
    version: str
    headline: str
    market_summary: str
    context_summary: str
    checklist_summary: str
    evidence_summary: str
    caution_level: str
    voice_text: str
    evidence_count: int
    context_count: int
    checklist_count: int
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsAssistantProjector:
    VERSION = "RC29-ASSISTANT-DASHBOARD-PROJECTION"

    def build(self, receiver_or_snapshot) -> AssistantDashboardProjection:
        snapshot = self._snapshot(receiver_or_snapshot)
        self._validate(snapshot)

        evidence = dict(snapshot.get("evidence") or {})
        context = dict(snapshot.get("context") or {})
        checklist = dict(snapshot.get("checklist") or {})

        caution_level = self._caution_level(checklist)
        market_summary = self._market_summary(context)
        context_summary = self._context_summary(context)
        checklist_summary = self._checklist_summary(checklist)
        evidence_summary = self._evidence_summary(evidence)
        headline = self._headline(market_summary, caution_level)
        voice_text = self._voice_text(
            headline=headline,
            market_summary=market_summary,
            checklist_summary=checklist_summary,
            caution_level=caution_level,
        )

        return AssistantDashboardProjection(
            version=self.VERSION,
            headline=headline,
            market_summary=market_summary,
            context_summary=context_summary,
            checklist_summary=checklist_summary,
            evidence_summary=evidence_summary,
            caution_level=caution_level,
            voice_text=voice_text,
            evidence_count=len(evidence),
            context_count=len(context),
            checklist_count=len(checklist),
        )

    @staticmethod
    def _snapshot(value) -> dict:
        if hasattr(value, "snapshot"):
            return dict(value.snapshot())
        return dict(value or {})

    @staticmethod
    def _validate(snapshot: dict):
        if not bool(snapshot.get("readonly", False)):
            raise PermissionError("RC29 requires readonly RC28 snapshot")
        if bool(snapshot.get("affects_decision", True)):
            raise PermissionError("RC29 rejects decision-affecting snapshot")
        version = str(snapshot.get("version", "") or "")
        if version != "RC28-NON-INVASIVE-CORE-RECEIVERS":
            raise PermissionError("RC29 requires RC28 receiver snapshot")

    @staticmethod
    def _caution_level(checklist: dict) -> str:
        failed = [item for item in checklist.values() if not bool(item.get("passed", True))]
        if any(str(item.get("severity", "")).upper() == "BLOCK" for item in failed):
            return "HIGH"
        if any(str(item.get("severity", "")).upper() == "CAUTION" for item in failed):
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _market_summary(context: dict) -> str:
        if not context:
            return "Sem contexto experimental consolidado."
        preferred = (
            "market_environment",
            "trend_control",
            "reversal_pressure",
            "synthesis_state",
        )
        fragments = []
        for key in preferred:
            item = context.get(key)
            if item:
                state = str(item.get("state", "") or "").replace("_", " ").strip().lower()
                if state:
                    fragments.append(state)
        if not fragments:
            for item in context.values():
                state = str(item.get("state", "") or "").replace("_", " ").strip().lower()
                if state:
                    fragments.append(state)
                if len(fragments) >= 3:
                    break
        if not fragments:
            return "Contexto experimental disponivel, sem estado textual."
        return "; ".join(fragments[:4]).capitalize() + "."

    @staticmethod
    def _context_summary(context: dict) -> str:
        if not context:
            return "0 contextos ativos."
        parts = []
        for key, item in sorted(context.items()):
            state = str(item.get("state", "") or "").replace("_", " ")
            if state:
                parts.append(f"{key}: {state}")
        return "; ".join(parts) if parts else f"{len(context)} contextos ativos."

    @staticmethod
    def _checklist_summary(checklist: dict) -> str:
        if not checklist:
            return "Checklist experimental sem alertas."
        failed = [item for item in checklist.values() if not bool(item.get("passed", True))]
        if not failed:
            return f"Checklist experimental: {len(checklist)} itens, sem falhas."
        blocks = sum(1 for item in failed if str(item.get("severity", "")).upper() == "BLOCK")
        cautions = sum(1 for item in failed if str(item.get("severity", "")).upper() == "CAUTION")
        return f"Checklist experimental: {len(failed)} falhas, {blocks} bloqueios informativos e {cautions} cautelas."

    @staticmethod
    def _evidence_summary(evidence: dict) -> str:
        if not evidence:
            return "Sem evidencias experimentais ativas."
        strongest = sorted(
            evidence.items(),
            key=lambda pair: abs(float(pair[1].get("weighted_value", 0.0) or 0.0)),
            reverse=True,
        )[:3]
        parts = [
            f"{key}={float(item.get('weighted_value', 0.0) or 0.0):.3f}"
            for key, item in strongest
        ]
        return "Evidencias principais: " + ", ".join(parts) + "."

    @staticmethod
    def _headline(market_summary: str, caution_level: str) -> str:
        if caution_level == "HIGH":
            return "Contexto experimental exige cautela elevada."
        if caution_level == "MEDIUM":
            return "Contexto experimental pede cautela."
        if market_summary.startswith("Sem contexto"):
            return "Contexto experimental ainda insuficiente."
        return "Contexto experimental estavel para observacao."

    @staticmethod
    def _voice_text(*, headline: str, market_summary: str, checklist_summary: str, caution_level: str) -> str:
        if caution_level == "HIGH":
            prefix = "Atencao. "
        elif caution_level == "MEDIUM":
            prefix = "Cautela. "
        else:
            prefix = "Leitura atual. "
        return f"{prefix}{headline} {market_summary} {checklist_summary}"
