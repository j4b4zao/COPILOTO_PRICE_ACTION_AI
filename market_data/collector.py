"""Coleta Profit/Excel com integridade, diagnóstico, qualidade e recorder de Delta."""

import logging
import math
import sys
from copy import copy, deepcopy
from datetime import datetime, timezone, tzinfo
from threading import Lock

from analysis.temporal_snapshot_policy import (
    TemporalSnapshotHistory,
    TemporalSnapshotPolicy,
    primary_quote_source_timestamp,
    validate_primary_quote_timestamp,
)
from connectors.profit_reader import ProfitQuoteIncompleteRange, ProfitReader
from core.analysis_context import AnalysisContext
from core.market_clock import MarketClock
from core.multi_timeframe_state import MultiTimeframeState
from core.order_flow_state import OrderFlowState
from core.renko_state import RenkoState
from enums.chart_mode import ChartMode
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator
from market_data.profit_delta_session_recorder import ProfitDeltaSessionRecorder
from market_data.profit_delta_source_diagnostics import ProfitDeltaSourceDiagnostics
from market_data.profit_rtd_order_flow_pipeline import ProfitRTDOrderFlowPipeline
from market_data.profit_source_integrity import ProfitSourceIntegrityGuard
from market_data.profit_rtd_validation_recorder import ProfitRTDValidationRecorder


logger = logging.getLogger(__name__)


_PROTECTED_CYCLE_STATE = (
    "market", "multi_timeframe", "renko", "order_flow", "source_guard",
    "source_diagnostics", "delta_quality_validator", "delta_session_recorder",
    "profit_rtd_validation_recorder", "_temporal_primary_history",
)


class Collector:
    NAME = "Collector"
    VERSION = "RC25-PROFIT-RTD-VOLUME-HOLD"

    def __init__(self, excel=None, reader=None, multi_timeframe=None, renko_state=None,
                 order_flow_state=None, chart_mode=None, renko_brick_size=None, clock=None,
                 source_guard=None, source_diagnostics=None, delta_quality_validator=None,
                 delta_session_recorder=None, enable_profit_rtd_order_flow=None,
                 profit_rtd_order_flow_pipeline=None, profit_rtd_validation_recorder=None,
                 *, temporal_primary_policy=None, source_timezone=None):
        if temporal_primary_policy is not None and not isinstance(
            temporal_primary_policy, TemporalSnapshotPolicy
        ):
            raise TypeError("INVALID_PRIMARY_TEMPORAL_POLICY")
        if source_timezone is not None and not isinstance(source_timezone, tzinfo):
            raise TypeError("INVALID_PRIMARY_SOURCE_TIMEZONE")
        self.temporal_primary_policy = temporal_primary_policy
        self.source_timezone = source_timezone
        self._temporal_primary_history = TemporalSnapshotHistory()
        self._primary_contract = None
        self._last_primary_receipt = None
        self._primary_gap_pending = False
        self._primary_gap_reason = None
        self._primary_publication_blocked = False
        self._primary_chart_volume = None
        self._protected_cycle_lock = Lock()
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
        self.last_valid_volume = None

        self.enable_profit_rtd_order_flow = bool(
            ENABLE_PROFIT_RTD_ORDER_FLOW
            if enable_profit_rtd_order_flow is None
            else enable_profit_rtd_order_flow
        )
        self.profit_rtd_order_flow_pipeline = profit_rtd_order_flow_pipeline
        self._accepted_rtd_version = None
        self.last_profit_rtd_receipt = None

        if not self.excel.conectar(EXCEL_PATH):
            raise RuntimeError("Não foi possível conectar ao Excel.")

        if self.enable_profit_rtd_order_flow and self.profit_rtd_order_flow_pipeline is None:
            self.profit_rtd_order_flow_pipeline = self._build_profit_rtd_order_flow_pipeline()

    def get_data(self):
        if self.temporal_primary_policy is None:
            return self._collect_cycle()

        if not self._protected_cycle_lock.acquire(blocking=False):
            raise RuntimeError("PROFIT_QUOTE_PROTECTED_CYCLE_IN_PROGRESS")
        try:
            return self._collect_protected()
        finally:
            self._protected_cycle_lock.release()

    def _collect_protected(self):
        print("[DATA LOOP] PROFIT_LOOP_ACTIVE", file=sys.stderr)
        if self._primary_publication_blocked:
            return self._reject_primary("PROFIT_QUOTE_REINITIALIZATION_REQUIRED")

        # Copy the graph together so builder/history and RTD/flow aliases
        # are preserved within the prepared cycle and detached from older ones.
        try:
            prepared = self._fork_protected_cycle()
        except Exception as exc:
            self._primary_publication_blocked = True
            raise RuntimeError("PROFIT_QUOTE_REINITIALIZATION_REQUIRED") from exc

        context = prepared._collect_cycle()
        if context is None:
            self.__dict__ = {
                **self.__dict__,
                "_primary_gap_pending": prepared._primary_gap_pending,
                "_primary_gap_reason": prepared._primary_gap_reason,
            }
            return None

        recovery_reason = prepared.__dict__.pop("_cycle_recovery_reason")
        original_rtd = self.profit_rtd_order_flow_pipeline
        if self.enable_profit_rtd_order_flow and isinstance(original_rtd, ProfitRTDOrderFlowPipeline):
            prepared._accepted_rtd_version = (
                original_rtd, prepared.profit_rtd_order_flow_pipeline._state(),
            )
            prepared.profit_rtd_order_flow_pipeline = original_rtd
        # ACCEPTED: the complete state becomes current in one reference swap.
        # Only the caller can observe delivery, when get_data() returns.
        self.__dict__ = prepared.__dict__
        self._report_protected_acceptance(recovery_reason)
        return context

    def _fork_protected_cycle(self):
        prepared = copy(self)
        memo = {}
        state = {name: getattr(self, name) for name in _PROTECTED_CYCLE_STATE}
        prepared.__dict__.update(deepcopy(state, memo))
        if self.enable_profit_rtd_order_flow:
            pipeline = self.profit_rtd_order_flow_pipeline
            if isinstance(pipeline, ProfitRTDOrderFlowPipeline):
                pipeline._bind_collector(self)
                fork = pipeline._fork(memo)
            else:
                # The previous injection contract requires prepare/publish.
                # An alternate must be independently copyable around its reader.
                reader = getattr(pipeline, "reader", None)
                if reader is not None:
                    memo[id(reader)] = reader
                fork = deepcopy(pipeline, memo)
            adapter = getattr(pipeline, "state_adapter", None)
            if fork is pipeline or (
                adapter is not None and fork.state_adapter.state is adapter.state
            ):
                raise TypeError("RTD_PIPELINE_ISOLATION_REQUIRED")
            prepared.profit_rtd_order_flow_pipeline = fork
        return prepared

    def _rtd_state_for(self, pipeline):
        version = self._accepted_rtd_version
        if version is not None and version[0] is pipeline:
            return version[1]

    @staticmethod
    def _report_protected_acceptance(recovery_reason):
        messages = [
            "[DATA ACCEPTED] PROFIT_QUOTE_ACCEPTED",
            "[DATA PUBLISHED] PROFIT_QUOTE_PUBLISHED",
        ]
        if recovery_reason is not None:
            messages.append(
                f"[DATA RECOVERED] PROFIT_LOCAL_RECOVERY_COMPLETE reason={recovery_reason}"
            )
        for message in messages:
            try:
                print(message)
            except Exception:
                # A failed diagnostic must not consume the accepted context.
                continue

    def _collect_cycle(self):
        policy = self.temporal_primary_policy
        read_coherent = getattr(self.reader, "obter_dados_coerentes", None)
        if policy is not None:
            logger.info("PROFIT_QUOTE_READ_ATTEMPT")
            try:
                dados = read_coherent() if callable(read_coherent) else self.reader.obter_dados()
            except ProfitQuoteIncompleteRange:
                return self._reject_primary("PROFIT_QUOTE_INCOMPLETE_RANGE", gap=True)
            except Exception:
                return self._reject_primary("PROFIT_QUOTE_READ_ERROR", gap=True)
            if dados is None:
                reason = ("PROFIT_QUOTE_INCONSISTENT_READ" if callable(read_coherent)
                          else "PROFIT_QUOTE_UNAVAILABLE")
                return self._reject_primary(reason, gap=True)
            if not dados:
                return self._reject_primary("PROFIT_QUOTE_UNAVAILABLE", gap=True)
            print("[DATA READ] PROFIT_QUOTE_READ_OK")
        else:
            dados = self.reader.obter_dados()
        if not dados:
            return None

        ativo = str(dados.get("ativo") or "").strip()
        if not ativo:
            if policy is not None:
                return self._reject_primary("PROFIT_QUOTE_INVALID_SYMBOL", gap=True)
            print("[DATA WARNING] Ativo inválido recebido. Leitura ignorada.")
            return None

        close = self.to_float(dados.get("close"))
        if not math.isfinite(close) or close <= 0:
            if policy is not None:
                return self._reject_primary("PROFIT_QUOTE_INVALID_PRICE", gap=True)
            print(f"[DATA WARNING] Preço inválido recebido: {close!r}. Leitura ignorada.")
            return None

        source_timestamp = primary_quote_source_timestamp(
            dados, source_timezone=self.source_timezone if policy is not None else None
        )
        received_timestamp = None
        gap_reason = None
        if policy is not None:
            try:
                received_timestamp = self.clock.now()
                if (not isinstance(received_timestamp, datetime)
                        or received_timestamp.utcoffset() is None):
                    return self._reject_primary("TEMPORAL_VALIDATION_ERROR")
            except Exception:
                return self._reject_primary("TEMPORAL_VALIDATION_ERROR")
            stream = ativo.upper()
            previous_source = self._temporal_primary_history.previous(None, stream)
            temporal = validate_primary_quote_timestamp(
                source_timestamp,
                reference_timestamp=received_timestamp,
                policy=policy,
                previous_timestamp=previous_source,
            )
            if not temporal.accepted:
                if temporal.reason == "TEMPORAL_SOURCE_TIMEZONE_REQUIRED":
                    print("[DATA WARNING] TEMPORAL_INVALID_TIMESTAMP")
                return self._reject_primary(temporal.reason)
            contract = (stream, str(dados.get("vencimento") or "").strip())
            if self._primary_contract is not None and contract != self._primary_contract:
                return self._reject_primary("TEMPORAL_CONTRACT_TRANSITION_BLOCKED")
            if (
                self._last_primary_receipt is not None
                and (
                    received_timestamp.astimezone(timezone.utc)
                    < self._last_primary_receipt.astimezone(timezone.utc)
                    or received_timestamp.replace(tzinfo=None)
                    < self._last_primary_receipt.replace(tzinfo=None)
                )
            ):
                return self._reject_primary("TEMPORAL_REGRESSIVE_RECEIPT")
            if self._last_primary_receipt is not None:
                receipt_interval = (
                    received_timestamp.astimezone(timezone.utc)
                    - self._last_primary_receipt.astimezone(timezone.utc)
                ).total_seconds()
                source_interval = (
                    datetime.fromisoformat(source_timestamp).astimezone(timezone.utc)
                    - datetime.fromisoformat(previous_source).astimezone(timezone.utc)
                ).total_seconds()
                if self._primary_gap_pending:
                    gap_reason = self._primary_gap_reason
                elif max(receipt_interval, source_interval) > policy.maximum_age_seconds:
                    gap_reason = "PROFIT_QUOTE_INTERVAL_EXCEEDED"

        raw_volume = dados.get("volume")
        if policy is None:
            volume, volume_held = self._resolve_cumulative_volume(raw_volume)
        else:
            volume = self.to_optional_float(raw_volume)
            volume_held = False
            if volume is None:
                return self._reject_primary("PROFIT_QUOTE_INVALID_VOLUME", gap=True)
        print(
            f"[VOLUME DEBUG] raw={raw_volume!r} converted={volume} "
            f"held_last_valid={volume_held}"
        )
        if volume is None:
            print(
                "[DATA WARNING] Volume acumulado indisponível e ainda sem baseline válido. "
                "Leitura ignorada."
            )
            return None
        if volume_held:
            print(
                "[DATA WARNING] Volume acumulado indisponível nesta leitura; "
                "mantendo último valor válido para evitar reset artificial."
            )
        aggression_buy = self.to_optional_float(dados.get("agressao_compra"))
        aggression_sell = self.to_optional_float(dados.get("agressao_venda"))
        # O timestamp de origem participa da deduplicação protegida,
        # inclusive quando a fonte fornece source_timestamp em vez de data/hora.
        integrity_data = dados if policy is None else dict(
            dados, data=source_timestamp, hora=None
        )
        integrity = (self.source_guard.inspect(integrity_data) if policy is None
                     else self.source_guard.evaluate(integrity_data))

        if policy is not None and integrity.duplicate:
            return self._reject_primary("PROFIT_QUOTE_DUPLICATE: Snapshot do Profit sem mudança")

        if policy is not None:
            print("[DATA VALIDATED] PROFIT_QUOTE_ELIGIBLE")
        staged_rtd = None
        if policy is not None and self.enable_profit_rtd_order_flow:
            try:
                staged_rtd, receipt = self.profit_rtd_order_flow_pipeline.prepare(
                    ativo, price=close, rebase=gap_reason is not None,
                )
                recorder = deepcopy(self.profit_rtd_validation_recorder)
                recorder.record(receipt)
            except Exception:
                return self._reject_primary("PROFIT_QUOTE_AUXILIARY_FAILED", gap=True)

        chart_volume = volume
        if policy is not None and self._primary_chart_volume is not None:
            # Preserve attributed volume and start measuring fresh deltas at
            # the resumed sample. The raw counter can include the entire gap.
            if gap_reason is not None:
                chart_volume = self._primary_chart_volume
                print("[DATA CONTINUITY] PROFIT_QUOTE_GAP_VOLUME_INDETERMINATE")
            elif volume < self.last_valid_volume:
                chart_volume = 0.0
            else:
                chart_volume = self._primary_chart_volume + (volume - self.last_valid_volume)

        if staged_rtd is not None:
            auxiliary_flow = staged_rtd.state_adapter.state
            diagnostic_buy = auxiliary_flow.cumulative_buy
            diagnostic_sell = auxiliary_flow.cumulative_sell
        elif self.enable_profit_rtd_order_flow:
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
            if policy is None and integrity.symbol_changed:
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

        timestamp = self.clock.now() if policy is None else received_timestamp
        self.last_new_candles = self.multi_timeframe.update_tick(
            symbol=ativo,
            price=close,
            cumulative_volume=chart_volume,
            timestamp=timestamp,
        )

        if self.chart_mode == ChartMode.RENKO:
            self.last_closed_renko_bricks = self.renko.update_tick(
                symbol=ativo,
                price=close,
                cumulative_volume=chart_volume,
                timestamp=timestamp,
            )

        if staged_rtd is not None:
            self.profit_rtd_order_flow_pipeline.publish(staged_rtd)
            self.profit_rtd_validation_recorder = recorder
            self.last_profit_rtd_receipt = receipt
        elif not self.enable_profit_rtd_order_flow:
            if gap_reason is not None:
                self.order_flow.clear()
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

        context = AnalysisContext(
            market=self.market,
            multi_timeframe=self.multi_timeframe,
            order_flow_state=self.order_flow,
            source_timestamp=source_timestamp,
            received_timestamp=timestamp,
        )
        if policy is not None:
            self.source_guard.record(integrity)
            self._temporal_primary_history.record(None, stream, source_timestamp)
            self._primary_contract = contract
            self._last_primary_receipt = received_timestamp
            self._primary_gap_pending = False
            self._cycle_recovery_reason = gap_reason or self._primary_gap_reason
            self._primary_gap_reason = None
            self._primary_chart_volume = chart_volume
            self.last_valid_volume = volume
        return context

    def _reject_primary(self, reason, *, gap=False):
        if gap:
            self._primary_gap_pending = True
            self._primary_gap_reason = reason
        print(f"[DATA REJECTED] {reason}")
        return None

    def _build_profit_rtd_order_flow_pipeline(self):
        from market_data.excel_range_gateway import ExcelRangeGateway
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

    def export_profit_rtd_validation_session(self, target, *, overwrite: bool = False):
        from market_data.profit_rtd_validation_exporter import ProfitRTDValidationExporter

        exporter = ProfitRTDValidationExporter()
        return exporter.export(
            self.profit_rtd_validation_recorder.snapshot,
            target,
            overwrite=overwrite,
        )

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

    def _resolve_cumulative_volume(self, raw_volume):
        converted = self.to_optional_float(raw_volume)
        if converted is not None:
            self.last_valid_volume = converted
            return converted, False
        if self.last_valid_volume is not None:
            return self.last_valid_volume, True
        return None, False

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
