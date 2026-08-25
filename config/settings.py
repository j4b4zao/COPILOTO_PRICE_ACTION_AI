"""
config/settings.py

Configurações globais do
COPILOTO PRICE ACTION AI.

RC9
"""

# ==========================================================
# EXCEL / PROFIT WORKBOOKS
# ==========================================================

# Cotação principal / OHLC / indicadores.
EXCEL_PATH = r"C:\COPILOTO_PRICE_ACTION_AI\Profit.xlsx"

# Times & Trades RTD dedicado para Order Flow observacional.
PROFIT_RTD_TIMES_TRADES_PATH = r"C:\COPILOTO_PRICE_ACTION_AI\times&trades.xlsx"

# Livro de Ofertas RTD dedicado. Ainda não é consumido pelo núcleo.
PROFIT_RTD_ORDER_BOOK_PATH = r"C:\COPILOTO_PRICE_ACTION_AI\livroOfertas.xlsx"

# ==========================================================
# MARKET
# ==========================================================

DEFAULT_TIMEFRAME = "M1"

# NORMAL mantém o gráfico temporal M1 como mercado principal.
# RENKO usa tijolos de preço e mantém M1/M5/M15 como contexto.
CHART_MODE = "NORMAL"

# Tamanho do tijolo em pontos do ativo. Para WIN, 20 pontos
# correspondem a quatro variações mínimas de 5 pontos.
RENKO_BRICK_SIZE = 20.0

MIN_HISTORY = 5

# ==========================================================
# ORDER FLOW / PROFIT RTD
# ==========================================================

# RC8: fonte deduplicada Times & Trades RTD. Desativada por padrão
# para preservar integralmente o fluxo legado de agressão do Profit.
ENABLE_PROFIT_RTD_ORDER_FLOW = False

# ==========================================================
# RISK
# ==========================================================

DEFAULT_STOP = 150.0

DEFAULT_TARGET = 300.0

DEFAULT_RR = 2.0

# ==========================================================
# SCORE
# ==========================================================

MIN_SCORE = 80

MAX_SCORE = 100

# Experimento RC4.5. Desativado por padrão: quando False, o
# comportamento e o breakdown do ScoreEngine permanecem iguais.
ENABLE_ORDER_FLOW_SCORE = False

# Bônus máximo experimental, aplicado apenas a padrão confirmado
# e alinhado com a direção da estratégia.
ORDER_FLOW_SCORE_WEIGHT = 5.0

# Experimento RC13.2. Desativado por padrão para preservar o
# comportamento oficial do score até concluirmos a validação A/B.
ENABLE_REGIME_MTF_SCORE = False

# Ajuste contextual máximo em pontos. O valor pode ser positivo ou
# negativo conforme confirmação/conflito, mas nunca excede este teto.
REGIME_MTF_SCORE_WEIGHT = 3.0

# ==========================================================
# REPLAY
# ==========================================================

ENABLE_REPLAY = True

SAVE_REPORT = True

# ==========================================================
# LOG
# ==========================================================

LOG_LEVEL = "INFO"

PRINT_CONSOLE = True
