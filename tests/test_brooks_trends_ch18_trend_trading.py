"""Testes do capítulo 18 de Trading Price Action Trends."""

from types import SimpleNamespace

from analysis.price_action.trend_trading_dynamics import TrendTradingDynamics
from enums.trend import Trend


def snapshot(**overrides):
    base = {
        "trend": Trend.UNKNOWN,
        "climax_active": False,
        "brooks_late_entry_climax_risk": False,
        "brooks_late_entry_reduce_position": False,
        "brooks_second_entry_detected": False,
        "brooks_second_entry_confirmed": False,
        "brooks_second_entry_direction": "NONE",
        "brooks_horizontal_breakout_pullback": False,
        "brooks_horizontal_break_direction": "NONE",
        "brooks_horizontal_state": "NO_LEVEL",
        "brooks_trend_line_valid": False,
        "brooks_trend_line_tested": False,
        "brooks_trend_line_broken": False,
        "brooks_microchannel_active": False,
        "brooks_microchannel_direction": "NONE",
        "brooks_microchannel_strength": "NONE",
        "brooks_close_direction": "NEUTRAL",
        "brooks_close_quality": "UNKNOWN",
        "brooks_close_confirmed": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def teste_sem_tendencia_nao_cria_entrada():
    metrics = TrendTradingDynamics.analyze(snapshot(trend=Trend.SIDEWAYS))

    assert metrics["brooks_trend_trade_state"] == "NO_TREND"
    assert metrics["brooks_trend_trade_valid"] is False
    assert metrics["brooks_trend_trade_confirmed"] is False


def teste_high_2_em_tendencia_de_alta_recebe_prioridade():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.UP,
            brooks_second_entry_detected=True,
            brooks_second_entry_direction="BUY",
        )
    )

    assert metrics["brooks_trend_trade_direction"] == "BUY"
    assert metrics["brooks_trend_trade_setup"] == "HIGH_2"
    assert metrics["brooks_trend_trade_entry_style"] == "STOP_ENTRY"
    assert metrics["brooks_trend_trade_quality"] == "HIGH"
    assert metrics["brooks_trend_trade_confirmed"] is True


def teste_low_2_em_tendencia_de_baixa_recebe_prioridade():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.DOWN,
            brooks_second_entry_confirmed=True,
            brooks_second_entry_direction="SELL",
        )
    )

    assert metrics["brooks_trend_trade_direction"] == "SELL"
    assert metrics["brooks_trend_trade_setup"] == "LOW_2"
    assert metrics["brooks_trend_trade_quality"] == "HIGH"


def teste_breakout_pullback_alinhado_e_setup_de_tendencia():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.UP,
            brooks_horizontal_breakout_pullback=True,
            brooks_horizontal_break_direction="UP",
        )
    )

    assert metrics["brooks_trend_trade_setup"] == "BREAKOUT_PULLBACK"
    assert metrics["brooks_trend_trade_breakout_pullback"] is True
    assert metrics["brooks_trend_trade_confirmed"] is True


def teste_pullback_em_linha_de_tendencia_e_reconhecido():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.DOWN,
            brooks_trend_line_valid=True,
            brooks_trend_line_tested=True,
            brooks_trend_line_broken=False,
        )
    )

    assert metrics["brooks_trend_trade_setup"] == "TREND_LINE_PULLBACK"
    assert metrics["brooks_trend_trade_entry_style"] == "LIMIT_OR_STOP"
    assert metrics["brooks_trend_trade_trend_line_pullback"] is True


def teste_microcanal_forte_permite_high_1():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.UP,
            brooks_microchannel_active=True,
            brooks_microchannel_direction="BUY",
            brooks_microchannel_strength="STRONG",
        )
    )

    assert metrics["brooks_trend_trade_strong_trend"] is True
    assert metrics["brooks_trend_trade_setup"] == "HIGH_1"
    assert metrics["brooks_trend_trade_quality"] == "MEDIUM"


def teste_breakout_de_swing_exige_tendencia_forte():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.DOWN,
            brooks_microchannel_active=True,
            brooks_microchannel_direction="SELL",
            brooks_microchannel_strength="VERY_STRONG",
            brooks_horizontal_state="BREAKOUT",
            brooks_horizontal_break_direction="DOWN",
        )
    )

    assert metrics["brooks_trend_trade_swing_breakout"] is True
    assert metrics["brooks_trend_trade_setup"] == "SWING_BREAKOUT"
    assert metrics["brooks_trend_trade_quality"] == "HIGH"


def teste_climax_bloqueia_entrada_agressiva_high_1():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.UP,
            climax_active=True,
            brooks_microchannel_active=True,
            brooks_microchannel_direction="BUY",
            brooks_microchannel_strength="STRONG",
        )
    )

    assert metrics["brooks_trend_trade_setup"] == "WAIT_AFTER_CLIMAX"
    assert metrics["brooks_trend_trade_entry_style"] == "WAIT"
    assert metrics["brooks_trend_trade_confirmed"] is False


def teste_entrada_tardia_reduz_qualidade_de_setup_forte():
    metrics = TrendTradingDynamics.analyze(
        snapshot(
            trend=Trend.UP,
            brooks_second_entry_detected=True,
            brooks_second_entry_direction="BUY",
            brooks_late_entry_reduce_position=True,
        )
    )

    assert metrics["brooks_trend_trade_setup"] == "HIGH_2"
    assert metrics["brooks_trend_trade_late_entry_risk"] is True
    assert metrics["brooks_trend_trade_quality"] == "MEDIUM"


def teste_tendencia_sem_setup_especifico_mantem_contexto_base():
    metrics = TrendTradingDynamics.analyze(snapshot(trend=Trend.UP))

    assert metrics["brooks_trend_trade_state"] == "TREND_CONTEXT"
    assert metrics["brooks_trend_trade_setup"] == "TREND_EXISTENCE"
    assert metrics["brooks_trend_trade_entry_style"] == "SMALL_WITH_TREND"
    assert metrics["brooks_trend_trade_confirmed"] is False
    assert metrics["brooks_trend_trade_countertrend_block"] is True


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("teste_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"OK - {test.__name__}")
