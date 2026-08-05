"""
analysis/smart_money/smart_money_engine.py

Smart Money Engine

RC13

Classe base para todas as engines Smart Money
do COPILOTO PRICE ACTION AI.
"""

from __future__ import annotations

from abc import abstractmethod

from ai.engine_base import EngineBase
from core.analysis_context import AnalysisContext


class SmartMoneyEngine(EngineBase):

    NAME = "SmartMoneyEngine"

    VERSION = "RC13"

    PRIORITY = 30

    ENABLED = True

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(
        self,
        context: AnalysisContext,
    ) -> AnalysisContext:

        result = self.get_result(context)

        result.clear()

        if not self.validate_context(context):

            return context

        self.analyze(context)

        self.calculate_strength(context)

        self.calculate_score(context)

        self.finalize(context)

        return context

    # ==========================================================
    # RESULT
    # ==========================================================

    @abstractmethod
    def get_result(self, context):
        """
        Retorna o Result correspondente
        à engine.
        """
        raise NotImplementedError

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    def validate_context(
        self,
        context: AnalysisContext,
    ) -> bool:

        return context.structure.valid

    # ==========================================================
    # ANÁLISE
    # ==========================================================

    @abstractmethod
    def analyze(
        self,
        context: AnalysisContext,
    ):

        raise NotImplementedError

    # ==========================================================
    # FORÇA
    # ==========================================================

    def calculate_strength(
        self,
        context: AnalysisContext,
    ):

        pass

    # ==========================================================
    # SCORE
    # ==========================================================

    def calculate_score(
        self,
        context: AnalysisContext,
    ):

        result = self.get_result(context)

        result.score = min(

            result.strength,

            100,

        )

    # ==========================================================
    # FINALIZAÇÃO
    # ==========================================================

    def finalize(
        self,
        context: AnalysisContext,
    ):

        result = self.get_result(context)

        result.valid = result.score > 0