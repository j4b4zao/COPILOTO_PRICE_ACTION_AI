"""
app/bot.py

Controlador principal do
COPILOTO PRICE ACTION AI.

RC9
"""

import time

from core.system_initializer import SystemInitializer

from logs.logger import Logger


class Bot:

    def __init__(self):

        self.logger = Logger()

        print("=" * 60)
        print("           COPILOTO PRICE ACTION AI")
        print("=" * 60)

        self.logger.info("Inicializando sistema...")

        # ======================================================
        # SISTEMA
        # ======================================================

        self.sistema = SystemInitializer().inicializar()

        # ======================================================
        # COMPONENTES
        # ======================================================

        self.connection = self.sistema.connection

        self.collector = self.sistema.collector

        self.pipeline = self.sistema.pipeline

        self.event_bus = self.sistema.event_bus

        self.monitor = self.sistema.monitor

        self.logger.sucesso("Sistema inicializado com sucesso.")

    # ==========================================================
    # LOOP PRINCIPAL
    # ==========================================================

    def executar(self):

        self.logger.info("COPILOTO PRICE ACTION AI ONLINE")

        while True:

            try:

                # ----------------------------------------------
                # Atualiza conexão
                # ----------------------------------------------

                self.connection.atualizar()

                # ----------------------------------------------
                # Coleta dados
                # ----------------------------------------------

                context = self.collector.get_data()

                if context is None:

                    self.logger.warning(
                        "Aguardando dados do mercado..."
                    )

                    time.sleep(1)

                    continue

                # ----------------------------------------------
                # Executa pipeline
                # ----------------------------------------------

                context = self.pipeline.executar(context)

                # ----------------------------------------------
                # Exibição
                # ----------------------------------------------

                self.mostrar(context)

                # Futuramente:
                #
                # self.monitor.show(context)
                #
                # ou
                #
                # EventBus -> DebugMonitor
                #

                time.sleep(1)

            except KeyboardInterrupt:

                self.logger.warning(
                    "Sistema encerrado pelo usuário."
                )

                break

            except Exception as erro:

                self.logger.erro(str(erro))

                time.sleep(1)

    # ==========================================================
    # EXIBIÇÃO TEMPORÁRIA
    # ==========================================================

    def mostrar(self, context):

        market = context.market

        structure = context.structure

        liquidity = context.liquidity

        volume = context.volume

        strategy = context.strategy

        score = context.score

        decision = context.decision

        print("\n" + "=" * 60)

        print(f"Ativo...........: {market.symbol}")
        print(f"TimeFrame.......: {market.timeframe}")
        print(f"Candles.........: {market.candle_count}")

        print(f"Preço...........: {market.last_price:.2f}")

        print(f"Tendência.......: {structure.trend}")

        print(f"BOS UP..........: {structure.bos_up}")
        print(f"BOS DOWN........: {structure.bos_down}")

        print(f"CHOCH...........: {structure.choch}")

        print(
            f"Liquidez........: "
            f"BUY={liquidity.buy_side}  "
            f"SELL={liquidity.sell_side}"
        )

        print(f"Volume Forte....: {volume.high}")

        print(f"Sinal...........: {strategy.signal}")

        print(f"Setup...........: {strategy.name}")

        print(f"Score...........: {score.total:.2f}")

        print(f"Grade...........: {score.grade}")

        print(f"Ação............: {decision.action}")

        print("=" * 60)