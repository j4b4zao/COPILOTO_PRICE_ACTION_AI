"""
price_action/setups/base_setup.py

Classe base para todos os setups do Copiloto.
"""

from abc import ABC, abstractmethod


class BaseSetup(ABC):

    def __init__(self):

        self.nome = self.__class__.__name__

    @abstractmethod
    def executar(self, market):
        """
        Executa o setup.
        Deve retornar um dicionário.
        """
        raise NotImplementedError

    # ==========================================================
    # RESULTADO PADRÃO
    # ==========================================================

    def resultado(self):

        return {

            "valido": False,

            "nome": "NENHUM",

            "lado": "NEUTRO",

            "score": 0,

            "classe": "SEM_SETUP",

            "motivos": []

        }

    # ==========================================================
    # CLASSIFICAÇÃO
    # ==========================================================

    def classificar(self, score):

        if score >= 95:
            return "A+"

        if score >= 85:
            return "A"

        if score >= 75:
            return "B"

        if score >= 65:
            return "C"

        return "SEM_SETUP"