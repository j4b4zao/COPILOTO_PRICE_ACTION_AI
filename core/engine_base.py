"""
# LEGACY - DO NOT USE

Legacy EngineBase retained temporarily for migration compatibility.

Classe base de todas as engines do
COPILOTO PRICE ACTION AI.
"""

from abc import ABC, abstractmethod
from time import perf_counter


class EngineBase(ABC):

    NAME = "Engine"

    VERSION = "RC2"

    ENABLED = True

    PRIORITY = 100

    def __init__(self):

        self.last_execution = 0.0

    # ==========================================================
    # EXECUÇÃO DA ENGINE
    # ==========================================================

    @abstractmethod
    def executar(self, context):
        """
        Método obrigatório implementado por todas as engines.
        """
        pass

    # ==========================================================
    # EXECUÇÃO COM MEDIÇÃO DE TEMPO
    # ==========================================================

    def execute(self, context):

        inicio = perf_counter()

        context = self.executar(context)

        fim = perf_counter()

        self.last_execution = (fim - inicio) * 1000

        return context
