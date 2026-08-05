
"""
core/event_types.py

Eventos oficiais do
COPILOTO PRICE ACTION AI.

RC13
"""


class EventType:

    # ==========================================================
    # LOOP
    # ==========================================================

    LOOP_STARTED = "LOOP_STARTED"

    LOOP_COMPLETED = "LOOP_COMPLETED"

    # ==========================================================
    # MERCADO
    # ==========================================================

    MARKET_UPDATED = "MARKET_UPDATED"

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    STRUCTURE_UPDATED = "STRUCTURE_UPDATED"

    LIQUIDITY_UPDATED = "LIQUIDITY_UPDATED"

    VOLUME_UPDATED = "VOLUME_UPDATED"

    PRICE_ACTION_UPDATED = "PRICE_ACTION_UPDATED"

    # ==========================================================
    # SMART MONEY
    # ==========================================================

    IMBALANCE_UPDATED = "IMBALANCE_UPDATED"

    ORDER_BLOCK_UPDATED = "ORDER_BLOCK_UPDATED"

    FAIR_VALUE_GAP_UPDATED = "FAIR_VALUE_GAP_UPDATED"

    LIQUIDITY_POOL_UPDATED = "LIQUIDITY_POOL_UPDATED"

    # Próximos módulos

    BREAKER_BLOCK_UPDATED = "BREAKER_BLOCK_UPDATED"

    MITIGATION_BLOCK_UPDATED = "MITIGATION_BLOCK_UPDATED"

    DISPLACEMENT_UPDATED = "DISPLACEMENT_UPDATED"

    PREMIUM_DISCOUNT_UPDATED = "PREMIUM_DISCOUNT_UPDATED"

    SMT_UPDATED = "SMT_UPDATED"

    # ==========================================================
    # IA
    # ==========================================================

    CONTEXT_UPDATED = "CONTEXT_UPDATED"

    STRATEGY_UPDATED = "STRATEGY_UPDATED"

    SCORE_UPDATED = "SCORE_UPDATED"

    RISK_UPDATED = "RISK_UPDATED"

    DECISION_UPDATED = "DECISION_UPDATED"

    # ==========================================================
    # ALERTAS
    # ==========================================================

    ALERT_CREATED = "ALERT_CREATED"

    ALERT_TRIGGERED = "ALERT_TRIGGERED"

    # ==========================================================
    # EXECUÇÃO
    # ==========================================================

    SIGNAL_GENERATED = "SIGNAL_GENERATED"

    ORDER_SENT = "ORDER_SENT"

    TRADE_OPENED = "TRADE_OPENED"

    TRADE_CLOSED = "TRADE_CLOSED"

    # ==========================================================
    # LOG
    # ==========================================================

    LOG_CREATED = "LOG_CREATED"

