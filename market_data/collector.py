"""Coleta Profit/Excel com integridade, diagnóstico, qualidade e recorder de Delta."""

import math

from connectors.profit_reader import ProfitReader
from core.analysis_context import AnalysisContext
from core.market_clock import MarketClock
from core.multi_timeframe_state import MultiTimeframeState
from core.order_flow_state import OrderFlowState
from core.renko_state import RenkoState
from enums.chart_mode import ChartMode
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator
from market_data.profit_delta_session_recorder import ProfitDeltaSessionRecorder
from market_data.profit_delta_source_diagnostics import ProfitDeltaSourceDiagnostics
from market_data.profit_source_integrity import ProfitSourceIntegrityGuard
from market_data.profit_rtd_validation_recorder import ProfitRTDValidationRecorder


class Collector:
    NAME = "Collector"
    VERSION = "RC18-PROFIT-RTD-VALIDATION-OBSERVABILITY"

    def __init__(self, excel=None, reader=None, multi_timeframe=None, renko_state=None,
                 order_flow_state=None, chart_mode=None, renko_brick_size=None, clock=None,
                 source_guard=None, source_diagnostics=None, delta_quality_validator=None,
                 delta_session_recorder=None, enable_profit_rtd_order_flow=None,
                 profit_rtd_order_flow_pipeline=None, profit_rtd_validation_recorder=None):
        if excel is None:
            from connectors.excel_connector import ExcelConnector
            excel = ExcelConnector()
        self.excel = excel
        self.reader = reader if reader is not None else ProfitReader(self.excel)

        from config.settings import (
            CHART_MODE,
            ENABLE_PROFIT_RTD_ORDER_FLOW,
            EXCEL_PATH,
            RENKO_BRICK_SIZE,
        )

        self.chart_mode = ChartMode.normalize(
            chart_mode if chart_mode is not None else CHART_MODE
        )
        brick_size = renko_brick_size if renko_brick_size is not None else RENKO_BRICK_SIZE
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
        self.delta_quality_validator = (
            delta_quality_validator
            if delta_quality_validator is not None
            else ProfitDeltaQualityValidator()
        )
        self.delta_session_recorder = (
            delta_session_recorder
            if delta_session_recorder is not None
            else ProfitDeltaSessionRecorder()
        )
        self.profit_rtd_validation_recorder = (
            profit_rtd_validation_recorder
            if profit_rtd_validation_recorder is not None
            else ProfitRTDValidationRecorder()
        )
        self.last_delta_quality = self.delta_quality_validator.evaluate(
            self.order_flow,
            self.source_diagnostics.snapshot,
        )
        self.market = self._primary_market()
        self.last_new_candles = {
            timeframe: False for timeframe in self.multi_timeframe.TIMEFRAMES
        }
        self.last_closed_renko_bricks = 0
        self.clock = clock if clock is not None else MarketClock

        self.enable_profit_rtd_order_flow = bool(
            ENABLE_PROFIT_RTD_ORDER_FLOW
            if enable_profit_rtd_order_flow is None
            else enable_profit_rtd_order_flow
        )
        self.profit_rtd_order_flow_pipeline = profit_rtd_order_flow_pipeline
        self.last_profit_rtd_receipt = None

        if not self.excel.conectar(EXCEL_PATH):
            raise RuntimeError("Não foi possível conectar ao Excel.")

        if self.enable_profit_rtd_order_flow and self.profit_rtd_order_flow_pipeline is None:
            self.profit_rtd_order_flow_pipeline = self._build_profit_rtd_order_flow_pipeline()

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

        if self.enable_profit_rtd_order_flow:
            self.last_profit_rtd_receipt = self.profit_rtd_order_flow_pipeline.process(
                ativo,
                price=close,
            )
            self.profit_rtd_validation_recorder.record(self.last_profit_rtd_receipt)
            diagnostic_buy = self.order_flow.cumulative_buy
            diagnostic_sell = self.order_flow.cumulative_sell
            validation = self.profit_rtd_validation_recorder.snapshot
            print(
                "[PROFIT RTD VALIDATION] "
                f"cycles={validation.total_cycles} updates={validation.state_updates} "
                f"new_trades={validation.total_new_trades} resets={validation.baseline_resets} "
                f"continuity={validation.continuity_rate:.0%} "
                f"last={validation.last_continuity}"
            )
        else:
            diagnostic_buy = aggression_buy
            diagnostic_sell = aggression_sell
            if integrity.symbol_changed:
                self.order_flow.clear()

        if integrity.duplicate:
            if not self.enable_profit_rtd_order_flow:
                if aggression_buy is None or aggression_sell is None:
                    self.order_flow.mark_unavailable()
                else:
                    self.order_flow.mark_waiting("SOURCE_UNCHANGED")
            self._observe_delta_source(integrity, diagnostic_buy, diagnostic_sell)
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

        if not self.enable_profit_rtd_order_flow:
            self._update_order_flow(
                aggression_buy=aggression_buy,
                aggression_sell=aggression_sell,
                price=close,
            )

        self._observe_delta_source(integrity, diagnostic_buy, diagnostic_sell)

        candle = self.market.last_candle
        print(
            "[CANDLE DEBUG] "
            f"time={timestamp} period={candle.timestamp if candle else None} "
            f"new={self.last_new_candles} price={close:.2f} cumulative_volume={volume:.2f} "
            f"candle_volume={candle.volume if candle else None} "
            f"history=M1:{self.multi_timeframe.get('M1').candle_count},"
            f"M5:{self.multi_timeframe.get('M5').candle_count},"
            f"M15:{self.multi_timeframe.get('M15').candle_count} "
            f"chart_mode={self.chart_mode.value} primary={self.market.timeframe} "
            f"renko_bricks={self.renko.market.candle_count} "
            f"order_flow_source={'PROFIT_RTD_TT' if self.enable_profit_rtd_order_flow else 'LEGACY'}"
        )

        return AnalysisContext(
            market=self.market,
            multi_timeframe=self.multi_timeframe,
            order_flow_state=self.order_flow,
        )

    def _build_profit_rtd_order_flow_pipeline(self):
        from market_data.excel_range_gateway import ExcelRangeGateway
        from market_data.profit_rtd_order_flow_pipeline import ProfitRTDOrderFlowPipeline
        from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader

        gateway = ExcelRangeGateway(self.excel)
        reader = ProfitRTDTimesTradesReader(gateway)
        return ProfitRTDOrderFlowPipeline(reader, self.order_flow)

    def _observe_delta_source(self, integrity, aggression_buy, aggression_sell):
        self.source_diagnostics.observe(
            integrity=integrity,
            aggression_buy=aggression_buy,
            aggression_sell=aggression_sell,
            order_flow=self.order_flow,
        )
        source = self.source_diagnostics.snapshot
        self.last_delta_quality = self.delta_quality_validator.evaluate(
            self.order_flow,
            source,
        )
        quality = self.last_delta_quality
        self.delta_session_recorder.record(source, quality)
        print(
            "[DELTA SOURCE] "
            f"status={source.status} symbol={source.symbol} fresh={source.fresh_snapshots} "
            f"duplicates={source.duplicate_snapshots} aggression={source.aggression_availability_rate:.0%} "
            f"samples={source.order_flow_samples} resets={source.accumulator_resets} "
            f"symbol_changes={source.symbol_changes}"
        )
        print(
            "[DELTA QUALITY] "
            f"status={quality.status} samples={quality.sample_count} delta={quality.recent_delta:.2f} "
            f"dominance={quality.dominance:.2f} persistence={quality.persistence:.2f} "
            f"avg_abs={quality.average_abs_delta:.2f} max_abs={quality.max_abs_delta:.2f} "
            f"zero_rate={quality.zero_delta_rate:.0%} anomalies={quality.anomaly_count} "
            f"reasons={','.join(quality.reasons) if quality.reasons else 'OK'}"
        )

    def delta_session_summary(self) -> dict:
        return self.delta_session_recorder.summary()

    def profit_rtd_validation_summary(self) -> dict:
        return self.profit_rtd_validation_recorder.snapshot.to_dict()

    def _primary_market(self):
        return (
            self.renko.market
            if self.chart_mode == ChartMode.RENKO
            else self.multi_timeframe.primary
        )

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
