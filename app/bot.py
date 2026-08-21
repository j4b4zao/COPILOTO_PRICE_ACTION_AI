"""
app/bot.py

Controlador principal do
COPILOTO PRICE ACTION AI.

RC10 - OBSERVABILIDADE MULTI-TIMEFRAME
"""

import time

from core.system_initializer import SystemInitializer

from logs.logger import Logger
from monitor.multi_timeframe_monitor import MultiTimeframeMonitor


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

                self.connection.atualizar()

                context = self.collector.get_data()

                if context is None:

                    self.logger.warning(
                        "Aguardando dados do mercado..."
                    )

                    time.sleep(1)

                    continue

                context = self.pipeline.executar(context)

                self.mostrar(context)

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

        price_action = context.price_action

        order_block = context.order_block

        fair_value_gap = context.fair_value_gap

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

        print("\n" + "=" * 60)
        print(
            MultiTimeframeMonitor.render(
                context
            )
        )
        print("=" * 60)

        print("\n" + "=" * 60)
        print("SMART MONEY / CONFLUENCE DIAGNOSTIC")
        print("=" * 60)

        print("\nORDER BLOCK")
        print("------------")
        print(f"valid      : {order_block.valid}")
        print(f"bullish    : {order_block.bullish}")
        print(f"bearish    : {order_block.bearish}")
        print(f"mitigated  : {order_block.mitigated}")
        print(f"strength   : {order_block.strength}")
        print(f"score      : {order_block.score}")
        print(f"high       : {order_block.high}")
        print(f"low        : {order_block.low}")
        print(f"entry      : {order_block.entry_price}")

        print("\nFVG")
        print("------------")
        print(f"valid      : {fair_value_gap.valid}")
        print(f"bullish    : {fair_value_gap.bullish}")
        print(f"bearish    : {fair_value_gap.bearish}")
        print(f"filled     : {fair_value_gap.filled}")
        print(f"strength   : {fair_value_gap.strength}")
        print(f"score      : {fair_value_gap.score}")

        print("\nPRICE ACTION")
        print("------------")
        print(f"valid             : {price_action.valid}")
        print(f"bias              : {price_action.bias}")
        print(f"breakout          : {price_action.breakout}")
        print(f"pullback          : {price_action.pullback}")
        print(f"hammer            : {price_action.hammer}")
        print(f"shooting_star     : {price_action.shooting_star}")
        print(f"bullish_engulfing : {price_action.bullish_engulfing}")
        print(f"bearish_engulfing : {price_action.bearish_engulfing}")

        print("\nVOLUME")
        print("------------")
        print(f"valid      : {volume.valid}")
        print(f"low        : {volume.low}")
        print(f"medium     : {volume.medium}")
        print(f"high       : {volume.high}")

        print("\nLIQUIDITY")
        print("------------")
        print(f"valid      : {liquidity.valid}")
        print(f"buy_side   : {liquidity.buy_side}")
        print(f"sell_side  : {liquidity.sell_side}")
        print(f"sweep_up   : {liquidity.sweep_up}")
        print(f"sweep_down : {liquidity.sweep_down}")

        print("\nSTRUCTURE")
        print("------------")
        print(f"valid      : {structure.valid}")
        print(f"trend      : {structure.trend}")
        print(f"bos_up     : {structure.bos_up}")
        print(f"bos_down   : {structure.bos_down}")
        print(f"choch      : {structure.choch}")

        print("\nSTRATEGY")
        print("------------")
        print(f"valid      : {strategy.valid}")
        print(f"name       : {strategy.name}")
        print(f"signal     : {strategy.signal}")
        print(f"score      : {strategy.score}")

        print("=" * 60)
        print("END SMART MONEY DIAGNOSTIC")
        print("=" * 60)
