"""
Classe base para todas as estratégias.
"""

from abc import ABC, abstractmethod


class Strategy(ABC):

    def __init__(self):

        self.name = self.__class__.__name__

    @abstractmethod
    def analyze(self, context):

        """
        Retorna True caso a estratégia encontre um setup.
        """
        pass