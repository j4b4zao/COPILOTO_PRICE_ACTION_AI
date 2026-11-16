"""
tests/test_external_provider_robustness.py

Teste de robustez da camada externa.

Objetivo:

Garantir que dados ausentes, inválidos ou incompletos
não sejam interpretados como contexto válido.

Cenários:

1. Provider retorna None
2. Provider retorna tipo inválido
3. Dados incompletos
4. Dados com valores inválidos
5. Dados válidos
"""

from external_context.external_market_collector import (
    ExternalMarketCollector,
)

from external_context.external_context_engine import (
    ExternalContextEngine,
)


# ==============================================================
# DADOS VÁLIDOS
# ==============================================================

def dados_validos():

    return {
        "timestamp": "2026-08-17 11:00:00",

        "us500": 6400.0,
        "nasdaq": 23700.0,
        "dxy": 98.5,
        "vix": 15.0,
        "us10y": 4.25,
        "oil": 65.0,
        "gold": 3350.0,

        "us500_change": 0.80,
        "nasdaq_change": 1.10,
        "dxy_change": -0.30,
        "vix_change": -4.00,

        "us10y_change": -0.50,
        "oil_change": 0.40,
        "gold_change": 0.20,
    }


# ==============================================================
# EXECUTAR TESTE
# ==============================================================

def _verificar_coleta(
    nome,
    dados,
    deve_ser_valido,
):

    print()
    print("=" * 72)
    print(
        f"TESTE ROBUSTEZ: {nome}"
    )
    print("=" * 72)

    state = ExternalMarketCollector().coletar(
        dados
    )

    print()
    print("COLLECTOR")
    print("-" * 72)

    print(
        f"valid        : "
        f"{state.valid}"
    )

    print(
        f"risk_on_off  : "
        f"{state.risk_on_off}"
    )

    print(
        f"global_bias  : "
        f"{state.global_bias}"
    )

    print(
        f"confidence   : "
        f"{state.confidence}"
    )

    print()
    print("REASONS")
    print("-" * 72)

    for reason in state.reasons:

        print(
            f"- {reason}"
        )

    # ----------------------------------------------------------
    # VALIDAÇÃO
    # ----------------------------------------------------------

    if state.valid != deve_ser_valido:

        print()
        print(
            "❌ RESULTADO: FALHOU"
        )

        print(
            f"Esperado valid={deve_ser_valido}, "
            f"obtido valid={state.valid}"
        )

        raise AssertionError(f"{nome}: esperado valid={deve_ser_valido}, obtido {state.valid}")

    print()
    print(
        "✅ RESULTADO: APROVADO"
    )

    return state


# ==============================================================
# TESTE NONE
# ==============================================================

def teste_none():

    _verificar_coleta(
        "PROVIDER RETORNOU NONE",
        None,
        False,
    )


# ==============================================================
# TESTE TIPO INVÁLIDO
# ==============================================================

def teste_tipo_invalido():

    _verificar_coleta(
        "TIPO DE DADO INVÁLIDO",
        "dados inválidos",
        False,
    )


# ==============================================================
# TESTE DADOS INCOMPLETOS
# ==============================================================

def teste_incompleto():

    dados = {
        "timestamp": "2026-08-17 11:05:00",

        "us500": 6400.0,
        "nasdaq": 23700.0,

        # DXY, VIX, US10Y, OIL e GOLD ausentes.
    }

    _verificar_coleta(
        "DADOS INCOMPLETOS",
        dados,
        False,
    )


# ==============================================================
# TESTE VALORES INVÁLIDOS
# ==============================================================

def teste_valores_invalidos():

    dados = dados_validos()

    dados["us500"] = -6400.0
    dados["vix"] = 0.0
    dados["dxy"] = -98.5

    _verificar_coleta(
        "VALORES INVÁLIDOS",
        dados,
        False,
    )


# ==============================================================
# TESTE VÁLIDO
# ==============================================================

def teste_valido():

    state = _verificar_coleta(
        "DADOS VÁLIDOS",
        dados_validos(),
        True,
    )

    # ----------------------------------------------------------
    # Agora o Engine pode interpretar.
    # ----------------------------------------------------------

    ExternalContextEngine().executar(
        state
    )

    print()
    print("ENGINE")
    print("-" * 72)

    print(
        f"risk_on_off  : "
        f"{state.risk_on_off}"
    )

    print(
        f"global_bias  : "
        f"{state.global_bias}"
    )

    print(
        f"confidence   : "
        f"{state.confidence:.3f}"
    )

    assert state.risk_on_off == "RISK_ON", state.risk_on_off

# ==============================================================
# MAIN
# ==============================================================

def main():
    teste_none()
    teste_tipo_invalido()
    teste_incompleto()
    teste_valores_invalidos()
    teste_valido()
    print("EXTERNAL PROVIDER ROBUSTNESS RC1 APROVADO")


if __name__ == "__main__":

    main()