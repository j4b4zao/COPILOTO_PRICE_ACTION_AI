"""
market_data/collector.py

Coleta dados do Profit Pro através do Excel,
alimenta M1/M5/M15, oferece mercado NORMAL ou RENKO
e retorna AnalysisContext.

RC12 - CHART MODE / RENKO
"""

import math

from connectors.profit_reader import ProfitReader

from core.analysis_context import AnalysisContext
from core.market_clock import MarketClock
from core.multi_timeframe_state import MultiTimeframeState
from core.order_flow_state import OrderFlowState
from core.renko_state import RenkoState
from enums.chart_mode import ChartMode


class Collector:

    NAME = "Collector"
    VERSION = "RC12-CHART-MODE"

    def __init__(
        self,
        excel=None,
        reader=None,
        multi_timeframe=None,
        renko_state=None,
        order_flow_state=None,
        chart_mode=None,
        renko_brick_size=None,
        clock=None,
    ):

        # ======================================================
        # EXCEL
        # ======================================================

        if excel is None:

            # Import tardio: mantém xlwings restrito ao caminho
            # de produção e permite testes offline por injeção.
            from connectors.excel_connector import (
                ExcelConnector,
            )

            excel = ExcelConnector()

        self.excel = excel

        self.reader = (
            reader
            if reader is not None
            else ProfitReader(self.excel)
        )

        # ======================================================
        # MERCADO
        # ======================================================

        from config.settings import (
            CHART_MODE,
            RENKO_BRICK_SIZE,
        )

        self.chart_mode = ChartMode.normalize(
            chart_mode
            if chart_mode is not None
            else CHART_MODE
        )

        brick_size = (
            renko_brick_size
            if renko_brick_size is not None
            else RENKO_BRICK_SIZE
        )

        self.multi_timeframe = (
            multi_timeframe
            if multi_timeframe is not None
            else MultiTimeframeState()
        )

        self.renko = (
            renko_state
            if renko_state is not None
            else RenkoState(
                brick_size=brick_size
            )
        )

        self.order_flow = (
            order_flow_state
            if order_flow_state is not None
            else OrderFlowState()
        )

        self.market = self._primary_market()

        self.last_new_candles = {
            timeframe: False
            for timeframe
            in self.multi_timeframe.TIMEFRAMES
        }

        self.last_closed_renko_bricks = 0

        self.clock = (
            clock
            if clock is not None
            else MarketClock
        )

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

        ativo = str(
            dados.get("ativo") or ""
        ).strip()

        if not ativo:

            print(
                "[DATA WARNING] "
                "Ativo inválido recebido. "
                "Leitura ignorada."
            )

            return None

        close = self.to_float(
            dados.get("close")
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
        # TIMESTAMP
        # ======================================================

        timestamp = self.clock.now()

        aggression_buy = self.to_optional_float(
            dados.get("agressao_compra")
        )
        aggression_sell = self.to_optional_float(
            dados.get("agressao_venda")
        )

        if aggression_buy is None or aggression_sell is None:
            self.order_flow.mark_unavailable()
        else:
            self.order_flow.update(
                cumulative_buy=aggression_buy,
                cumulative_sell=aggression_sell,
                price=close,
            )

        # ======================================================
        # MULTI-TIMEFRAME
        # ======================================================

        self.last_new_candles = (
            self.multi_timeframe.update_tick(
                symbol=ativo,
                price=close,
                cumulative_volume=volume,
                timestamp=timestamp,
            )
        )

        if self.chart_mode == ChartMode.RENKO:

            self.last_closed_renko_bricks = (
                self.renko.update_tick(
                    symbol=ativo,
                    price=close,
                    cumulative_volume=volume,
                    timestamp=timestamp,
                )
            )

        candle = self.market.last_candle

        # ======================================================
        # CANDLE DEBUG
        # ======================================================

        print(
            "[CANDLE DEBUG] "
            f"time={timestamp} "
            f"period={candle.timestamp if candle else None} "
            f"new={self.last_new_candles} "
            f"price={close:.2f} "
            f"cumulative_volume={volume:.2f} "
            f"candle_volume={candle.volume if candle else None} "
            f"history="
            f"M1:{self.multi_timeframe.get('M1').candle_count},"
            f"M5:{self.multi_timeframe.get('M5').candle_count},"
            f"M15:{self.multi_timeframe.get('M15').candle_count} "
            f"chart_mode={self.chart_mode.value} "
            f"primary={self.market.timeframe} "
            f"renko_bricks={self.renko.market.candle_count}"
        )

        # ======================================================
        # ANALYSIS CONTEXT
        # ======================================================

        context = AnalysisContext(
            market=self.market,
            multi_timeframe=self.multi_timeframe,
            order_flow_state=self.order_flow,
        )

        return context

    # ==========================================================
    # GRÁFICO PRINCIPAL
    # ==========================================================

    def _primary_market(self):

        if self.chart_mode == ChartMode.RENKO:

            return self.renko.market

        return self.multi_timeframe.primary

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

    @staticmethod
    def to_optional_float(value):

        if value is None:
            return None

        if isinstance(value, (int, float)):
            converted = float(value)
        else:
            try:
                text = str(value).strip()
                if not text:
                    return None
                converted = float(
                    text.replace(".", "").replace(",", ".")
                )
            except (TypeError, ValueError):
                return None

        if not math.isfinite(converted) or converted < 0:
            return None

        return converted
