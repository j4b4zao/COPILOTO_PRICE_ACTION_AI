"""
market_data/collector.py

Coleta dados do Profit Pro através do Excel
e transforma os dados em AnalysisContext.

RC10
"""

import math

from connectors.excel_connector import ExcelConnector
from connectors.profit_reader import ProfitReader

from core.candle_builder import CandleBuilder
from core.market_state import MarketState

from core.analysis_context import AnalysisContext

from core.market_clock import MarketClock


class Collector:

    NAME = "Collector"
    VERSION = "RC10"

    def __init__(self):

        # ======================================================
        # EXCEL
        # ======================================================

        self.excel = ExcelConnector()

        self.reader = ProfitReader(
            self.excel
        )

        # ======================================================
        # MERCADO
        # ======================================================

        self.market = MarketState()

        self.candle_builder = CandleBuilder()

        # ======================================================
        # CONEXÃO
        # ======================================================

        from config.settings import EXCEL_PATH

        if not self.excel.conectar(EXCEL_PATH):

            raise RuntimeError(
                "Não foi possível conectar ao Excel."
            )

    # ==========================================================
    # COLETAR DADOS
    # ==========================================================

    def get_data(self):

        dados = self.reader.obter_dados()

        if not dados:

            return None

        # ======================================================
        # VOLUME DEBUG
        # ======================================================

        raw_volume = dados.get(
            "volume"
        )

        volume = self.to_float(
            raw_volume
        )

        print(
            "[VOLUME DEBUG] "
            f"raw={raw_volume!r} "
            f"converted={volume}"
        )

        # ======================================================
        # DADOS BÁSICOS
        # ======================================================

        ativo = dados.get(
            "ativo"
        )

        close = self.to_float(
            dados.get("close")
        )

        open_price = self.to_float(
            dados.get("open")
        )

        high = self.to_float(
            dados.get("high")
        )

        low = self.to_float(
            dados.get("low")
        )

        # ======================================================
        # VALIDAÇÃO DO PREÇO
        # ======================================================

        if not math.isfinite(close) or close <= 0:

            print(
                "[DATA WARNING] "
                f"Preço inválido recebido: {close!r}. "
                "Leitura ignorada."
            )

            return None

        # ======================================================
        # VALIDAÇÃO DO VOLUME
        # ======================================================

        if not math.isfinite(volume) or volume < 0:

            print(
                "[DATA WARNING] "
                f"Volume inválido recebido: {volume!r}. "
                "Volume será tratado como 0.0."
            )

            volume = 0.0

        # ======================================================
        # TIMEFRAME
        # ======================================================

        timeframe = dados.get(
            "timeframe",
            "M1"
        )

        if not timeframe:

            timeframe = "M1"

        # ======================================================
        # TIMESTAMP
        # ======================================================

        timestamp = MarketClock.now()

        # ======================================================
        # CANDLE BUILDER
        # ======================================================

        candle, new_candle = (
            self.candle_builder.update(

                open_price=open_price,

                high=high,

                low=low,

                close=close,

                volume=volume,

                timeframe=timeframe,

                timestamp=timestamp,

            )
        )

        # ======================================================
        # CANDLE DEBUG
        # ======================================================

        print(
            "[CANDLE DEBUG] "
            f"time={timestamp} "
            f"period={candle.timestamp if candle else None} "
            f"new={new_candle} "
            f"price={close:.2f} "
            f"cumulative_volume={volume:.2f} "
            f"candle_volume={candle.volume if candle else None} "
            f"history_before={self.market.candle_count}"
        )

        # ======================================================
        # MARKET STATE
        # ======================================================

        self.market.update(

            candle=candle,

            symbol=ativo,

            timeframe=timeframe,

            volume=volume,

            timestamp=timestamp,

            new_candle=new_candle,

        )

        # ======================================================
        # CANDLE HISTORY DEBUG
        # ======================================================

        print(
            "[CANDLE DEBUG] "
            f"history_after={self.market.candle_count}"
        )

        # ======================================================
        # ANALYSIS CONTEXT
        # ======================================================

        context = AnalysisContext(
            market=self.market
        )

        return context

    # ==========================================================
    # CONVERSÃO
    # ==========================================================

    @staticmethod
    def to_float(value):

        if value is None:

            return 0.0

        if isinstance(
            value,
            (int, float)
        ):

            return float(value)

        try:

            value = str(
                value
            ).strip()

            if not value:

                return 0.0

            value = value.replace(
                ".",
                ""
            )

            value = value.replace(
                ",",
                "."
            )

            return float(
                value
            )

        except (
            ValueError,
            TypeError
        ):

            return 0.0