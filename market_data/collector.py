"""
market_data/collector.py

Coleta dados do Profit Pro através do Excel, alimenta M1/M5/M15,
oferece mercado NORMAL ou RENKO e retorna AnalysisContext.

RC14 - PROFIT DELTA SOURCE DIAGNOSTICS
"""

import math

from connectors.profit_reader import ProfitReader
from core.analysis_context import AnalysisContext
from core.market_clock import MarketClock
from core.multi_timeframe_state import MultiTimeframeState
from core.order_flow_state import OrderFlowState
from core.renko_state import RenkoState
from enums.chart_mode import ChartMode
from market_data.profit_delta_source_diagnostics import ProfitDeltaSourceDiagnostics
from market_data.profit_source_integrity import ProfitSourceIntegrityGuard


class Collector:
    NAME = "Collector"
    VERSION = "RC14-PROFIT-DELTA-SOURCE-DIAGNOSTICS"

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
        source_guard=None,
        source_diagnostics=None,
    ):
        if excel is None:
            from connectors.excel_connector import ExcelConnector
            excel = ExcelConnector()

        self.excel = excel
        self.reader = reader if reader is not None else ProfitReader(self.excel)

        from config.settings import CHART_MODE, RENKO_BRICK_SIZE

        self.chart_mode = ChartMode.normalize(
            chart_mode if chart_mode is not None else CHART_MODE
        )
        brick_size = (
            renko_brick_size if renko_brick_size is not None else RENKO_BRICK_SIZE
        )
        self.multi_timeframe = (
            multi_timeframe if multi_timeframe is not None else MultiTimeframeState()
        )
        self.renko = (
            renko_state if renko_state is not None else RenkoState(brick_size=brick_size)
        )
        self.order_flow = (
            order_flow_state if order_flow_state is not None else OrderFlowState()
        )
        self.source_guard = (
            source_guard if source_guard is not None else ProfitSourceIntegrityGuard()
        )
        self.source_diagnostics = (
            source_diagnostics
            if source_diagnostics is not None
            else ProfitDeltaSourceDiagnostics()
        )
        self.market = self._primary_market()
        self.last_new_candles = {
            timeframe: False for timeframe in self.multi_timeframe.TIMEFRAMES
        }
        self.last_closed_renko_bricks = 0
        self.clock = clock if clock is not None else MarketClock

        from config.settings import EXCEL_PATH
        if not self.excel.conectar(EXCEL_PATH):
            raise RuntimeError("Não foi possível conectar ao Excel.")

    def get_data(self):
        dados = self.reader.obter_dados()
        if not dados:
            return None

        raw_volume = dados.get("volume")
        volume = self.to_float(raw_volume)
        print(f"[VOLUME DEBUG] raw={raw_volume!r} converted={volume}")

        ativo = str(dados.get("ativo") or "").strip()
        if not ativo:
            print("[DATA WARNING] Ativo inválido recebido. Leitura ignorada.")
            return None

        close = self.to_float(dados.get("close"))
        if not math.isfinite(close) or close <= 0:
            print(f"[DATA WARNING] Preço inválido recebido: {close!r}. Leitura ignorada.")
            return None

        if not math.isfinite(volume) or volume < 0:
            print(
                f"[DATA WARNING] Volume inválido recebido: {volume!r}. "
                "Volume será tratado como 0.0."
            )
            volume = 0.0

        aggression_buy = self.to_optional_float(dados.get("agressao_compra"))
        aggression_sell = self.to_optional_float(dados.get("agressao_venda"))

        integrity = self.source_guard.inspect(dados)
        if integrity.symbol_changed:
            self.order_flow.clear()

        if integrity.duplicate:
            if aggression_buy is None or aggression_sell is None:
                self.order_flow.mark_unavailable()
            else:
                self.order_flow.mark_waiting("SOURCE_UNCHANGED")
            self.source_diagnostics.observe(
                integrity=integrity,
                aggression_buy=aggression_buy,
                aggression_sell=aggression_sell,
                order_flow=self.order_flow,
            )
            print("[DATA WAIT] Snapshot do Profit sem mudança; ciclo ignorado.")
            return None

        timestamp = self.clock.now()

        self.last_new_candles = self.multi_timeframe.update_tick(
            symbol=ativo,
            price=close,
            cumulative_volume=volume,
            timestamp=timestamp,
        )

        if self.chart_mode == ChartMode.RENKO:
            self.last_closed_renko_bricks = self.renko.update_tick(
                symbol=ativo,
                price=close,
                cumulative_volume=volume,
                timestamp=timestamp,
            )

        self._update_order_flow(
            aggression_buy=aggression_buy,
            aggression_sell=aggression_sell,
            price=close,
        )

        self.source_diagnostics.observe(
            integrity=integrity,
            aggression_buy=aggression_buy,
            aggression_sell=aggression_sell,
            order_flow=self.order_flow,
        )

        candle = self.market.last_candle
        print(
            "[CANDLE DEBUG] "
            f"time={timestamp} "
            f"period={candle.timestamp if candle else None} "
            f"new={self.last_new_candles} "
            f"price={close:.2f} "
            f"cumulative_volume={volume:.2f} "
            f"candle_volume={candle.volume if candle else None} "
            f"history=M1:{self.multi_timeframe.get('M1').candle_count},"
            f"M5:{self.multi_timeframe.get('M5').candle_count},"
            f"M15:{self.multi_timeframe.get('M15').candle_count} "
            f"chart_mode={self.chart_mode.value} "
            f"primary={self.market.timeframe} "
            f"renko_bricks={self.renko.market.candle_count}"
        )

        return AnalysisContext(
            market=self.market,
            multi_timeframe=self.multi_timeframe,
            order_flow_state=self.order_flow,
        )

    def _primary_market(self):
        if self.chart_mode == ChartMode.RENKO:
            return self.renko.market
        return self.multi_timeframe.primary

    def _update_order_flow(self, *, aggression_buy, aggression_sell, price):
        if aggression_buy is None or aggression_sell is None:
            self.order_flow.mark_unavailable()
            return

        if self.chart_mode == ChartMode.NORMAL:
            self.order_flow.update(
                cumulative_buy=aggression_buy,
                cumulative_sell=aggression_sell,
                price=price,
                sampling_mode="TICK",
                source_units=1,
            )
            return

        if self.order_flow.cumulative_buy is None:
            self.order_flow.update(
                cumulative_buy=aggression_buy,
                cumulative_sell=aggression_sell,
                price=price,
                sampling_mode="RENKO_CLOSE",
                source_units=0,
            )
            return

        if self.last_closed_renko_bricks <= 0:
            self.order_flow.mark_waiting("RENKO_CLOSE")
            return

        self.order_flow.update(
            cumulative_buy=aggression_buy,
            cumulative_sell=aggression_sell,
            price=price,
            sampling_mode="RENKO_CLOSE",
            source_units=self.last_closed_renko_bricks,
        )

    @staticmethod
    def to_float(value):
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            text = str(value).strip()
            if not text:
                return 0.0
            return float(text.replace(".", "").replace(",", "."))
        except (ValueError, TypeError):
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
                converted = float(text.replace(".", "").replace(",", "."))
            except (TypeError, ValueError):
                return None
        if not math.isfinite(converted) or converted < 0:
            return None
        return converted
