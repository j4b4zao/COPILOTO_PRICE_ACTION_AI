"""
core/module.py

Classe base para todos os módulos do COPILOTO PRICE ACTION AI.
"""


class Module:

    def executar(self, market):
        """
        Executa o módulo.

        Todos os módulos do sistema deverão implementar
        este método.

        Sempre retorna MarketData.
        """
        return market