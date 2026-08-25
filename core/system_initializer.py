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
from psychology.trader_psychology_session_provider import (
    TraderPsychologySessionProvider,
)
from psychology.trader_psychology_trade_event_bridge import (
    TraderPsychologyTradeEventBridge,
)


class SystemInitializer:

    def __init__(self, *, voice_enabled: bool | None = None, voice_config: VoiceConfig | None = None):
        config = validate_voice_config(voice_config or VoiceConfig())
        if voice_enabled is not None:
            config = config.with_updates(enabled=bool(voice_enabled))
        self.voice_config = config
        self.voice_enabled = config.enabled

        self.connection = None
        self.collector = None
        self.event_bus = None
        self.validator = None
        self.pipeline = None
        self.psychology_session = None
        self.psychology_trade_events = None
        self.voice = None
        self.risk = None
        self.market_filter = None
        self.quality = None
        self.signal = None
        self.execution = None
        self.monitor = None
        self.alert = None
        self.logger = None

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
        self.pipeline = AnalysisPipeline(
            event_bus=self.event_bus,
            psychology_state_provider=self.psychology_session,
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
