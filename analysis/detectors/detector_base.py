"""
Classe base para todos os detectores.
"""

from abc import ABC, abstractmethod


class DetectorBase(ABC):

    NAME = ""

    ENABLED = True

    VERSION = "RC15"

    @abstractmethod
    def detectar(self, context):
        """
        Executa a detecção.
        """
        pass