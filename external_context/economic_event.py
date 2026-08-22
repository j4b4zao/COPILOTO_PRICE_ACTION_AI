"""Contrato de evento do calendário econômico RC5.0."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EconomicEvent:

    title: str
    scheduled_at: datetime
    impact: str
    country: str = ""
    currency: str = ""
    category: str = ""
    forecast: str = ""
    previous: str = ""
    actual: str = ""
    source: str = "CONTROLLED"

    VALID_IMPACTS = frozenset({
        "LOW",
        "MEDIUM",
        "HIGH",
    })

    def __post_init__(self):
        title = str(self.title).strip()
        impact = str(self.impact).strip().upper()

        if not title:
            raise ValueError(
                "Evento econômico deve possuir título."
            )

        if not isinstance(self.scheduled_at, datetime):
            raise TypeError(
                "Horário do evento deve ser datetime."
            )

        if impact not in self.VALID_IMPACTS:
            raise ValueError(
                "Impacto deve ser LOW, MEDIUM ou HIGH."
            )

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "impact", impact)
        object.__setattr__(
            self,
            "country",
            str(self.country).strip().upper(),
        )
        object.__setattr__(
            self,
            "currency",
            str(self.currency).strip().upper(),
        )
        object.__setattr__(
            self,
            "category",
            str(self.category).strip().upper(),
        )
        object.__setattr__(
            self,
            "source",
            str(self.source).strip().upper() or "CONTROLLED",
        )
