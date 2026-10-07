"""
Replay Historical Input Contract

RC5 - HISTORICAL CAUSAL INPUT CONTRACT

Contrato passivo para declarar quais domínios históricos estão disponíveis
em cada instante do Replay.

Este módulo:
- não executa Strategy, Score, Risk ou Decision;
- não reconstrói MTF ou Order Flow;
- não consulta rede, relógio ou serviços externos;
- não aceita observações posteriores ao candle corrente;
- representa ausência explicitamente como UNAVAILABLE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"

VALID_STATUSES = frozenset({
    AVAILABLE,
    UNAVAILABLE,
})

HISTORICAL_DOMAINS = (
    "MTF",
    "ORDER_FLOW",
    "EXTERNAL",
    "ECONOMIC_CALENDAR",
    "BOOK_DEPTH",
)


@dataclass(frozen=True, slots=True)
class HistoricalDomainObservation:
    domain: str
    status: str
    observed_at: datetime | None = None
    source: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        domain = str(self.domain).strip().upper()
        status = str(self.status).strip().upper()
        source = str(self.source).strip().upper()
        reason = str(self.reason).strip().upper()

        if domain not in HISTORICAL_DOMAINS:
            raise ValueError(
                f"Domínio histórico inválido: {domain!r}."
            )

        if status not in VALID_STATUSES:
            raise ValueError(
                f"Status histórico inválido: {status!r}."
            )

        if (
            self.observed_at is not None
            and type(self.observed_at) is not datetime
        ):
            raise TypeError(
                "observed_at deve ser datetime ou None."
            )

        if status == AVAILABLE:
            if self.observed_at is None:
                raise ValueError(
                    "Domínio AVAILABLE requer observed_at."
                )

            if not source:
                raise ValueError(
                    "Domínio AVAILABLE requer source."
                )

        if status == UNAVAILABLE and self.observed_at is not None:
            raise ValueError(
                "Domínio UNAVAILABLE não deve possuir observed_at."
            )

        object.__setattr__(self, "domain", domain)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "reason", reason)

    @property
    def available(self) -> bool:
        return self.status == AVAILABLE

    def validate_as_of(
        self,
        candle_timestamp: datetime,
    ) -> None:
        if type(candle_timestamp) is not datetime:
            raise TypeError(
                "candle_timestamp deve ser datetime."
            )

        if not self.available:
            return

        try:
            future = self.observed_at > candle_timestamp
        except TypeError as exc:
            raise ValueError(
                "observed_at e candle_timestamp possuem "
                "semântica temporal incompatível."
            ) from exc

        if future:
            raise ValueError(
                f"{self.domain} contém observação futura: "
                f"{self.observed_at!r} > {candle_timestamp!r}."
            )


@dataclass(frozen=True, slots=True)
class ReplayHistoricalInput:
    candle_timestamp: datetime
    mtf: HistoricalDomainObservation
    order_flow: HistoricalDomainObservation
    external: HistoricalDomainObservation
    economic_calendar: HistoricalDomainObservation
    book_depth: HistoricalDomainObservation

    def __post_init__(self) -> None:
        if type(self.candle_timestamp) is not datetime:
            raise TypeError(
                "ReplayHistoricalInput requer candle_timestamp datetime."
            )

        observations = self.observations

        expected = HISTORICAL_DOMAINS

        actual = tuple(
            observation.domain
            for observation in observations
        )

        if actual != expected:
            raise ValueError(
                "Domínios históricos não correspondem "
                "ao contrato RC5."
            )

        for observation in observations:
            observation.validate_as_of(
                self.candle_timestamp
            )

    @property
    def observations(
        self,
    ) -> tuple[HistoricalDomainObservation, ...]:
        return (
            self.mtf,
            self.order_flow,
            self.external,
            self.economic_calendar,
            self.book_depth,
        )

    @property
    def available_domains(self) -> tuple[str, ...]:
        return tuple(
            observation.domain
            for observation in self.observations
            if observation.available
        )

    @property
    def unavailable_domains(self) -> tuple[str, ...]:
        return tuple(
            observation.domain
            for observation in self.observations
            if not observation.available
        )

    def status_for(
        self,
        domain: str,
    ) -> str:
        normalized = str(domain).strip().upper()

        for observation in self.observations:
            if observation.domain == normalized:
                return observation.status

        raise ValueError(
            f"Domínio histórico inválido: {normalized!r}."
        )

    @classmethod
    def unavailable(
        cls,
        candle_timestamp: datetime,
        *,
        reason: str = "HISTORICAL_DATA_NOT_PROVIDED",
    ) -> "ReplayHistoricalInput":
        normalized_reason = (
            str(reason).strip().upper()
            or "HISTORICAL_DATA_NOT_PROVIDED"
        )

        def missing(
            domain: str,
        ) -> HistoricalDomainObservation:
            return HistoricalDomainObservation(
                domain=domain,
                status=UNAVAILABLE,
                reason=normalized_reason,
            )

        return cls(
            candle_timestamp=candle_timestamp,
            mtf=missing("MTF"),
            order_flow=missing("ORDER_FLOW"),
            external=missing("EXTERNAL"),
            economic_calendar=missing(
                "ECONOMIC_CALENDAR"
            ),
            book_depth=missing("BOOK_DEPTH"),
        )