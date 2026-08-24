"""Modelo normalizado de evento econômico.

RC1 mantém somente dados necessários para contexto observacional. Nenhum evento
gera ordem, sinal ou bloqueio operacional por conta própria.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EconomicEvent:
    title: str
    scheduled_at: datetime
    impact: str
    currency: str = ""
    country: str = ""
    source: str = "CONTROLLED"

    IMPACT_LEVELS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

    def __post_init__(self) -> None:
        title = str(self.title).strip()
        impact = str(self.impact).strip().upper()
        currency = str(self.currency).strip().upper()
        country = str(self.country).strip().upper()
        source = str(self.source).strip().upper()

        if not title:
            raise ValueError("EconomicEvent requer título válido.")
        if not isinstance(self.scheduled_at, datetime):
            raise TypeError("EconomicEvent requer scheduled_at datetime.")
        if self.scheduled_at.tzinfo is None:
            raise ValueError("EconomicEvent requer scheduled_at com fuso horário.")
        if impact not in self.IMPACT_LEVELS:
            raise ValueError("Impacto deve ser LOW, MEDIUM ou HIGH.")

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "impact", impact)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "country", country)
        object.__setattr__(self, "source", source or "CONTROLLED")

    @property
    def impact_level(self) -> int:
        return self.IMPACT_LEVELS[self.impact]
