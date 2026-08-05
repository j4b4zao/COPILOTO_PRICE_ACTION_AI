"""
core/base_module.py

Classe base para todos os módulos do COPILOTO.
"""

from abc import ABC, abstractmethod


class BaseModule(ABC):

    def __init__(self, name: str):

        self.name = name
        self.enabled = True

    def enable(self):

        self.enabled = True

    def disable(self):

        self.enabled = False

    @abstractmethod
    def executar(self, context):
        """
        Executa o módulo.
        """
        pass