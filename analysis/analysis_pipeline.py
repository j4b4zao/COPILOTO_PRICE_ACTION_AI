"""
analysis/analysis_pipeline.py

Pipeline principal do COPILOTO PRICE ACTION AI.

RC15.5 + TRADER PSYCHOLOGY RC7 - PIPELINE OBSERVATIONAL
"""

from copy import deepcopy
from analysis.temporal_snapshot_policy import (
    TemporalSnapshotHistory,
    TemporalSnapshotPolicy,
    validate_primary_quote_timestamp,
    validate_snapshot_timestamp,
)
from dataclasses import replace

from core.analysis_context import AnalysisContext
from external_context.external_market_state import ExternalMarketState
from models.book_depth import BookDepthSnapshot
from psychology.trader_psychology_context_bridge import (
    TraderPsychologyContextBridge,
)
from psychology.trader_psychology_runtime import TraderPsychologyRuntime
from psychology.trader_psychology_state import TraderPsychologyState

from analysis.market_structure import MarketStructure
from analysis.market_regime import MarketRegime
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from analysis.liquidity_analysis import LiquidityAnalysis
from analysis.volume_analysis import VolumeAnalysis
from analysis.order_flow import OrderFlow
from analysis.book_depth_analysis import BookDepthAnalysis
from analysis.price_action.price_action import PriceAction
from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from analysis.replay.book_diagnostics_replay_recorder import BookDiagnosticsReplayRecorder
from analysis.replay.score_regime_mtf_ab_recorder import ScoreRegimeMtfABRecorder
from analysis.replay.score_external_context_ab_recorder import ScoreExternalContextABRecorder
from analysis.replay.score_order_flow_ab_recorder import ScoreOrderFlowABRecorder
from analysis.replay.score_order_flow_structure_ab_recorder import ScoreOrderFlowStructureABRecorder
from analysis.replay.score_book_depth_ab_recorder import ScoreBookDepthABRecorder
from analysis.replay.score_microstructure_eligibility_ab_recorder import (
    ScoreMicrostructureEligibilityABRecorder,
)
from analysis.replay.microstructure_confluence_replay_recorder import (
    MicrostructureConfluenceReplayRecorder,
)
from analysis.replay.microstructure_eligibility_replay_recorder import (
    MicrostructureEligibilityReplayRecorder,
)

from analysis.smart_money.imbalance import Imbalance
from analysis.smart_money.order_block import OrderBlock
from analysis.smart_money.fair_value_gap import FairValueGap
from analysis.smart_money.liquidity_pool import LiquidityPool

from brain.context_engine import ContextEngine
from strategies.strategy_engine import StrategyEngine
from ai.score_engine_rc13_2 import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine
from alerts.alert_manager import AlertManager

from core.event import Event
from core.event_types import EventType


_NO_CYCLE_REFERENCE = object()


class AnalysisPipeline:

    def __init__(
        self,
        event_bus=None,
        external_context_service=None,
        book_depth_service=None,
        psychology_state_provider=None,
        psychology_runtime=None,
        psychology_context_bridge=None,
        psychology_evidence_correlator=None,
        psychology_confirmation_audit=None,
        psychology_evidence_presenter=None,
        psychology_session_journal=None,
        *,
        temporal_external_policy=None,
        temporal_book_policy=None,
        temporal_reference_provider=None,
        temporal_primary_policy=None,
    ):
        if external_context_service is not None and not callable(
            getattr(external_context_service, "snapshot", None)
        ):
            raise TypeError("External context service deve expor snapshot().")
        if book_depth_service is not None and not callable(
            getattr(book_depth_service, "snapshot", None)
        ):
            raise TypeError("Book depth service deve expor snapshot(symbol).")
        if psychology_state_provider is not None and not callable(
            getattr(psychology_state_provider, "snapshot", None)
        ):
            raise TypeError(
                "Psychology state provider deve expor snapshot(context)."
            )
        if psychology_runtime is not None and not callable(
            getattr(psychology_runtime, "process", None)
        ):
            raise TypeError("Psychology runtime deve expor process(state).")
        if psychology_context_bridge is not None and not callable(
            getattr(psychology_context_bridge, "attach", None)
        ):
            raise TypeError("Psychology bridge deve expor attach(context, result).")
        if psychology_evidence_correlator is not None and not callable(
            getattr(psychology_evidence_correlator, "correlate", None)
        ):
            raise TypeError(
                "Psychology evidence correlator deve expor correlate()."
            )
        if psychology_confirmation_audit is not None and not hasattr(
            psychology_confirmation_audit,
            "entries",
        ):
            raise TypeError(
                "Psychology confirmation audit deve expor entries."
            )
        if (psychology_evidence_correlator is None) != (
            psychology_confirmation_audit is None
        ):
            raise TypeError(
                "Psychology evidence correlator e confirmation audit "
                "devem ser configurados juntos."
            )
        if psychology_evidence_presenter is not None and not callable(
            getattr(psychology_evidence_presenter, "enrich", None)
        ):
            raise TypeError(
                "Psychology evidence presenter deve expor enrich()."
            )
        if (
            psychology_evidence_presenter is not None
            and psychology_evidence_correlator is None
        ):
            raise TypeError(
                "Psychology evidence presenter exige correlator e audit."
            )
        if psychology_session_journal is not None and not callable(
            getattr(psychology_session_journal, "record", None)
        ):
            raise TypeError(
                "Psychology session journal deve expor record()."
            )

        if temporal_external_policy is not None and not isinstance(
            temporal_external_policy, TemporalSnapshotPolicy
        ):
            raise TypeError("INVALID_EXTERNAL_TEMPORAL_POLICY")

        if temporal_book_policy is not None and not isinstance(
            temporal_book_policy, TemporalSnapshotPolicy
        ):
            raise TypeError("INVALID_BOOK_TEMPORAL_POLICY")

        if temporal_primary_policy is not None and not isinstance(
            temporal_primary_policy, TemporalSnapshotPolicy
        ):
            raise TypeError("INVALID_PRIMARY_TEMPORAL_POLICY")

        if (
            temporal_reference_provider is not None
            and not callable(temporal_reference_provider)
        ):
            raise TypeError("INVALID_TEMPORAL_REFERENCE_PROVIDER")

        if (
            temporal_external_policy is not None
            or temporal_book_policy is not None
            or temporal_primary_policy is not None
        ) and temporal_reference_provider is None:
            raise ValueError("TEMPORAL_REFERENCE_PROVIDER_REQUIRED")

        self.temporal_external_policy = temporal_external_policy
        self.temporal_book_policy = temporal_book_policy
        self.temporal_primary_policy = temporal_primary_policy
        self.temporal_reference_provider = temporal_reference_provider

        self._temporal_external_history = TemporalSnapshotHistory()
        self._temporal_book_history = TemporalSnapshotHistory()
        self._temporal_primary_history = TemporalSnapshotHistory()
        self._temporal_cycle_reference = _NO_CYCLE_REFERENCE

        self.event_bus = event_bus
        self.external_context_service = external_context_service
        self.book_depth_service = book_depth_service
        self.psychology_state_provider = psychology_state_provider
        self.psychology_runtime = psychology_runtime or TraderPsychologyRuntime()
        self.psychology_context_bridge = (
            psychology_context_bridge or TraderPsychologyContextBridge()
        )
        self.psychology_evidence_correlator = psychology_evidence_correlator
        self.psychology_confirmation_audit = psychology_confirmation_audit
        self.psychology_evidence_presenter = psychology_evidence_presenter
        self.psychology_session_journal = psychology_session_journal
        self.context = AnalysisContext()

        self.book_diagnostics_replay = BookDiagnosticsReplayRecorder()
        self.score_regime_mtf_ab = ScoreRegimeMtfABRecorder()
        self.score_external_context_ab = ScoreExternalContextABRecorder()
        self.score_order_flow_ab = ScoreOrderFlowABRecorder()
        self.score_order_flow_structure_ab = ScoreOrderFlowStructureABRecorder()
        self.score_book_depth_ab = ScoreBookDepthABRecorder()
        self.score_microstructure_eligibility_ab = ScoreMicrostructureEligibilityABRecorder()
        self.microstructure_confluence_replay = MicrostructureConfluenceReplayRecorder()
        self.microstructure_eligibility_replay = MicrostructureEligibilityReplayRecorder()

        self.price_action_engines = [
            MarketRegime(),
            MultiTimeframeAnalysis(),
            MarketStructure(),
            LiquidityAnalysis(),
            VolumeAnalysis(),
            OrderFlow(),
            BookDepthAnalysis(),
            PriceAction(),
            BookDiagnosticsEngine(),
        ]
        self.smart_money_engines = [Imbalance(), OrderBlock(), FairValueGap(), LiquidityPool()]
        self.ai_engines = [ContextEngine(), StrategyEngine(), ScoreEngine(), RiskManager(), DecisionEngine(), AlertManager()]
        self.engines = self.price_action_engines + self.smart_money_engines + self.ai_engines
        self.engines.sort(key=lambda engine: engine.PRIORITY)

    def executar(self, context):
        if not isinstance(context, AnalysisContext):
            raise TypeError(
                "AnalysisPipeline esperava AnalysisContext, "
                f"recebeu {type(context).__name__}"
            )

        self.context = context
        # RC9.13: invalida resultados anteriores antes dos refreshes.
        self.context.clear_results()
        primary_policy = getattr(self, "temporal_primary_policy", None)
        previous_reference = getattr(
            self, "_temporal_cycle_reference", _NO_CYCLE_REFERENCE
        )
        self._temporal_cycle_reference = None
        try:
            if (
                getattr(self, "temporal_external_policy", None) is not None
                or getattr(self, "temporal_book_policy", None) is not None
                or primary_policy is not None
            ):
                self._temporal_cycle_reference = self._read_temporal_reference()
            if primary_policy is not None:
                stream = context.market.symbol.strip().upper()
                history = self._temporal_primary_history
                timestamp = context.source_timestamp
                temporal = validate_primary_quote_timestamp(
                    timestamp,
                    reference_timestamp=self._temporal_cycle_reference,
                    policy=primary_policy,
                    previous_timestamp=history.previous(None, stream),
                )
                if not temporal.accepted:
                    context.decision.add_reason(temporal.reason)
                    return context
                history.record(None, stream, timestamp)
            self._refresh_external_context()
            self._refresh_book_depth()
        finally:
            self._temporal_cycle_reference = previous_reference

        for engine in self.engines:
            if not engine.ENABLED:
                continue
            try:
                engine.executar(self.context)
                self._publish_engine(engine)
            except Exception:
                # RC9.6: nenhum resultado parcial pode sobreviver a uma
                # falha da engine ou da publicacao de seu evento.
                self.context.clear_results()
                raise

        # RC9.7: recorders sao observacionais. Cada um recebe um snapshot
        # independente para impedir alteracoes no contexto operacional oficial.
        # Uma falha de recorder invalida os resultados do ciclo (fail-closed).
        recorders = (
            self.book_diagnostics_replay,
            self.score_regime_mtf_ab,
            self.score_external_context_ab,
            self.score_order_flow_ab,
            self.score_order_flow_structure_ab,
            self.score_book_depth_ab,
            self.score_microstructure_eligibility_ab,
            self.microstructure_confluence_replay,
            self.microstructure_eligibility_replay,
        )
        try:
            for recorder in recorders:
                recorder.record(deepcopy(self.context))
        except Exception:
            self.context.clear_results()
            raise

        # A Psicologia roda somente depois do núcleo operacional e dos replays.
        # Ela anexa um snapshot observacional e nunca retroalimenta as engines.
        self._refresh_trader_psychology()
        try:
            self._publish_loop()
        except Exception:
            # RC9.12: falha na publicacao final invalida o ciclo.
            # Nenhum resultado operacional parcial deve permanecer.
            self.context.clear_results()
            raise
        return self.context


    def _read_temporal_reference(self):
        try:
            return self.temporal_reference_provider()
        except Exception:
            return None

    def _rc915_validate_temporal(
        self,
        *,
        timestamp,
        policy,
        history,
        service,
        stream=None,
    ):
        """Valida o snapshot antes da publicação, sem alterar o histórico."""
        if policy is None:
            return True, "TEMPORAL_POLICY_DISABLED"

        try:
            reference = getattr(
                self, "_temporal_cycle_reference", _NO_CYCLE_REFERENCE
            )
            if reference is _NO_CYCLE_REFERENCE:
                reference = self._read_temporal_reference()

            result = validate_snapshot_timestamp(
                timestamp,
                reference_timestamp=reference,
                policy=policy,
                previous_timestamp=history.previous(service, stream),
            )

            return result.accepted, result.reason

        except Exception:
            return False, "TEMPORAL_VALIDATION_ERROR"

    def _refresh_external_context(self) -> None:
        service = self.external_context_service
        if service is None:
            # RC9.14: sem fonte, dados anteriores nao sao atuais.
            self.context.external_market.clear()
            self.context.external_market.add_reason(
                'EXTERNAL_CONTEXT_SERVICE_UNAVAILABLE'
            )
            return
        try:
            state = service.snapshot()
        except Exception as exc:
            self.context.external_market.clear()
            self.context.external_market.add_reason(
                "Contexto externo indisponível: " f"{type(exc).__name__}."
            )
            return
        if not isinstance(state, ExternalMarketState):
            self.context.external_market.clear()
            self.context.external_market.add_reason(
                "ExternalContextService retornou estado inválido."
            )
            return
        policy = getattr(self, "temporal_external_policy", None)
        validate_temporal = policy is not None and state.valid
        if validate_temporal:
            timestamp = state.timestamp
            accepted, reason = self._rc915_validate_temporal(
                timestamp=timestamp,
                policy=policy,
                history=self._temporal_external_history,
                service=service,
            )

            if not accepted:
                self.context.external_market.clear()
                self.context.external_market.add_reason(reason)
                return

        published = deepcopy(state)
        self.context.external_market = published
        if validate_temporal:
            self._temporal_external_history.record(service, None, timestamp)

    def _refresh_book_depth(self) -> None:
        service = self.book_depth_service
        if service is None:
            # RC9.14: evita reutilizar Book de ciclo anterior.
            symbol = str(getattr(self.context.market, 'symbol', '') or '')
            self.context.book_depth = BookDepthSnapshot.unavailable(
                symbol=symbol,
                source='BOOK_DEPTH_SERVICE_UNAVAILABLE',
            )
            return
        symbol = str(getattr(self.context.market, "symbol", "") or "")
        try:
            snapshot = service.snapshot(symbol)
        except Exception:
            self.context.book_depth = BookDepthSnapshot.unavailable(
                symbol=symbol,
                source="BOOK_DEPTH_SERVICE_ERROR",
            )
            return
        if not isinstance(snapshot, BookDepthSnapshot):
            self.context.book_depth = BookDepthSnapshot.unavailable(
                symbol=symbol,
                source="BOOK_DEPTH_INVALID_SNAPSHOT",
            )
            return
        try:
            if not snapshot.available:
                if snapshot.bids or snapshot.asks:
                    raise ValueError("BOOK_DEPTH_UNAVAILABLE_WITH_LEVELS")
                self.context.book_depth = BookDepthSnapshot.unavailable(
                    symbol=snapshot.symbol,
                    source=snapshot.source,
                )
                return

            normalized = BookDepthSnapshot.build(
                symbol=snapshot.symbol,
                timestamp=snapshot.timestamp,
                bids=tuple(
                    (level.price, level.quantity, level.orders)
                    for level in snapshot.bids
                ),
                asks=tuple(
                    (level.price, level.quantity, level.orders)
                    for level in snapshot.asks
                ),
                source=snapshot.source,
            )
            if normalized.available != snapshot.available:
                raise ValueError("BOOK_DEPTH_AVAILABILITY_MISMATCH")
            policy = getattr(self, "temporal_book_policy", None)
            validate_temporal = policy is not None and normalized.available
            if validate_temporal:
                stream = (normalized.symbol, normalized.source)
                accepted, reason = self._rc915_validate_temporal(
                    timestamp=normalized.timestamp,
                    policy=policy,
                    history=self._temporal_book_history,
                    service=service,
                    stream=stream,
                )

                if not accepted:
                    self.context.book_depth = BookDepthSnapshot.unavailable(
                        symbol=symbol,
                        source=reason,
                    )
                    return

        except Exception:
            self.context.book_depth = BookDepthSnapshot.unavailable(
                symbol=symbol,
                source="BOOK_DEPTH_INVALID_CONTENT",
            )
            return

        self.context.book_depth = normalized
        if validate_temporal:
            self._temporal_book_history.record(service, stream, normalized.timestamp)

    def _refresh_trader_psychology(self) -> None:
        if self.psychology_state_provider is None:
            return
        try:
            state = self.psychology_state_provider.snapshot(deepcopy(self.context))
            if not isinstance(state, TraderPsychologyState):
                return
            runtime_result = self.psychology_runtime.process(state)
            evidence_correlator = getattr(
                self,
                "psychology_evidence_correlator",
                None,
            )
            confirmation_audit = getattr(
                self,
                "psychology_confirmation_audit",
                None,
            )
            if evidence_correlator is not None and confirmation_audit is not None:
                try:
                    evidence = evidence_correlator.correlate(
                        runtime_result,
                        confirmation_audit.entries,
                    )
                    runtime_result = replace(
                        runtime_result,
                        evidence=evidence,
                    )
                    evidence_presenter = getattr(
                        self,
                        "psychology_evidence_presenter",
                        None,
                    )
                    if evidence_presenter is not None:
                        try:
                            runtime_result = evidence_presenter.enrich(
                                runtime_result,
                                evidence,
                            )
                        except Exception:
                            # A apresentação é secundária e nunca invalida
                            # o relatório nem reenvia áudio.
                            pass
                except Exception:
                    # A evidência é explicativa e secundária: sua falha
                    # não apaga o snapshot psicológico principal.
                    pass
            session_journal = getattr(
                self,
                "psychology_session_journal",
                None,
            )
            if session_journal is not None:
                try:
                    session_journal.record(runtime_result)
                except Exception:
                    # O diário é observacional e nunca invalida o snapshot.
                    pass
            # RC9.8: bridge observacional opera em copia independente.
            # Somente o slot de psicologia e transferido ao contexto oficial.
            psychology_context = deepcopy(self.context)
            self.psychology_context_bridge.attach(
                psychology_context,
                runtime_result,
            )
            self.context.trader_psychology = deepcopy(
                psychology_context.trader_psychology
            )
        except Exception:
            # Fail-open operacional: psicologia indisponível não interfere
            # em Score, Risk, Decision, Alert ou execução de ordens.
            self.context.trader_psychology = None

    def _publish_engine(self, engine):
        if self.event_bus is None:
            return
        mapping = {
            MarketRegime: EventType.REGIME_UPDATED,
            MultiTimeframeAnalysis: EventType.MULTI_TIMEFRAME_UPDATED,
            MarketStructure: EventType.STRUCTURE_UPDATED,
            LiquidityAnalysis: EventType.LIQUIDITY_UPDATED,
            VolumeAnalysis: EventType.VOLUME_UPDATED,
            OrderFlow: EventType.ORDER_FLOW_UPDATED,
            PriceAction: EventType.PRICE_ACTION_UPDATED,
            BookDiagnosticsEngine: EventType.BOOK_DIAGNOSTICS_UPDATED,
            Imbalance: EventType.IMBALANCE_UPDATED,
            OrderBlock: EventType.ORDER_BLOCK_UPDATED,
            FairValueGap: EventType.FAIR_VALUE_GAP_UPDATED,
            LiquidityPool: EventType.LIQUIDITY_POOL_UPDATED,
            ContextEngine: EventType.CONTEXT_UPDATED,
            StrategyEngine: EventType.STRATEGY_UPDATED,
            ScoreEngine: EventType.SCORE_UPDATED,
            RiskManager: EventType.RISK_UPDATED,
            DecisionEngine: EventType.DECISION_UPDATED,
        }
        event_type = mapping.get(type(engine))
        if event_type is None:
            return
        # RC9.6: observadores recebem uma copia isolada, nunca o contexto
        # operacional que sera consumido pelas proximas engines.
        self.event_bus.publish(Event(event_type, deepcopy(self.context)))

    def _publish_loop(self):
        if self.event_bus is None:
            return
        # RC9.6: o encerramento tambem nao expoe o contexto original.
        self.event_bus.publish(Event(EventType.LOOP_COMPLETED, deepcopy(self.context)))
