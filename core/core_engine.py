"""
core/core_engine.py

Motor principal do pipeline do Copiloto Price Action AI.
"""

from time import perf_counter

from core.module_result import ModuleResult
from logs.logger import logger


class CoreEngine:

    def __init__(self):

        self.modulos = []

        self.resultados = []

    # ==========================================================
    # REGISTRAR MÓDULO
    # ==========================================================

    def registrar(self, modulo):

        self.modulos.append(modulo)

    # ==========================================================
    # EXECUTAR PIPELINE
    # ==========================================================

    def executar(self, market):

        self.resultados.clear()

        for modulo in self.modulos:

            if not getattr(modulo, "ativo", True):
                continue

            inicio = perf_counter()

            try:

                market = modulo.executar(market)

                tempo = (perf_counter() - inicio) * 1000

                self.resultados.append(

                    ModuleResult(
                        nome=modulo.nome,
                        sucesso=True,
                        tempo_ms=tempo
                    )

                )

                logger.debug(
                    f"{modulo.nome} executado ({tempo:.2f} ms)"
                )

            except Exception as erro:

                tempo = (perf_counter() - inicio) * 1000

                self.resultados.append(

                    ModuleResult(
                        nome=modulo.nome,
                        sucesso=False,
                        tempo_ms=tempo,
                        erro=str(erro)
                    )

                )

                logger.erro(
                    f"{modulo.nome}: {erro}"
                )

        return market

    # ==========================================================
    # RESULTADOS
    # ==========================================================

    def obter_resultados(self):

        return self.resultados