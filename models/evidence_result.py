"""
models/evidence_result.py

Resultado produzido pelo EvidenceEngine.

Centraliza todas as evidências encontradas pelas
engines do COPILOTO PRICE ACTION AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.result_base import ResultBase


@dataclass(slots=True)
class EvidenceResult(ResultBase):
    """
    Resultado consolidado das evidências.
    """

    evidences: list[str] = field(default_factory=list)

    score: float = 0.0

    confidence: float = 0.0

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def add(self, evidence: str):

        if evidence not in self.evidences:

            self.evidences.append(evidence)

    def has(self, evidence: str) -> bool:

        return evidence in self.evidences

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.evidences.clear()

        self.score = 0.0

        self.confidence = 0.0