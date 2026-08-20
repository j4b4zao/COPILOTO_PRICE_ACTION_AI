"""
strategies/base_setup.py

Classe base para todos os Setups do
COPILOTO PRICE ACTION AI.

Todos os setups deverão herdar desta classe.
"""

from abc import ABC, abstractmethod

from ai.engine_base import EngineBase
from models.strategy_result import StrategyResult


class BaseSetup(EngineBase, ABC):

    NAME = ""

    VERSION = "1.0"

    PRIORITY = 100

    ENABLED = True

    MIN_SCORE = 70

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    @abstractmethod
    def executar(self, context) -> StrategyResult:
        """
        Executa o Setup.
        """
        pass

    # ==========================================================
    # ADICIONAR PONTOS
    # ==========================================================

    def add_points(

        self,

        result: StrategyResult,

        score: int,

        points: int,

        reason: str

    ) -> int:

        result.reasons.append(reason)

        return score + points

    # ==========================================================
    # FINALIZAR
    # ==========================================================

    def finalize(

        self,

        result: StrategyResult,

        score: int,

        direction: str

    ):

        result.name = self.NAME

        result.score = score

        result.confidence = score / 100

        result.direction = direction

        result.valid = score >= self.MIN_SCORE

    # ==========================================================
    # REPROVAR
    # ==========================================================

    def reject(

        self,

        result: StrategyResult,

        reason: str

    ):

        result.valid = False

        result.reasons.append(reason)

    # ==========================================================
    # APROVAR
    # ==========================================================

    def approve(

        self,

        result: StrategyResult,

        reason: str

    ):

        result.reasons.append(reason)