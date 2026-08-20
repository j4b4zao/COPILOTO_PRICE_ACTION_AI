"""
analysis/detectors/pullback_detector.py

Primeiro detector operacional do
COPILOTO PRICE ACTION AI.

RC15
"""

from analysis.detectors.detector_base import DetectorBase

from models.strategy_result import StrategyResult


class PullbackDetector(DetectorBase):

    NAME = "Pullback Institucional"

    VERSION = "RC15"

    PRIORITY = 100

    def detectar(self, context):

        result = StrategyResult()

        result.name = self.NAME

        result.priority = self.PRIORITY

        # -----------------------------------------------------
        # Regras mínimas da RC15
        # -----------------------------------------------------

        if not context.checklist.trend:
            result.add_reason("Tendência não confirmada.")
            return result

        if not context.checklist.structure:
            result.add_reason("Estrutura não confirmada.")
            return result

        if not context.checklist.volume:
            result.add_reason("Volume não confirma.")
            return result

        if not context.checklist.liquidity:
            result.add_reason("Liquidez insuficiente.")
            return result

        if not context.checklist.context:
            result.add_reason("Contexto desfavorável.")
            return result

        # -----------------------------------------------------
        # Pullback encontrado
        # -----------------------------------------------------

        result.validate()

        result.signal = "BUY"

        result.score = 70

        result.classify()

        result.add_reason(
            "Todos os critérios mínimos do Pullback foram atendidos."
        )

        return result