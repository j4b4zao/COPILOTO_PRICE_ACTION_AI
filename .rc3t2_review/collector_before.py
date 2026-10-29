"""Coleta Profit/Excel com integridade, diagnóstico, qualidade e recorder de Delta."""

import math
from connectors.profit_reader import ProfitReader, ReaderAcquisitionMetadata, AcquisitionState
import re
import contextlib
import io
from time import monotonic_ns
from inspect import getattr_static
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from market_data.source_temporal_validator import TemporalResult, validate_source_temporal
from market_data.source_reread_capability import (
    RereadDecision, evaluate_reread_capability,
)
from market_data.source_snapshot_consistency import (
    AcquisitionError, AcquisitionMetadata, SnapshotConsistencyResult,
    evaluate_snapshot_consistency,
)


@dataclass(frozen=True, slots=True)
class AcquisitionTiming:
    """Monotonic endpoints in ns; no calendar time or quote age.

    Missing clock values or a regressive clock yield duration_ns=None.
    Endpoints include failed reader calls, with no timeout/retry policy.
    """
    start_ns: int | None
    end_ns: int | None
    duration_ns: int | None


@dataclass(frozen=True, slots=True)
class CollectionAcquisitionMetadata:
    """Bounded, observational K envelope for one reader invocation.

    UNKNOWN may retain a valid K envelope for a legacy connector. Absent,
    unsupported or stale metadata has no retained envelope and is not evidence.
    Association supports only the exact imported ProfitReader K class, not
    subclasses or lookalikes, plus a new envelope and the exact next ID.
    This is a local supported-contract guarantee, not absolute authenticity;
    runtime patching or connector behavior is not certified. Serial use only.
    Mutable raw values inside the K envelope are not copied or frozen.
    """
    cycle_id: int
    sample_position: str
    state: AcquisitionState = AcquisitionState.UNKNOWN
    reader_metadata: ReaderAcquisitionMetadata | None = None
    reason: str | None = None
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False


@dataclass(frozen=True, slots=True)
class CollectionCycleTrace:
    """Latest cycle only; independent from the latest comparison.

    UPDATED: current comparison available, no known diagnostic/clock failure.
    INCOMPLETE: enabled but acquisition/processing/evaluation/timing incomplete.
    NOT_EXECUTED: disabled or reread denied, without additional reads.
    Denial reasons come from the explicit reread contract; query/evaluation
    failures also deny. reread_decision retains the normalized declaration.
    observation_relation is CURRENT_CYCLE, PREVIOUS_CYCLE or NONE.
    These states do not certify completeness of RTD cells or market validity.
    IDs start at 1, count every get_data attempt, and never reset on symbol
    changes. Serial use per instance only; no concurrency/reentrancy guarantee.
    """
    cycle_id: int
    enabled: bool
    diagnostic_status: str
    observation_relation: str
    first_acquisition: AcquisitionTiming
    second_acquisition: AcquisitionTiming | None
    reason: str | None = None
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    reread_decision: RereadDecision | None = None
    acquisition_metadata: tuple[CollectionAcquisitionMetadata, ...] = ()


@dataclass(frozen=True, slots=True)
class CollectorSnapshotObservation:
    """One pair only, acquired sequentially around existing processing.

    The second sample is acquired AFTER candles/RTD/temporal diagnostics to
    preserve their acquisition order and candle clock calls. This is not a
    simultaneous pair. attempts counts obter_dados invocations per sample,
    not cell reads or hidden connector retries. None errors means unknown,
    including cell exceptions silently returned as None by ExcelConnector.
    No chosen sample, rejection, atomicity or freshness assertion.
    """
    diagnostic: SnapshotConsistencyResult | None
    first_metadata: AcquisitionMetadata
    second_metadata: AcquisitionMetadata
    error: str | None = None
    atomicity_proven: bool = False
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    cycle_id: int = 0
    first_acquisition: AcquisitionTiming | None = None
    second_acquisition: AcquisitionTiming | None = None



@dataclass(frozen=True, slots=True)
class CollectorTemporalObservation:
    """Last acquisition attempt only; no freshness or last-trade assertion.

    Acquisition is stamped after the sequential reader returns; processing is
    stamped at entry to existing processing. Both use explicit system UTC,
    independently of the injected candle clock. Neither is an atomic RTD time.
    Raw fields are retained unchanged (unsupported mutable values remain raw).
    Failed/rejected symbol attempts never replace the active-symbol baseline.
    get_data binds each newly constructed observation to its local cycle and
    FIRST_SAMPLE. A failed acquisition can retain an older object and its ID;
    consumers must compare IDs, never relabel the previous observation.
    Legacy constructors/direct three-argument publisher calls remain unbound.
    """
    symbol: str
    raw_date: object
    raw_time: object
    acquired_at: datetime | None
    processing_at: datetime | None
    diagnostic: TemporalResult | None
    error: str | None = None
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    cycle_id: int | None = None
    sample_position: str | None = None


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
    VERSION = "H10-RC3.18.3.3H-REREAD-GUARD"
    MAX_MISSING_VOLUME_READS = 2

    def __init__(self, excel=None, reader=None, multi_timeframe=None, renko_state=None,
                 order_flow_state=None, chart_mode=None, renko_brick_size=None, clock=None,
                 source_guard=None, source_diagnostics=None, delta_quality_validator=None,
                 delta_session_recorder=None, enable_profit_rtd_order_flow=None,
                 profit_rtd_order_flow_pipeline=None, profit_rtd_validation_recorder=None,
                 enable_snapshot_consistency=False):
        if type(enable_snapshot_consistency) is not bool:
            raise TypeError("enable_snapshot_consistency must be bool")
        self.enable_snapshot_consistency = enable_snapshot_consistency
        self.last_snapshot_observation = None
        self.collection_cycle_id = 0
        self.last_collection_cycle = None
        self._cycle_acquisition_metadata = ()
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
        self._missing_volume_reads = 0
        self.last_temporal_observation = None
        self._temporal_reference = None

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

    @staticmethod
    def _temporal_now():
        # No extra calls to self.clock: candle clock behavior remains unchanged.
        try:
            return datetime.now(timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _monotonic_now():
        try:
            return monotonic_ns()
        except Exception:
            return None

    @staticmethod
    def _acquisition_timing(start, end):
        duration = (end - start if type(start) is int and type(end) is int
                    and end >= start else None)
        return AcquisitionTiming(start, end, duration)

    def get_data(self):
        self.collection_cycle_id += 1
        cycle_id = self.collection_cycle_id
        self._cycle_acquisition_metadata = ()
        enabled = self.enable_snapshot_consistency
        start = self._monotonic_now()
        timing = None
        reason = "FIRST_SAMPLE_READ_FAILED"
        completed = False
        reread_decision = None
        reread_block_reason = None
        try:
            try:
                dados = self._acquire_sample(cycle_id, "FIRST_SAMPLE")
            finally:
                timing = self._acquisition_timing(start, self._monotonic_now())
            acquired_at = self._temporal_now()
            processing_at = self._temporal_now()
            reason = "MARKET_PROCESSING_FAILED"
            try:
                result = self._process_acquired_snapshot(dados)
                completed = True
                reason = None
                return result
            finally:
                # Existing temporal/candle clocks and processing order retained.
                self._publish_temporal_observation(
                    dados, acquired_at, processing_at, cycle_id=cycle_id)
                if completed and enabled:
                    reread_decision, reread_block_reason = self._query_reread_capability()
                    if reread_block_reason is None:
                        self._publish_snapshot_observation(dados, cycle_id, timing)
        finally:
            self._publish_cycle_trace(cycle_id, enabled, timing, reason,
                                      reread_decision, reread_block_reason)

    @staticmethod
    def _reader_metadata_snapshot(reader):
        # K exposes concrete instance attributes. Do not invoke properties,
        # dynamic providers, capability methods, or additional source reads.
        if type(reader) is not ProfitReader:
            return None, None
        try:
            values = object.__getattribute__(reader, "__dict__")
            return values.get("acquisition_id"), values.get("last_acquisition_metadata")
        except Exception:
            return None, None

    def _acquire_sample(self, cycle_id, position):
        reader = self.reader
        before_id, before_metadata = self._reader_metadata_snapshot(reader)
        try:
            return reader.obter_dados()
        finally:
            # Immediately capture even a failed acquisition, before any market
            # processing or authorized second sample can replace K metadata.
            try:
                after_id, metadata = self._reader_metadata_snapshot(reader)
                valid = (type(reader) is ProfitReader
                         and type(before_id) is int and before_id >= 0
                         and type(after_id) is int and after_id == before_id + 1
                         and type(metadata) is ReaderAcquisitionMetadata
                         and metadata is not before_metadata
                         and type(metadata.acquisition_id) is int
                         and metadata.acquisition_id == after_id
                         and type(metadata.contract_version) is int
                         and metadata.contract_version == 1
                         and type(metadata.state) is AcquisitionState
                         and type(metadata.cells) is tuple and len(metadata.cells) == 31
                         and metadata.orders_allowed is False
                         and metadata.live_certified is False
                         and metadata.flow_complete is False)
                sample = CollectionAcquisitionMetadata(
                    cycle_id, position,
                    metadata.state if valid else AcquisitionState.UNKNOWN,
                    metadata if valid else None,
                    None if valid else "METADATA_UNAVAILABLE_OR_UNASSOCIATED")
                self._cycle_acquisition_metadata = (
                    self._cycle_acquisition_metadata + (sample,))[-2:]
            except Exception:
                # Observability must never change a quote return/exception.
                sample = CollectionAcquisitionMetadata(
                    cycle_id, position, reason="METADATA_CAPTURE_FAILED")
                self._cycle_acquisition_metadata = (
                    self._cycle_acquisition_metadata + (sample,))[-2:]

    def _query_reread_capability(self):
        """Explicit reader.reread_capability value/property; no method calls.

        Absent attributes and dynamic __getattr__ providers are not declarations.
        A property is consulted once; lookup failures deny. No inference from
        reader class, name, obter_dados or transport. Declaration is not proof
        of atomicity, freshness or side-effect isolation.
        """
        try:
            # Static lookup avoids invoking a dynamic provider for missing attrs.
            declared = getattr_static(self.reader, "reread_capability", None)
            declaration = (None if declared is None
                           else getattr(self.reader, "reread_capability"))
        except Exception:
            return None, "REREAD_CAPABILITY_QUERY_FAILED"
        try:
            decision = evaluate_reread_capability(declaration)
            if type(decision) is not RereadDecision:
                raise TypeError("UNSUPPORTED_REREAD_DECISION")
            return decision, None if decision.authorized else decision.reason.value
        except Exception:
            return None, "REREAD_CAPABILITY_EVALUATION_FAILED"

    def _publish_cycle_trace(self, cycle_id, enabled, timing, reason,
                             reread_decision=None, reread_block_reason=None):
        try:
            observation = self.last_snapshot_observation
            relation = ("NONE" if observation is None else
                        "CURRENT_CYCLE" if observation.cycle_id == cycle_id
                        else "PREVIOUS_CYCLE")
            second = (observation.second_acquisition
                      if relation == "CURRENT_CYCLE" else None)
            if not enabled:
                status = "NOT_EXECUTED"
                reason = reason or "DISABLED"
            elif reread_block_reason is not None:
                status = "NOT_EXECUTED"
                reason = reread_block_reason
            elif relation != "CURRENT_CYCLE":
                status = "INCOMPLETE"
                reason = reason or "OBSERVATION_NOT_PUBLISHED"
            else:
                reason = reason or observation.error
                if reason is None and (timing.duration_ns is None or
                                       second is None or second.duration_ns is None):
                    reason = "ACQUISITION_TIMING_UNAVAILABLE"
                status = "INCOMPLETE" if reason else "UPDATED"
            self.last_collection_cycle = CollectionCycleTrace(
                cycle_id, enabled, status, relation, timing, second, reason,
                reread_decision=reread_decision,
                acquisition_metadata=self._cycle_acquisition_metadata)
        except Exception:
            # Trace publication cannot suppress an existing return/exception.
            pass

    def _publish_snapshot_observation(self, first, cycle_id, first_timing):
        # One additional invocation only; no RTD processing, retries or sleeps.
        try:
            method = ("SEQUENTIAL_CELLS" if type(self.reader) is ProfitReader
                      else "READER_OBTER_DADOS")
            first_metadata = AcquisitionMetadata(method, 1, None)
            second_metadata = AcquisitionMetadata(method, 1, None)
            diagnostic, error = None, None
            # Capture before the extra call, including readers reusing one dict.
            frozen_first = dict(first) if type(first) is dict else {}
            second_start = self._monotonic_now()
            try:
                second = self._acquire_sample(cycle_id, "SECOND_SAMPLE")
            except Exception:
                second = {}
                error = "SECOND_SAMPLE_READ_FAILED"
                second_metadata = AcquisitionMetadata(
                    method, 1, (AcquisitionError(error),))
            finally:
                second_timing = self._acquisition_timing(
                    second_start, self._monotonic_now())
            if type(second) is not dict:
                second = {}
                error = "SECOND_SAMPLE_NOT_DICT"
                second_metadata = AcquisitionMetadata(
                    method, 1, (AcquisitionError(error),))
            try:
                diagnostic = evaluate_snapshot_consistency(
                    frozen_first, second, first_metadata=first_metadata,
                    second_metadata=second_metadata)
                if type(diagnostic) is not SnapshotConsistencyResult:
                    raise TypeError("UNSUPPORTED_CONSISTENCY_RESULT")
            except Exception:
                diagnostic = None
                error = "SNAPSHOT_EVALUATION_FAILED"
            self.last_snapshot_observation = CollectorSnapshotObservation(
                diagnostic, first_metadata, second_metadata, error,
                cycle_id=cycle_id, first_acquisition=first_timing,
                second_acquisition=second_timing)
        except Exception:
            # Diagnostics never replace a market return/exception.
            pass

    def _publish_temporal_observation(self, dados, acquired_at, processing_at, *, cycle_id=None):
        try:
            raw = dados if isinstance(dados, dict) else {}
            symbol = str(raw.get("ativo") or "").strip().upper()
            reference = self._temporal_reference
            previous = reference[1] if reference and reference[0] == symbol else None
            diagnostic, error = None, None
            try:
                # No format or temporal semantics inferred from B2/C2 labels.
                diagnostic = validate_source_temporal(
                    raw.get("data"), raw.get("hora"), acquired_at=acquired_at,
                    previous_timestamp=previous)
                if type(diagnostic) is not TemporalResult:
                    raise TypeError("UNSUPPORTED_TEMPORAL_RESULT")
            except Exception:
                diagnostic, error = None, "TEMPORAL_DIAGNOSTIC_FAILED"
            observation = CollectorTemporalObservation(
                symbol, raw.get("data"), raw.get("hora"), acquired_at,
                processing_at, diagnostic, error, cycle_id=cycle_id,
                sample_position="FIRST_SAMPLE" if cycle_id is not None else None)
            current = str(self.market.symbol or "").strip().upper()
            if reference and reference[0] != current:
                self._temporal_reference = None
            if symbol and symbol == current and diagnostic is not None:
                if diagnostic.source_timestamp is not None:
                    self._temporal_reference = (symbol, diagnostic.source_timestamp)
            self.last_temporal_observation = observation
        except Exception:
            # Diagnostic-only failures never change market flow.
            pass

    def _process_acquired_snapshot(self, dados):
        if not dados:
            return None
        symbol = str(dados.get("ativo") or "").strip().upper()
        current = str(self.market.symbol or "").strip().upper()
        normalized = dict(dados)
        normalized["ativo"] = symbol
        if not current or symbol == current:
            return self._get_data_from_snapshot(normalized)
        try:
            # No retained volume is permitted across instruments.
            price = self.to_float(dados.get("close"))
            volume = self.to_optional_float(dados.get("volume"))
            self.to_optional_float(dados.get("agressao_compra"))
            self.to_optional_float(dados.get("agressao_venda"))
            if not symbol or price <= 0 or volume is None:
                return None
            prepared = self._prepare_symbol_transition()
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = prepared._get_data_from_snapshot(normalized)
            if result is None:
                return None
        except Exception:
            print("[DATA WARNING] SYMBOL_TRANSITION_REJECTED: estado anterior preservado.")
            return None
        # Single publication after all processing/diagnostic operations succeed.
        self.__dict__.update(prepared.__dict__)
        print(output.getvalue(), end="")
        return result

    def _prepare_symbol_transition(self):
        """Explicit reconstruction of audited state types; never generic copying."""
        from core.candle_builder import CandleBuilder
        from core.market_state import MarketState
        from models.candle_history import CandleHistory
        from dataclasses import fields
        from market_data.profit_delta_session_recorder import ProfitDeltaSessionSample

        expected = (
            (self.multi_timeframe, MultiTimeframeState), (self.renko, RenkoState),
            (self.order_flow, OrderFlowState), (self.source_guard, ProfitSourceIntegrityGuard),
            (self.source_diagnostics, ProfitDeltaSourceDiagnostics),
            (self.delta_quality_validator, ProfitDeltaQualityValidator),
            (self.delta_session_recorder, ProfitDeltaSessionRecorder),
            (self.profit_rtd_validation_recorder, ProfitRTDValidationRecorder),
        )
        if any(type(obj) is not cls or any(callable(v) for v in getattr(obj, "__dict__", {}).values())
               for obj, cls in expected):
            raise TypeError("UNSUPPORTED_TRANSITION_COMPONENT")
        if self.multi_timeframe.TIMEFRAMES != MultiTimeframeState.TIMEFRAMES:
            raise TypeError("UNSUPPORTED_TIMEFRAMES")
        for name in self.multi_timeframe.TIMEFRAMES:
            market = self.multi_timeframe._markets[name]
            builder = self.multi_timeframe._builders[name]
            if (type(market) is not MarketState or type(market.candles) is not CandleHistory
                    or type(builder) is not CandleBuilder
                    or set(vars(builder)) != {'current', 'current_period', 'last_cumulative_volume', 'period_start_volume'}):
                raise TypeError("UNSUPPORTED_MARKET_COMPONENT")
        if type(self.renko.market) is not MarketState or type(self.renko.market.candles) is not CandleHistory:
            raise TypeError("UNSUPPORTED_RENKO_COMPONENT")
        # Validate aggregate data before constructing or invoking mutable components.
        scalar_types = (str, int, float, bool, type(None))
        if any(type(v) not in scalar_types for v in vars(self.source_diagnostics).values()):
            raise TypeError("UNSUPPORTED_DIAGNOSTIC_STATE")
        if any(type(v) not in scalar_types for v in vars(self.delta_quality_validator).values()):
            raise TypeError("UNSUPPORTED_QUALITY_CONFIGURATION")
        if any(type(sample) is not ProfitDeltaSessionSample or
               any(type(getattr(sample, field.name)) not in scalar_types for field in fields(sample))
               for sample in self.delta_session_recorder.samples):
            raise TypeError("UNSUPPORTED_RECORDER_STATE")
        for name, value in vars(self.profit_rtd_validation_recorder).items():
            if name == '_continuities':
                if type(value) is not Counter or any(type(k) is not str or type(v) is not int for k, v in value.items()):
                    raise TypeError("UNSUPPORTED_VALIDATION_COUNTER")
            elif type(value) not in scalar_types:
                raise TypeError("UNSUPPORTED_VALIDATION_STATE")
        pipeline_types = None
        if self.enable_profit_rtd_order_flow:
            from market_data.profit_rtd_order_flow_pipeline import ProfitRTDOrderFlowPipeline
            from market_data.profit_rtd_order_flow_state_adapter import ProfitRTDOrderFlowStateAdapter
            from market_data.profit_rtd_times_trades_deduplicator import ProfitRTDTimesTradesDeduplicator
            from market_data.profit_rtd_incremental_aggression import ProfitRTDIncrementalAggressionBuilder
            from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader
            old = self.profit_rtd_order_flow_pipeline
            if (type(old) is not ProfitRTDOrderFlowPipeline
                    or set(vars(old)) != {"reader", "deduplicator", "aggression_builder", "state_adapter"}
                    or type(old.deduplicator) is not ProfitRTDTimesTradesDeduplicator
                    or type(old.state_adapter) is not ProfitRTDOrderFlowStateAdapter
                    or old.state_adapter.state is not self.order_flow
                    or set(vars(old.state_adapter)) != {"state", "_symbol", "_cumulative_buy", "_cumulative_sell"}
                    or set(vars(old.deduplicator)) != {"_symbol", "_previous"}
                    or old.aggression_builder is not ProfitRTDIncrementalAggressionBuilder
                    or type(old.reader) is not ProfitRTDTimesTradesReader):
                raise TypeError("UNSUPPORTED_RTD_TRANSITION")
            pipeline_types = ProfitRTDOrderFlowPipeline
        prepared = object.__new__(Collector)
        prepared.__dict__ = self.__dict__.copy()  # Only acquisition/config references retained.
        prepared.multi_timeframe = MultiTimeframeState()
        prepared.multi_timeframe.PRIMARY_TIMEFRAME = self.multi_timeframe.PRIMARY_TIMEFRAME
        for name, market in self.multi_timeframe._markets.items():
            prepared.multi_timeframe._markets[name].candles = CandleHistory(market.candles._candles.maxlen)
        prepared.renko = RenkoState(brick_size=self.renko.brick_size)
        prepared.renko.market.candles = CandleHistory(self.renko.market.candles._candles.maxlen)
        prepared.order_flow = OrderFlowState()
        prepared.source_guard = ProfitSourceIntegrityGuard()
        prepared.source_guard._last_symbol = str(self.market.symbol).strip().upper()
        prepared.source_diagnostics = ProfitDeltaSourceDiagnostics()
        prepared.source_diagnostics.__dict__.update(vars(self.source_diagnostics))  # Validated scalar counters.
        prepared.delta_quality_validator = ProfitDeltaQualityValidator()
        prepared.delta_quality_validator.__dict__.update(vars(self.delta_quality_validator))
        prepared.delta_session_recorder = ProfitDeltaSessionRecorder(self.delta_session_recorder.max_samples)
        prepared.delta_session_recorder._samples = list(self.delta_session_recorder.samples)
        prepared.profit_rtd_validation_recorder = ProfitRTDValidationRecorder()
        for name, value in vars(self.profit_rtd_validation_recorder).items():
            setattr(prepared.profit_rtd_validation_recorder, name, Counter(value) if name == '_continuities' else value)
        if pipeline_types is not None:
            prepared.profit_rtd_order_flow_pipeline = pipeline_types(self.profit_rtd_order_flow_pipeline.reader, prepared.order_flow)
        prepared.last_snapshot_observation = None
        prepared.last_temporal_observation = None
        prepared._temporal_reference = None
        prepared.last_valid_volume = None
        prepared._missing_volume_reads = 0
        prepared.last_profit_rtd_receipt = None
        prepared.last_new_candles = {name: False for name in self.multi_timeframe.TIMEFRAMES}
        prepared.last_closed_renko_bricks = 0
        prepared.market = prepared._primary_market()
        prepared.last_delta_quality = prepared.delta_quality_validator.evaluate(prepared.order_flow, prepared.source_diagnostics.snapshot)
        return prepared

    def _get_data_from_snapshot(self, dados):
        if not dados:
            return None

        raw_volume = dados.get("volume")
        # Validate every consumed numeric field before baseline/fingerprint changes.
        try:
            close = self.to_float(dados.get("close"))
            self.to_optional_float(raw_volume)
            aggression_buy = self.to_optional_float(dados.get("agressao_compra"))
            aggression_sell = self.to_optional_float(dados.get("agressao_venda"))
        except ValueError:
            print("[DATA WARNING] INVALID_NUMERIC_INPUT: leitura ignorada.")
            return None
        if close <= 0:
            print("[DATA WARNING] Preço ausente ou não positivo; leitura ignorada.")
            return None

        ativo = str(dados.get("ativo") or "").strip().upper()
        if not ativo:
            print("[DATA WARNING] Ativo inválido recebido. Leitura ignorada.")
            return None

        # Reject exhausted holds before touching the source guard, candles or OrderFlow.
        # Count numeric-valid missing-volume reads, including duplicate snapshots.
        if (self.to_optional_float(raw_volume) is None
                and self.last_valid_volume is not None
                and self._missing_volume_reads >= self.MAX_MISSING_VOLUME_READS):
            print("[DATA WARNING] VOLUME_HOLD_EXHAUSTED: leitura ignorada.")
            return None
        volume, volume_held = self._resolve_cumulative_volume(raw_volume)
        print(
            f"[VOLUME DEBUG] raw={raw_volume!r} converted={volume} "
            f"held_last_valid={volume_held}"
        )
        if volume is None:
            print("[DATA WARNING] Volume ausente e sem baseline; leitura ignorada.")
            return None
        if volume_held:
            print("[DATA WARNING] Volume ausente; mantendo último valor válido.")

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
            self._missing_volume_reads = 0
            return converted, False
        if self.last_valid_volume is not None:
            self._missing_volume_reads += 1
            return self.last_valid_volume, True
        return None, False

    @staticmethod
    def _parse_number(value):
        """None means absent; corrupt or ambiguous inputs raise ValueError."""
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("INVALID_NUMERIC_INPUT")
        if isinstance(value, (int, float)):
            normalized = value
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            sign = ""
            if text[0] in "+-":
                sign, text = text[0], text[1:]
            if not text:
                raise ValueError("INVALID_NUMERIC_INPUT")
            if "." in text and "," in text:
                decimal = "." if text.rfind(".") > text.rfind(",") else ","
                grouping = "," if decimal == "." else "."
                pattern = r"[0-9]{1,3}(?:" + re.escape(grouping) + r"[0-9]{3})+" + re.escape(decimal) + r"[0-9]+"
                if re.fullmatch(pattern, text) is None:
                    raise ValueError("INVALID_NUMERIC_INPUT")
                normalized = sign + text.replace(grouping, "").replace(decimal, ".")
            elif "." in text or "," in text:
                separator = "." if "." in text else ","
                if text.count(separator) == 1:
                    parts = text.split(separator)
                    if not all(re.fullmatch(r"[0-9]+", part) for part in parts):
                        raise ValueError("INVALID_NUMERIC_INPUT")
                    # A single separator followed by three digits is locale-ambiguous.
                    if len(parts[0]) <= 3 and len(parts[1]) == 3:
                        raise ValueError("AMBIGUOUS_NUMERIC_INPUT")
                    normalized = sign + text.replace(separator, ".")
                else:
                    pattern = r"[0-9]{1,3}(?:" + re.escape(separator) + r"[0-9]{3}){2,}"
                    if re.fullmatch(pattern, text) is None:
                        raise ValueError("INVALID_NUMERIC_INPUT")
                    normalized = sign + text.replace(separator, "")
            else:
                if re.fullmatch(r"[0-9]+", text) is None:
                    raise ValueError("INVALID_NUMERIC_INPUT")
                normalized = sign + text
        else:
            raise ValueError("INVALID_NUMERIC_INPUT")
        try:
            converted = float(normalized)
        except (ValueError, TypeError, OverflowError):
            raise ValueError("INVALID_NUMERIC_INPUT") from None
        if not math.isfinite(converted):
            raise ValueError("NON_FINITE_NUMERIC_INPUT")
        return converted

    @staticmethod
    def to_float(value):
        converted = Collector._parse_number(value)
        return 0.0 if converted is None else converted

    @staticmethod
    def to_optional_float(value):
        converted = Collector._parse_number(value)
        if converted is not None and converted < 0:
            raise ValueError("NEGATIVE_OPTIONAL_NUMBER")
        return converted
