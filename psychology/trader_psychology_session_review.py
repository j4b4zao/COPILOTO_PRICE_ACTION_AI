"""Revisão não julgadora da sessão psicológica (RC23)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.trader_psychology_session_summary import (
    TraderPsychologySessionSummary,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologyReviewMessage:
    code: str
    text: str
    category: str


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionReview:
    status: str
    messages: tuple[TraderPsychologyReviewMessage, ...]
    source_total_cycles: int
    source_dominant_signal_code: str | None
    pause_recommended: bool = False
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologySessionReviewer:
    """Converte fatos agregados em reflexão, nunca em comando de trade."""

    NAME = "TraderPsychologySessionReviewer"
    VERSION = "RC23"

    DOMINANT_REFLECTIONS = {
        "FOMO": (
            "FOMO apareceu com maior frequência. Na revisão, identifique "
            "qual confirmação objetiva ainda não estava presente."
        ),
        "OUTSIDE_PLAN": (
            "Entradas fora do plano apareceram com maior frequência. "
            "Revise quais itens do checklist ficaram incompletos."
        ),
        "OVERTRADING": (
            "Frequência elevada apareceu mais vezes. Compare os contextos "
            "operados com os critérios mínimos do plano."
        ),
        "REVENGE_TRADING": (
            "Reação após perda apareceu mais vezes. Observe quais fatos "
            "mudaram entre a saída anterior e a nova entrada."
        ),
        "STOP_SEQUENCE": (
            "Sequência de perdas foi o padrão mais frequente. Revise o "
            "contexto comum às operações sem julgar o resultado isolado."
        ),
        "RUSHED_REENTRY": (
            "Reentrada apressada apareceu mais vezes. Observe se o mercado "
            "teve tempo de formar informação nova."
        ),
        "OVERCONFIDENCE": (
            "Aumento de confiança após resultados positivos apareceu mais "
            "vezes. Compare tamanho e critérios com o padrão do plano."
        ),
    }

    FORBIDDEN_TRADING_WORDS = (
        "compre agora",
        "venda agora",
        "entre comprado",
        "entre vendido",
    )

    def __init__(self, *, maximum_messages=4):
        if (
            isinstance(maximum_messages, bool)
            or not isinstance(maximum_messages, int)
        ):
            raise TypeError("maximum_messages deve ser inteiro.")
        if not 1 <= maximum_messages <= 6:
            raise ValueError(
                "maximum_messages deve ficar entre 1 e 6."
            )
        self.maximum_messages = maximum_messages

    def build(self, summary):
        if not isinstance(
            summary,
            TraderPsychologySessionSummary,
        ):
            raise TypeError(
                "summary deve ser "
                "TraderPsychologySessionSummary."
            )
        if summary.status == "EMPTY":
            return TraderPsychologySessionReview(
                status="EMPTY",
                messages=(),
                source_total_cycles=0,
                source_dominant_signal_code=None,
            )

        messages = []
        dominant = summary.dominant_signal_code
        dominant_text = self.DOMINANT_REFLECTIONS.get(dominant)
        if dominant_text:
            messages.append(self._message(
                code="DOMINANT_PATTERN",
                text=dominant_text,
                category="REFLECTION",
            ))
        else:
            messages.append(self._message(
                code="NO_RECURRING_SIGNAL",
                text=(
                    "Nenhum sinal psicológico recorrente foi registrado. "
                    "Mantenha a revisão factual do processo."
                ),
                category="PROCESS",
            ))

        if summary.pause_recommended_cycles:
            messages.append(self._message(
                code="PAUSE_REVIEW",
                text=(
                    f"Houve {summary.pause_recommended_cycles} ciclo(s) "
                    "com recomendação de pausa. Revise os fatos que "
                    "antecederam essas ocorrências."
                ),
                category="REFLECTION",
            ))

        if summary.linked_evidence_cycles:
            messages.append(self._message(
                code="EVIDENCE_COVERAGE",
                text=(
                    f"{summary.linked_evidence_cycles} de "
                    f"{summary.total_cycles} ciclo(s) possuem evidências "
                    "auditadas vinculadas."
                ),
                category="EVIDENCE",
            ))

        if summary.voice_failed_cycles:
            messages.append(self._message(
                code="VOICE_TECHNICAL",
                text=(
                    f"A voz falhou em {summary.voice_failed_cycles} "
                    "ciclo(s). Esse dado é técnico e não altera a análise."
                ),
                category="TECHNICAL",
            ))

        return TraderPsychologySessionReview(
            status="REFLECTION_AVAILABLE",
            messages=tuple(messages[: self.maximum_messages]),
            source_total_cycles=summary.total_cycles,
            source_dominant_signal_code=dominant,
        )

    def _message(self, *, code, text, category):
        normalized = " ".join(str(text).split())
        lowered = normalized.casefold()
        if any(
            forbidden in lowered
            for forbidden in self.FORBIDDEN_TRADING_WORDS
        ):
            raise ValueError(
                "Revisão contém comando operacional."
            )
        return TraderPsychologyReviewMessage(
            code=code,
            text=normalized,
            category=category,
        )
