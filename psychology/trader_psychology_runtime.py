"""Runtime consolidado da Psicologia do Trader (RC5)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.coaching_engine import CoachingEngine, CoachingResult
from psychology.trader_psychology_engine import (
    TraderPsychologyEngine,
    TraderPsychologyResult,
)
from psychology.trader_psychology_state import TraderPsychologyState
from psychology.voice_assistant import (
    VoiceAssistant,
    VoiceAssistantResult,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologyRuntimeResult:
    status: str
    state: TraderPsychologyState
    psychology: TraderPsychologyResult
    coaching: CoachingResult
    voice: VoiceAssistantResult
    pause_recommended: bool
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologyRuntime:
    """Executa State → Engine → Coaching → Voice fora do núcleo operacional."""

    NAME = "TraderPsychologyRuntime"
    VERSION = "RC5"

    def __init__(
        self,
        *,
        psychology_engine=None,
        coaching_engine=None,
        voice_assistant=None,
    ):
        self.psychology_engine = (
            psychology_engine or TraderPsychologyEngine()
        )
        self.coaching_engine = coaching_engine or CoachingEngine()
        self.voice_assistant = voice_assistant or VoiceAssistant()

        if not callable(getattr(self.psychology_engine, "analyze", None)):
            raise TypeError("psychology_engine deve expor analyze().")
        if not callable(getattr(self.coaching_engine, "build", None)):
            raise TypeError("coaching_engine deve expor build().")
        if not callable(getattr(self.voice_assistant, "dispatch", None)):
            raise TypeError("voice_assistant deve expor dispatch().")

        self.last_result = None

    def process(self, state):
        if not isinstance(state, TraderPsychologyState):
            raise TypeError("state deve ser TraderPsychologyState.")

        psychology = self.psychology_engine.analyze(state)
        if not isinstance(psychology, TraderPsychologyResult):
            raise TypeError("psychology_engine retornou resultado incompatível.")

        coaching = self.coaching_engine.build(psychology)
        if not isinstance(coaching, CoachingResult):
            raise TypeError("coaching_engine retornou resultado incompatível.")

        voice = self.voice_assistant.dispatch(coaching)
        if not isinstance(voice, VoiceAssistantResult):
            raise TypeError("voice_assistant retornou resultado incompatível.")

        if psychology.pause_recommended:
            status = "PAUSE_RECOMMENDED"
        elif psychology.signals:
            status = "ATTENTION"
        else:
            status = "NEUTRAL"

        self.last_result = TraderPsychologyRuntimeResult(
            status=status,
            state=state,
            psychology=psychology,
            coaching=coaching,
            voice=voice,
            pause_recommended=psychology.pause_recommended,
        )
        return self.last_result
