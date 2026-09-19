"""Bridge historico passivo RC54.3.2 -> Microstructure RC2.

Responsabilidade:
- aceitar somente samples RC54.3.2 historicamente elegiveis;
- preservar Price Action e Market Structure capturados;
- usar RC35_SIGNED_DELTA para a direcao observacional do Order Flow;
- preservar somente evidencia de Book realmente disponivel;
- nunca fabricar momentum, pattern ou BookDepth Level 2 ausentes;
- executar MicrostructureConfluenceAudit + EligibilityPolicy em shadow;
- nunca alterar Score, Risk, Decision, Alert ou execucao.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from types import SimpleNamespace

from analysis.replay.microstructure_confluence import (
    MicrostructureConfluenceAudit,
)
from analysis.replay.microstructure_eligibility_policy import (
    MicrostructureEligibilityPolicy,
)


@dataclass(slots=True, frozen=True)
class HistoricalMicrostructureBridgeResult:
    cycle: int
    timestamp: str
    source_alignment: str
    price_action_bias: str
    structure_trend: str
    recent_delta: float
    dominance: float
    imbalance: float
    order_flow_pressure: str
    book_pressure: str
    confluence: dict
    eligibility: dict
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class HistoricalMicrostructureBridge:
    VERSION = "RC1-HISTORICAL-MICROSTRUCTURE-BRIDGE"
    DIRECTION_LOGIC_VERSION = "RC35_SIGNED_DELTA"

    DELTA_THRESHOLD = 0.35
    BOOK_THRESHOLD = 0.10

    def __init__(self) -> None:
        self._confluence = MicrostructureConfluenceAudit()
        self._eligibility = MicrostructureEligibilityPolicy()

    @staticmethod
    def eligible(sample: dict) -> bool:
        return bool(
            sample.get("data_ready") is True
            and sample.get("context_ready") is True
            and sample.get("delta_status") == "VALID"
            and sample.get("book_status") == "VALID"
            and isinstance(sample.get("price_action"), dict)
            and isinstance(sample.get("structure"), dict)
        )

    def analyze(self, sample: dict) -> HistoricalMicrostructureBridgeResult:
        if not self.eligible(sample):
            raise ValueError(
                "Sample RC54.3.2 nao elegivel para bridge historico."
            )

        pa = sample["price_action"]
        structure = sample["structure"]

        pa_bias = str(pa.get("bias", "NONE") or "NONE").upper()
        structure_trend = str(
            structure.get("trend", "UNKNOWN") or "UNKNOWN"
        ).upper()

        recent_delta = self._float(sample.get("recent_delta"))
        dominance = abs(self._float(sample.get("dominance")))
        imbalance = self._float(sample.get("imbalance"))

        order_flow_pressure = self._order_flow_pressure(
            recent_delta=recent_delta,
            dominance=dominance,
        )

        book_pressure = self._book_pressure(imbalance)

        context = SimpleNamespace(
            price_action=SimpleNamespace(
                bias=pa_bias,
            ),
            structure=SimpleNamespace(
                trend=structure_trend,
            ),
            order_flow=SimpleNamespace(
                pressure=order_flow_pressure,

                # Nao reconstruiveis com fidelidade a partir do
                # snapshot historico RC54.3.2.
                flow_momentum="INSUFFICIENT_DATA",
                pattern_direction="NONE",
                structure_alignment="UNAVAILABLE",
                structural_pattern_confidence=0.0,
            ),
            book_depth_analysis=SimpleNamespace(
                # Existe evidencia agregada de imbalance, mas nao
                # Level 2 suficiente para reconstruir BookDepthAnalysis.
                valid=book_pressure != "BALANCED",
                pressure=book_pressure,
                concentration_bias="BALANCED",

                # Sem concentracao top-N e spread normalizado historicos,
                # nao fabricamos confianca.
                confidence=0.0,

                # O imbalance usado no RC54 participa da mesma camada
                # observacional Delta/Book; conservadoramente tratamos
                # como potencialmente correlato.
                duplicate_evidence_risk=True,
            ),
        )

        confluence = self._confluence.analyze(context)
        eligibility = self._eligibility.evaluate(confluence)

        return HistoricalMicrostructureBridgeResult(
            cycle=int(sample.get("cycle", 0) or 0),
            timestamp=str(sample.get("timestamp", "") or ""),
            source_alignment=str(
                sample.get("alignment", "NEUTRAL") or "NEUTRAL"
            ).upper(),
            price_action_bias=pa_bias,
            structure_trend=structure_trend,
            recent_delta=recent_delta,
            dominance=dominance,
            imbalance=imbalance,
            order_flow_pressure=order_flow_pressure,
            book_pressure=book_pressure,
            confluence=confluence.to_dict(),
            eligibility=eligibility.to_dict(),
        )

    @classmethod
    def _order_flow_pressure(
        cls,
        *,
        recent_delta: float,
        dominance: float,
    ) -> str:
        if dominance < cls.DELTA_THRESHOLD:
            return "BALANCED"
        if recent_delta > 0:
            return "BUY"
        if recent_delta < 0:
            return "SELL"
        return "BALANCED"

    @classmethod
    def _book_pressure(cls, imbalance: float) -> str:
        if imbalance >= cls.BOOK_THRESHOLD:
            return "BID_DOMINANT"
        if imbalance <= -cls.BOOK_THRESHOLD:
            return "ASK_DOMINANT"
        return "BALANCED"

    @staticmethod
    def _float(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
