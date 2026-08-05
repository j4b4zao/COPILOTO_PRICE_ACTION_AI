"""
core/kernel.py

Kernel principal do Copiloto Price Action AI.
Responsável por controlar o ciclo de execução do sistema.
"""

import time

from core.settings import LOOP_MS
from logs.logger import logger


class Kernel:

    def __init__(
        self,
        collector,
        pipeline,
        monitor
    ):

        self.collector = collector
        self.pipeline = pipeline
        self.monitor = monitor

        self.loop = 0
        self.online = True

    # ==========================================================
    # LOOP PRINCIPAL
    # ==========================================================

    def executar(self):

        logger.titulo("COPILOTO PRICE ACTION AI")

        while self.online:

            self.loop += 1

            try:

                # ---------------------------------------------
                # Coleta
                # ---------------------------------------------

                market = self.collector.executar()

                # ---------------------------------------------
                # Pipeline
                # ---------------------------------------------

                market = self.pipeline.executar(market)

                # ---------------------------------------------
                # Monitor
                # ---------------------------------------------

                self.monitor.atualizar(
                    market,
                    self.pipeline.engine.obter_resultados()
                )

            except KeyboardInterrupt:

                logger.warning("Sistema encerrado pelo usuário.")
                self.online = False

            except Exception as erro:

                logger.erro(str(erro))

            time.sleep(LOOP_MS / 1000)

    # ==========================================================
    # PARAR
    # ==========================================================

    def parar(self):

        self.online = False