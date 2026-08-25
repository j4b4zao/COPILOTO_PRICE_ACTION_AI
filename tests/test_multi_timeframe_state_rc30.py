"""
Testes controlados do contrato MultiTimeframeState RC3.0.

Não utiliza Excel, rede ou API externa.
"""

from datetime import datetime, timedelta

from core.analysis_context import AnalysisContext
from core.multi_timeframe_state import MultiTimeframeState


START = datetime(
    2026,
    8,
    20,
    10,
    0,
)


def atualizar(
    state,
    minute,
    price,
    volume,
):

    return state.update_tick(
        symbol="WINV26",
        price=price,
        cumulative_volume=volume,
        timestamp=START + timedelta(minutes=minute),
    )


def teste_fronteiras_independentes():

    state = MultiTimeframeState()

    first = atualizar(
        state,
        minute=0,
        price=100.0,
        volume=1000.0,
    )

    assert first == {
        "M1": True,
        "M5": True,
        "M15": True,
    }

    minute_1 = atualizar(
        state,
        minute=1,
        price=101.0,
        volume=1100.0,
    )

    assert minute_1 == {
        "M1": True,
        "M5": False,
        "M15": False,
    }

    minute_5 = atualizar(
        state,
        minute=5,
        price=102.0,
        volume=1200.0,
    )

    assert minute_5 == {
        "M1": True,
        "M5": True,
        "M15": False,
    }

    minute_15 = atualizar(
        state,
        minute=15,
        price=103.0,
        volume=1300.0,
    )

    assert minute_15 == {
        "M1": True,
        "M5": True,
        "M15": True,
    }

    assert state.get("M1").candle_count == 4
    assert state.get("M5").candle_count == 3
    assert state.get("M15").candle_count == 2


def teste_ohlc_sem_misturar_historicos():

    state = MultiTimeframeState()

    atualizar(state, 0, 100.0, 1000.0)
    atualizar(state, 1, 105.0, 1100.0)
    atualizar(state, 2, 95.0, 1200.0)

    m1 = state.get("M1")
    m5 = state.get("M5")
    m15 = state.get("M15")

    assert m1.candle_count == 3
    assert m5.candle_count == 1
    assert m15.candle_count == 1

    assert m1.last_candle.open == 95.0
    assert m1.last_candle.high == 95.0
    assert m1.last_candle.low == 95.0
    assert m1.last_candle.close == 95.0
    assert m1.last_candle.volume == 100.0

    assert m5.last_candle.open == 100.0
    assert m5.last_candle.high == 105.0
    assert m5.last_candle.low == 95.0
    assert m5.last_candle.close == 95.0
    assert m5.last_candle.volume == 200.0

    assert m15.last_candle.open == 100.0
    assert m15.last_candle.high == 105.0
    assert m15.last_candle.low == 95.0
    assert m15.last_candle.close == 95.0
    assert m15.last_candle.volume == 200.0

    assert m1.last_candle is not m5.last_candle
    assert m5.last_candle is not m15.last_candle


def teste_mercado_primario_m1():

    state = MultiTimeframeState()

    atualizar(state, 0, 100.0, 1000.0)

    assert state.primary is state.get("M1")
    assert state.primary.timeframe == "M1"
    assert state.get("m5").timeframe == "M5"
    assert state.get("m15").timeframe == "M15"


def teste_prontidao_independente():

    state = MultiTimeframeState()

    for minute in range(61):

        atualizar(
            state,
            minute=minute,
            price=100.0 + minute,
            volume=1000.0 + minute * 10.0,
        )

    assert state.is_ready("M1") is True
    assert state.is_ready("M5") is True
    assert state.is_ready("M15") is True
    assert state.all_ready is True

    assert state.get("M1").candle_count == 61
    assert state.get("M5").candle_count == 13
    assert state.get("M15").candle_count == 5


def teste_snapshot():

    state = MultiTimeframeState()

    atualizar(state, 0, 100.0, 1000.0)

    snapshot = state.snapshot()

    assert snapshot["name"] == "MultiTimeframeState"
    assert snapshot["version"] == "RC3.0"
    assert snapshot["primary_timeframe"] == "M1"
    assert snapshot["all_ready"] is False

    assert set(
        snapshot["timeframes"]
    ) == {
        "M1",
        "M5",
        "M15",
    }

    assert (
        snapshot["timeframes"]["M5"]["candle_count"]
        == 1
    )


def teste_analysis_context_e_reset():

    state = MultiTimeframeState()

    atualizar(state, 0, 100.0, 1000.0)

    context = AnalysisContext(
        market=state.primary,
        multi_timeframe=state,
    )

    assert context.market is state.primary
    assert context.multi_timeframe is state

    context.clear_results()

    assert state.get("M1").candle_count == 1
    assert state.get("M5").candle_count == 1
    assert state.get("M15").candle_count == 1

    context.reset()

    assert context.market is state.primary
    assert state.get("M1").candle_count == 0
    assert state.get("M5").candle_count == 0
    assert state.get("M15").candle_count == 0


def teste_validacoes():

    state = MultiTimeframeState()

    try:

        state.get("M2")

    except ValueError:

        pass

    else:

        raise AssertionError(
            "M2 deveria ser rejeitado."
        )

    invalid_updates = [
        {
            "symbol": "",
            "price": 100.0,
            "cumulative_volume": 1000.0,
            "timestamp": START,
        },
        {
            "symbol": "WINV26",
            "price": 0.0,
            "cumulative_volume": 1000.0,
            "timestamp": START,
        },
        {
            "symbol": "WINV26",
            "price": 100.0,
            "cumulative_volume": -1.0,
            "timestamp": START,
        },
        {
            "symbol": "WINV26",
            "price": 100.0,
            "cumulative_volume": 1000.0,
            "timestamp": "10:00",
        },
    ]

    for invalid in invalid_updates:

        try:

            state.update_tick(**invalid)

        except (TypeError, ValueError):

            continue

        raise AssertionError(
            f"Atualização inválida aceita: {invalid}"
        )


def main():

    print()
    print("=" * 72)
    print("TESTE MULTI TIMEFRAME STATE RC3.0")
    print("=" * 72)

    tests = [
        teste_fronteiras_independentes,
        teste_ohlc_sem_misturar_historicos,
        teste_mercado_primario_m1,
        teste_prontidao_independente,
        teste_snapshot,
        teste_analysis_context_e_reset,
        teste_validacoes,
    ]

    for test in tests:

        test()

        print(
            f"✅ {test.__name__}"
        )

    print()
    print("🏆 MULTI TIMEFRAME STATE RC3.0 APROVADO")


if __name__ == "__main__":

    main()
