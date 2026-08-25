"""Ponte observacional da Psicologia para AnalysisContext (RC6)."""

from __future__ import annotations

from psychology.trader_psychology_runtime import (
    TraderPsychologyRuntimeResult,
)


class TraderPsychologyContextBridge:
    """Anexa/limpa somente o slot trader_psychology do contexto."""

    NAME = "TraderPsychologyContextBridge"
    VERSION = "RC6"

    def attach(self, context, runtime_result):
        self._context(context)
        if not isinstance(
            runtime_result,
            TraderPsychologyRuntimeResult,
        ):
            raise TypeError("runtime_result incompatível.")
        context.trader_psychology = runtime_result
        return context

    def clear(self, context):
        self._context(context)
        context.trader_psychology = None
        return context

    @staticmethod
    def _context(context):
        if context is None or not hasattr(context, "trader_psychology"):
            raise TypeError(
                "context deve expor slot trader_psychology."
            )
