"""
market_data/collector.py

Collector RC7

Responsável por:

- Ler dados do Profit
- Validar dados
- Construir candles
- Atualizar o MarketState
- Retornar o AnalysisContext
"""

from connectors.excel_connector import ExcelConnector
from connectors.profit_reader import ProfitReader

from config.settings import EXCEL_PATH

from core.analysis_context import AnalysisContext
from core.data_validator import DataValidator
from core.market_clock import MarketClock
from core.candle_builder import CandleBuilder


class Collector:

    NAME = "Collector"

    VERSION = "RC7"

    def __init__(self):

        self.excel = ExcelConnector()

        if not self.excel.conectar(EXCEL_PATH):

            raise RuntimeError(
                f"Não foi possível conectar ao Excel.\n"
                f"Arquivo esperado:\n{EXCEL_PATH}"
            )

        self.reader = ProfitReader(self.excel)

        self.context = AnalysisContext()

        self.builder = CandleBuilder()

    # ==========================================================
    # Conversão segura
    # ==========================================================

    @staticmethod
    def to_float(valor):

        if valor is None:
            return 0.0

        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()

        if not texto:
            return 0.0

        # Ex.: "12345/ABC"
        if "/" in texto:
            texto = texto.split("/")[0].strip()

        texto = texto.replace(".", "")
        texto = texto.replace(",", ".")

        try:
            return float(texto)

        except ValueError:
            return 0.0

    # ==========================================================
    # COLETA
    # ==========================================================

    def get_data(self):

        dados = self.reader.obter_dados()

        if not dados:
            return None

        symbol = dados.get("ativo", "")

        timeframe = dados.get("timeframe", "M1")

        open_price = self.to_float(dados.get("open"))
        high = self.to_float(dados.get("high"))
        low = self.to_float(dados.get("low"))
        close = self.to_float(dados.get("close"))
        volume = self.to_float(dados.get("volume"))

        # ------------------------------------------------------
        # Validação
        # ------------------------------------------------------

        if not DataValidator.validate(
            symbol,
            open_price,
            high,
            low,
            close,
            volume,
        ):
            return None

        timestamp = MarketClock.now()

        # ------------------------------------------------------
        # Candle Builder
        # ------------------------------------------------------

        candle, novo_candle = self.builder.update(
            open_price=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp,
        )

        # ------------------------------------------------------
        # Atualiza MarketState
        # ------------------------------------------------------

        self.context.market.update(
            candle=candle,
            symbol=symbol,
            timeframe=timeframe,
            volume=volume,
            timestamp=timestamp,
        )

        # ------------------------------------------------------
        # Limpa resultados da análise anterior
        # ------------------------------------------------------

        self.context.clear_results()

        # ------------------------------------------------------
        # Futuras evoluções (RC8+)
        # ------------------------------------------------------
        #
        # if novo_candle:
        #     self.context.market.close_candle()
        #
        # self.context.market.tick_count += 1
        #
        # self.context.market.spread = ...
        #
        # self.context.market.book = ...
        #
        # self.context.market.times_trades = ...
        #
        # ------------------------------------------------------

        return self.context