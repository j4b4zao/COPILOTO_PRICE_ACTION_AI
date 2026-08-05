"""
analysis_result.py

Objeto central que transporta todas as informações
geradas durante o pipeline de análise.
"""


class AnalysisResult:

    def __init__(self):

        # =====================================
        # DADOS DO MERCADO
        # =====================================

        self.mercado = {}

        # =====================================
        # CANDLE ATUAL
        # =====================================

        self.candle = None

        # =====================================
        # ESTRUTURA DO MERCADO
        # =====================================

        self.estrutura = {}

        # =====================================
        # PRICE ACTION
        # =====================================

        self.price_action = {}

        # =====================================
        # SETUP
        # =====================================

        self.setup = {}

        # =====================================
        # SCORE
        # =====================================

        self.score = 0

        # =====================================
        # GESTÃO DE RISCO
        # =====================================

        self.risco = {}

        # =====================================
        # FILTRO DE MERCADO
        # =====================================

        self.filtro = {}

        # =====================================
        # QUALIDADE
        # =====================================

        self.qualidade = {}

        # =====================================
        # DECISÃO
        # =====================================

        self.decisao = {}

        # =====================================
        # SINAL
        # =====================================

        self.sinal = {}

        # =====================================
        # ALERTA
        # =====================================

        self.alerta = None

    def __repr__(self):

        return (
            "AnalysisResult("
            f"score={self.score}, "
            f"decisao={self.decisao}, "
            f"sinal={self.sinal})"
        )