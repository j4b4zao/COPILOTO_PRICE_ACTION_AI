"""
core/system_initializer.py

Inicializa todos os módulos do COPILOTO PRICE ACTION AI.
"""

from core.connection_manager import ConnectionManager
from core.event_bus import EventBus
from market_data.collector import Collector
from validation.data_validator import DataValidator
from analysis.analysis_pipeline import AnalysisPipeline
from analysis.replay.book_diagnostics_voice_config import VoiceConfig, validate_voice_config
from analysis.replay.book_diagnostics_voice_service_rc97 import BookDiagnosticsVoiceServiceRC97
from risk.risk_manager import RiskManager
from filters.market_filter import MarketFilter
from risk.trade_quality import TradeQuality
from execution.signal_generator import SignalGenerator
from execution.execution_engine import ExecutionEngine
from monitor.monitor import Monitor
from alerts.alert_manager import AlertManager
from logs.trade_logger import TradeLogger
from psychology.psychology_voice_controlled_test import (
    PsychologyVoiceControlledTest,
)
from psychology.psychology_voice_readiness import (
    PsychologyVoiceReadiness,
)
from psychology.trader_psychology_confirmation_audit import (
    AuditedTraderPsychologyExecutionConfirmations,
    TraderPsychologyConfirmationAuditLedger,
)
from psychology.trader_psychology_evidence_correlator import (
    TraderPsychologyEvidenceCorrelator,
)
from psychology.trader_psychology_evidence_presenter import (
    TraderPsychologyEvidencePresenter,
)
from psychology.trader_psychology_execution_confirmation_adapter import (
    TraderPsychologyExecutionConfirmationAdapter,
)
from psychology.trader_psychology_runtime import TraderPsychologyRuntime
from psychology.trader_psychology_session_journal import (
    TraderPsychologySessionJournal,
)
from psychology.trader_psychology_session_provider import (
    TraderPsychologySessionProvider,
)
from psychology.trader_psychology_trade_event_bridge import (
    TraderPsychologyTradeEventBridge,
)
from psychology.trader_psychology_trade_event_publisher import (
    TraderPsychologyTradeEventPublisher,
)
from psychology.voice_assistant import (
    VoiceAssistant,
    VoiceAssistantConfig,
)


class SystemInitializer:

    def __init__(
        self,
        *,
        voice_enabled: bool | None = None,
        voice_config: VoiceConfig | None = None,
        psychology_voice_config: VoiceAssistantConfig | None = None,
        psychology_voice_sink=None,
    ):
        config = validate_voice_config(voice_config or VoiceConfig())
        if voice_enabled is not None:
            config = config.with_updates(enabled=bool(voice_enabled))
        self.voice_config = config
        self.voice_enabled = config.enabled

        psychology_config = (
            psychology_voice_config or VoiceAssistantConfig()
        )
        if not isinstance(psychology_config, VoiceAssistantConfig):
            raise TypeError(
                "psychology_voice_config deve ser VoiceAssistantConfig."
            )
        if psychology_voice_sink is not None and not callable(
            getattr(psychology_voice_sink, "speak", None)
        ):
            raise TypeError(
                "psychology_voice_sink deve expor speak()."
            )
        if psychology_config.enabled and psychology_voice_sink is None:
            raise ValueError(
                "Voz psicológica habilitada exige sink explícito."
            )
        self.psychology_voice_config = psychology_config
        self.psychology_voice_sink = psychology_voice_sink
        self.psychology_voice = VoiceAssistant(
            config=psychology_config,
            sink=psychology_voice_sink,
        )
        self.psychology_runtime = TraderPsychologyRuntime(
            voice_assistant=self.psychology_voice,
        )
        self.psychology_voice_readiness_service = (
            PsychologyVoiceReadiness()
        )
        self.psychology_voice_controlled_test = (
            PsychologyVoiceControlledTest(
                readiness=self.psychology_voice_readiness_service,
            )
        )

        self.connection = None
        self.collector = None
        self.event_bus = None
        self.validator = None
        self.pipeline = None
        self.psychology_session = None
        self.psychology_trade_events = None
        self.psychology_trade_publisher = None
        self.psychology_execution_confirmations = None
        self.psychology_confirmation_audit = None
        self.psychology_audited_confirmations = None
        self.psychology_evidence_correlator = None
        self.psychology_evidence_presenter = None
        self.psychology_session_journal = None
        self.voice = None
        self.risk = None
        self.market_filter = None
        self.quality = None
        self.signal = None
        self.execution = None
        self.monitor = None
        self.alert = None
        self.logger = None

    def psychology_voice_readiness(self):
        return self.psychology_voice_readiness_service.inspect(
            config=self.psychology_voice_config,
            sink=self.psychology_voice_sink,
        )

    def test_psychology_voice(self, confirmation=""):
        return self.psychology_voice_controlled_test.run(
            config=self.psychology_voice_config,
            sink=self.psychology_voice_sink,
            confirmation=confirmation,
        )

    def inicializar(self):
        self.connection = ConnectionManager()
        self.collector = Collector()
        self.event_bus = EventBus()
        self.validator = DataValidator()

        self.psychology_session = TraderPsychologySessionProvider()
        self.psychology_trade_events = TraderPsychologyTradeEventBridge(
            event_bus=self.event_bus,
            session_provider=self.psychology_session,
        ).connect()
        self.psychology_trade_publisher = (
            TraderPsychologyTradeEventPublisher(
                event_bus=self.event_bus,
            )
        )
        self.psychology_execution_confirmations = (
            TraderPsychologyExecutionConfirmationAdapter(
                publisher=self.psychology_trade_publisher,
            )
        )
        self.psychology_confirmation_audit = (
            TraderPsychologyConfirmationAuditLedger()
        )
        self.psychology_audited_confirmations = (
            AuditedTraderPsychologyExecutionConfirmations(
                adapter=self.psychology_execution_confirmations,
                ledger=self.psychology_confirmation_audit,
            )
        )
        self.psychology_evidence_correlator = (
            TraderPsychologyEvidenceCorrelator()
        )
        self.psychology_evidence_presenter = (
            TraderPsychologyEvidencePresenter()
        )
        self.psychology_session_journal = (
            TraderPsychologySessionJournal()
        )
        self.pipeline = AnalysisPipeline(
            event_bus=self.event_bus,
            psychology_state_provider=self.psychology_session,
            psychology_runtime=self.psychology_runtime,
            psychology_evidence_correlator=(
                self.psychology_evidence_correlator
            ),
            psychology_confirmation_audit=(
                self.psychology_confirmation_audit
            ),
            psychology_evidence_presenter=(
                self.psychology_evidence_presenter
            ),
            psychology_session_journal=(
                self.psychology_session_journal
            ),
        )

        self.voice = BookDiagnosticsVoiceServiceRC97(config=self.voice_config)

        self.risk = RiskManager()
        self.market_filter = MarketFilter()
        self.quality = TradeQuality()
        self.signal = SignalGenerator()
        self.execution = ExecutionEngine()
        self.monitor = Monitor()
        self.alert = AlertManager()
        self.logger = TradeLogger()

        return self
