"""Testes da dinâmica Spike and Channel do capítulo 21."""

from analysis.price_action.spike_channel_dynamics import SpikeChannelDynamics
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def current_bar():
    return candle(0, 1000, -1000, 0)


def bullish_spike_channel():
    closed = [
        candle(100, 104, 99, 103),
        candle(103, 108, 102, 107),
        candle(107, 112, 106, 111),
        candle(111, 112, 108, 109),
        candle(109, 111, 108, 110),
        candle(110, 113, 109, 112),
        candle(112, 114, 111, 113),
        candle(113, 114, 112, 113.5),
    ]
    return [*closed, current_bar()]


def bearish_spike_channel():
    closed = [
        candle(120, 121, 116, 117),
        candle(117, 118, 112, 113),
        candle(113, 114, 108, 109),
        candle(109, 112, 108, 111),
        candle(111, 112, 109, 110),
        candle(110, 111, 106, 107),
        candle(107, 108, 104, 105),
        candle(105, 106, 103, 104),
    ]
    return [*closed, current_bar()]


def test_detecta_spike_e_canal_de_alta():
    metrics = SpikeChannelDynamics.analyze(bullish_spike_channel(), Trend.UP)
    assert metrics["brooks_spike_channel_valid"] is True
    assert metrics["brooks_spike_channel_direction"] == "UP"
    assert metrics["brooks_spike_channel_state"] == "CHANNEL"
    assert metrics["brooks_spike_pullback_detected"] is True
    assert metrics["brooks_channel_detected"] is True
    assert metrics["brooks_spike_channel_continuation"] is True


def test_detecta_spike_e_canal_de_baixa():
    metrics = SpikeChannelDynamics.analyze(bearish_spike_channel(), Trend.DOWN)
    assert metrics["brooks_spike_channel_valid"] is True
    assert metrics["brooks_spike_channel_direction"] == "DOWN"
    assert metrics["brooks_spike_channel_state"] == "CHANNEL"
    assert metrics["brooks_spike_pullback_detected"] is True
    assert metrics["brooks_channel_detected"] is True


def test_spike_sem_recuo_permanece_na_fase_spike():
    candles = [
        candle(100, 104, 99, 103),
        candle(103, 108, 102, 107),
        candle(107, 112, 106, 111),
        candle(111, 116, 110, 115),
        candle(115, 120, 114, 119),
        current_bar(),
    ]
    metrics = SpikeChannelDynamics.analyze(candles, Trend.UP)
    assert metrics["brooks_spike_channel_valid"] is True
    assert metrics["brooks_spike_channel_state"] == "SPIKE"
    assert metrics["brooks_spike_pullback_detected"] is False
    assert metrics["brooks_channel_detected"] is False


def test_recuo_apos_spike_sem_canal_suficiente():
    candles = [
        candle(100, 104, 99, 103),
        candle(103, 108, 102, 107),
        candle(107, 112, 106, 111),
        candle(111, 112, 108, 109),
        candle(109, 111, 108, 110),
        current_bar(),
    ]
    metrics = SpikeChannelDynamics.analyze(candles, Trend.UP)
    assert metrics["brooks_spike_channel_valid"] is True
    assert metrics["brooks_spike_channel_state"] == "PULLBACK_AFTER_SPIKE"
    assert metrics["brooks_spike_pullback_detected"] is True
    assert metrics["brooks_channel_detected"] is False


def test_mercado_lateral_nao_valida_padrao():
    metrics = SpikeChannelDynamics.analyze(bullish_spike_channel(), Trend.SIDEWAYS)
    assert metrics["brooks_spike_channel_valid"] is False
    assert metrics["brooks_spike_channel_state"] == "NONE"


def test_movimento_com_muita_sobreposicao_nao_e_spike():
    candles = [
        candle(100, 104, 99, 102),
        candle(101, 105, 100, 103),
        candle(102, 106, 101, 104),
        candle(103, 107, 102, 105),
        candle(104, 108, 103, 106),
        candle(105, 109, 104, 107),
        current_bar(),
    ]
    metrics = SpikeChannelDynamics.analyze(candles, Trend.UP)
    assert metrics["brooks_spike_channel_valid"] is False


def test_projeta_movimento_medido_na_direcao_da_tendencia():
    metrics = SpikeChannelDynamics.analyze(bullish_spike_channel(), Trend.UP)
    assert metrics["brooks_spike_channel_measured_target"] > 0
    assert metrics["brooks_spike_channel_leg_equality_target"] > 0
    assert metrics["brooks_spike_channel_measured_target"] > 111


def test_canal_com_negociacao_dos_dois_lados_e_identificado():
    metrics = SpikeChannelDynamics.analyze(bullish_spike_channel(), Trend.UP)
    assert metrics["brooks_channel_two_sided"] is True


def test_candle_atual_nao_participa_da_confirmacao():
    baseline = bullish_spike_channel()
    metrics_a = SpikeChannelDynamics.analyze(baseline, Trend.UP)
    altered = baseline[:-1] + [candle(500, 900, 100, 150)]
    metrics_b = SpikeChannelDynamics.analyze(altered, Trend.UP)
    assert metrics_a == metrics_b


def test_reversal_watch_com_duas_barras_contra_no_final():
    candles = [
        candle(100, 104, 99, 103),
        candle(103, 108, 102, 107),
        candle(107, 112, 106, 111),
        candle(111, 112, 108, 109),
        candle(109, 113, 108, 112),
        candle(112, 114, 111, 113),
        candle(113, 114, 110, 111),
        candle(111, 112, 108, 109),
        current_bar(),
    ]
    metrics = SpikeChannelDynamics.analyze(candles, Trend.UP)
    assert metrics["brooks_spike_channel_valid"] is True
    assert metrics["brooks_spike_channel_reversal_watch"] is True
