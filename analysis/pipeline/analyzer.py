"""
analysis/pipeline/analyzer.py

Classe base para todos os módulos de análise.
"""

from abc import ABC, abstractmethod


class Analyzer(ABC):

    @abstractmethod
    def executar(self, market):
        """
        Executa uma etapa da análise.

        Deve retornar sempre o objeto MarketData.
        """
        pass