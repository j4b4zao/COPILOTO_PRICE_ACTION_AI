"""
config/settings.py

Configurações globais do
COPILOTO PRICE ACTION AI.

RC7
"""

# ==========================================================
# EXCEL
# ==========================================================

EXCEL_PATH = r"C:\COPILOTO_PRICE_ACTION_AI\Profit.xlsx"

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
