"""
strategies/setups/setup_base.py

Classe base para todos os setups.

RC4
"""

from abc import ABC, abstractmethod

from models.strategy_result import StrategyResult


class SetupBase(ABC):

    NAME = "Setup"

    VERSION = "RC4"

    ENABLED = True

    PRIORITY = 100

    @abstractmethod
    def executar(self, context) -> StrategyResult:
        """
        Executa o setup.

        Retorna um StrategyResult.
        """
        raise NotImplementedError