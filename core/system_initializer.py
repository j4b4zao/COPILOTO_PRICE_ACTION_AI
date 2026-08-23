"""
core/system_initializer.py

Inicializa todos os módulos do COPILOTO PRICE ACTION AI.
"""

from core.connection_manager import ConnectionManager
from core.event_bus import EventBus

from market_data.collector import Collector

from validation.data_validator import DataValidator

from analysis.analysis_pipeline import AnalysisPipeline
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService

from risk.risk_manager import RiskManager
from filters.market_filter import MarketFilter
from risk.trade_quality import TradeQuality

from execution.signal_generator import SignalGenerator
from execution.execution_engine import ExecutionEngine

from monitor.monitor import Monitor

from alerts.alert_manager import AlertManager
from logs.trade_logger import TradeLogger


class SystemInitializer:

    def __init__(self, *, voice_enabled: bool = False):

        self.voice_enabled = bool(voice_enabled)

        # ==========================================
        # CONEXÃO
        # ==========================================

        self.connection = None
        self.collector = None

        # ==========================================
        # EVENTOS
        # ==========================================

        self.event_bus = None

        # ==========================================
        # VALIDAÇÃO
        # ==========================================

        self.validator = None

        # ==========================================
        # ANÁLISE
        # ==========================================

        self.pipeline = None

        # ==========================================
        # VOZ / APRESENTAÇÃO OPCIONAL
        # ==========================================

        self.voice = None

        # ==========================================
        # RISCO
        # ==========================================

        self.risk = None
        self.market_filter = None
        self.quality = None

        # ==========================================
        # EXECUÇÃO
        # ==========================================

        self.signal = None
        self.execution = None

        # ==========================================
        # MONITORAMENTO
        # ==========================================

        self.monitor = None
        self.alert = None
        self.logger = None

    # ==========================================================
    # INICIALIZAR
    # ==========================================================

    def inicializar(self):

        # ==========================================
        # CONEXÃO
        # ==========================================

        self.connection = ConnectionManager()
        self.collector = Collector()

        # ==========================================
        # EVENT BUS
        # ==========================================

        self.event_bus = EventBus()

        # ==========================================
        # VALIDAÇÃO
        # ==========================================

        self.validator = DataValidator()

        # ==========================================
        # ANÁLISE
        # ==========================================

        self.pipeline = AnalysisPipeline(
            event_bus=self.event_bus
        )

        # ==========================================
        # VOZ / APRESENTAÇÃO OPCIONAL
        # ==========================================

        self.voice = BookDiagnosticsVoiceService(
            enabled=self.voice_enabled
        )

        # ==========================================
        # RISCO
        # ==========================================

        self.risk = RiskManager()

        self.market_filter = MarketFilter()

        self.quality = TradeQuality()

        # ==========================================
        # EXECUÇÃO
        # ==========================================

        self.signal = SignalGenerator()

        self.execution = ExecutionEngine()

        # ==========================================
        # MONITORAMENTO
        # ==========================================

        self.monitor = Monitor()

        self.alert = AlertManager()

        self.logger = TradeLogger()

        return self
