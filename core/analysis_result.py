class AnalysisResult:

    def __init__(self):

        # ==========================================
        # Dados do Mercado
        # ==========================================

        self.market = None
        self.candle = None

        # ==========================================
        # Análises
        # ==========================================

        self.structure = None
        self.price_action = None
        self.order_flow = None
        self.volume = None
        self.liquidity = None
        self.context = None

        # ==========================================
        # Estratégia
        # ==========================================

        self.setup = None
        self.strategy = None

        # ==========================================
        # Score
        # ==========================================

        self.score = 0
        self.confidence = 0
        self.quality = None

        # ==========================================
        # Filtros
        # ==========================================

        self.filter_result = None

        # ==========================================
        # Decisão
        # ==========================================

        self.decision = None
        self.signal = None

        # ==========================================
        # Execução
        # ==========================================

        self.trade_status = None
        self.risk = None

        # ==========================================
        # Alertas
        # ==========================================

        self.alert = None