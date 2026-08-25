"""Coaching curto e contextual para Psicologia do Trader (RC3)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.trader_psychology_engine import TraderPsychologyResult


@dataclass(frozen=True, slots=True)
class CoachingPolicy:
    maximum_messages: int = 3
    maximum_message_characters: int = 160
    speak_pause_recommendation: bool = True

    def __post_init__(self):
        if not 1 <= self.maximum_messages <= 5:
            raise ValueError("maximum_messages deve ficar entre 1 e 5.")
        if not 80 <= self.maximum_message_characters <= 240:
            raise ValueError(
                "maximum_message_characters deve ficar entre 80 e 240."
            )
        if not isinstance(self.speak_pause_recommendation, bool):
            raise TypeError("speak_pause_recommendation deve ser booleano.")


@dataclass(frozen=True, slots=True)
class CoachingMessage:
    code: str
    text: str
    priority: int
    voice_candidate: bool


@dataclass(frozen=True, slots=True)
class CoachingResult:
    status: str
    messages: tuple[CoachingMessage, ...]
    source_signal_codes: tuple[str, ...]
    pause_recommended: bool
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class CoachingEngine:
    """Traduz sinais em orientação não julgadora; não dá sinal de trade."""

    NAME = "CoachingEngine"
    VERSION = "RC3"

    MESSAGE_BY_SIGNAL = {
        "REVENGE_TRADING": (
            "Reação após perda detectada. Respire e confirme o plano antes "
            "de considerar uma nova entrada."
        ),
        "STOP_SEQUENCE": (
            "Sequência de perdas identificada. Preserve o processo e revise "
            "o contexto com calma."
        ),
        "OVERTRADING": (
            "Frequência de operações elevada. Priorize qualidade e aguarde "
            "um contexto realmente claro."
        ),
        "RUSHED_REENTRY": (
            "A reentrada está muito próxima da última saída. Dê tempo para "
            "o mercado formar nova informação."
        ),
        "FOMO": (
            "Sinal de pressa identificado. Evite perseguir o preço e espere "
            "confirmação do seu plano."
        ),
        "OVERCONFIDENCE": (
            "Resultado positivo com aumento de mão. Mantenha o mesmo padrão "
            "de risco e disciplina."
        ),
        "OUTSIDE_PLAN": (
            "Checklist incompleto. Revise os critérios objetivos antes de "
            "considerar a entrada."
        ),
    }

    PRIORITY_BY_SIGNAL = {
        "REVENGE_TRADING": 100,
        "STOP_SEQUENCE": 95,
        "OUTSIDE_PLAN": 80,
        "OVERTRADING": 70,
        "RUSHED_REENTRY": 65,
        "OVERCONFIDENCE": 60,
        "FOMO": 50,
    }

    PAUSE_TEXT = (
        "Pausa recomendada. Afaste-se por alguns minutos, respire e retome "
        "somente após revisar seu plano."
    )

    FORBIDDEN_TRADING_WORDS = (
        "compre agora",
        "venda agora",
        "entre comprado",
        "entre vendido",
    )

    def __init__(self, *, policy=None):
        self.policy = policy or CoachingPolicy()

    def build(self, psychology_result):
        if not isinstance(psychology_result, TraderPsychologyResult):
            raise TypeError("psychology_result incompatível.")

        if not psychology_result.signals and not psychology_result.pause_recommended:
            return CoachingResult(
                status="SILENT",
                messages=(),
                source_signal_codes=(),
                pause_recommended=False,
            )

        messages = []
        if psychology_result.pause_recommended:
            messages.append(CoachingMessage(
                code="PAUSE_RECOMMENDED",
                text=self._safe_text(self.PAUSE_TEXT),
                priority=110,
                voice_candidate=self.policy.speak_pause_recommendation,
            ))

        ordered = sorted(
            psychology_result.signals,
            key=lambda signal: (
                -self.PRIORITY_BY_SIGNAL.get(signal.code, 0),
                signal.code,
            ),
        )
        seen = set()
        for signal in ordered:
            if signal.code in seen:
                continue
            text = self.MESSAGE_BY_SIGNAL.get(signal.code)
            if not text:
                continue
            messages.append(CoachingMessage(
                code=signal.code,
                text=self._safe_text(text),
                priority=self.PRIORITY_BY_SIGNAL[signal.code],
                voice_candidate=True,
            ))
            seen.add(signal.code)
            if len(messages) >= self.policy.maximum_messages:
                break

        messages = tuple(messages[: self.policy.maximum_messages])
        return CoachingResult(
            status=(
                "PAUSE_RECOMMENDED"
                if psychology_result.pause_recommended
                else "GUIDANCE"
            ),
            messages=messages,
            source_signal_codes=tuple(
                signal.code for signal in psychology_result.signals
            ),
            pause_recommended=psychology_result.pause_recommended,
        )

    def _safe_text(self, text):
        normalized = " ".join(str(text).split())
        lowered = normalized.casefold()
        if any(word in lowered for word in self.FORBIDDEN_TRADING_WORDS):
            raise ValueError("Mensagem de coaching contém comando operacional.")
        if len(normalized) > self.policy.maximum_message_characters:
            raise ValueError("Mensagem excede o limite configurado.")
        return normalized
