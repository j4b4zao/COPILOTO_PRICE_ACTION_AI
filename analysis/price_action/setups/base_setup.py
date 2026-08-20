"""
strategies/base_setup.py

Classe base para todos os setups do
COPILOTO PRICE ACTION AI.

Todos os setups devem herdar desta classe.
"""

from abc import ABC, abstractmethod

from ai.engine_base import EngineBase
from models.strategy_result import StrategyResult


class BaseSetup(EngineBase, ABC):

    # ==========================================================
    # CONFIGURAÇÃO
    # ==========================================================

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
        Método obrigatório de todos os setups.
        """
        pass

    # ==========================================================
    # VALIDAÇÕES COMUNS
    # ==========================================================

    def validate_context(self, checklist):

        return checklist.context

    def validate_structure(self, structure):

        return structure.valid

    def validate_volume(self, volume):

        return volume.valid

    def validate_liquidity(self, liquidity):

        return liquidity.valid

    # ==========================================================
    # SCORE
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
    # REPROVAR
    # ==========================================================

    def reject(

        self,

        result: StrategyResult,

        reason: str

    ) -> StrategyResult:

        result.valid = False

        result.reasons.append(reason)

        return result

    # ==========================================================
    # FINALIZAR
    # ==========================================================

    def finalize(

        self,

        result: StrategyResult,

        score: int,

        direction: str

    ) -> StrategyResult:

        result.name = self.NAME

        result.score = score

        result.confidence = score / 100

        result.direction = direction

        result.valid = score >= self.MIN_SCORE

        return result