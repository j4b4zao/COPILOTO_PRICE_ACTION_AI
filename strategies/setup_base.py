"""
strategies/setup_base.py

Classe base para todos os setups.

RC4
"""

from abc import ABC, abstractmethod


class SetupBase(ABC):

    NAME = "SetupBase"

    VERSION = "RC4"

    ENABLED = True

    PRIORITY = 100

    @abstractmethod
    def executar(self, context):
        """
        Executa o setup.

        Retorna:
            StrategyResult
        """
        raise NotImplementedError