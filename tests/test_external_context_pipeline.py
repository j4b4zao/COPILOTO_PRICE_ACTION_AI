"""
tests/test_external_context_pipeline.py

Teste de integração da camada de contexto externo.

Fluxo:

    dados
      ↓
    Collector
      ↓
    ExternalMarketState
      ↓
    ExternalContextEngine
      ↓
    RISK_ON / RISK_OFF / NEUTRAL

Não utiliza internet.

Não altera:

- AnalysisContext
- ScoreEngine
- RiskManager
- DecisionEngine
- AlertManager
"""


from external_context.external_market_collector import (
    ExternalMarketCollector,
)

from external_context.external_context_engine import (
    ExternalContextEngine,
)


# ==============================================================
# DADOS RISK ON
# ==============================================================

def dados_risk_on():

    return {
        "timestamp": "2026-08-17 10:00:00",

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
# DADOS RISK OFF
# ==============================================================

def dados_risk_off():

    return {
        "timestamp": "2026-08-17 10:05:00",

        "us500": 6250.0,
        "nasdaq": 23100.0,
        "dxy": 100.0,
        "vix": 21.0,
        "us10y": 4.40,
        "oil": 63.0,
        "gold": 3380.0,

        "us500_change": -1.20,
        "nasdaq_change": -1.50,
        "dxy_change": 0.70,
        "vix_change": 8.00,
        "us10y_change": 0.50,
        "oil_change": -1.00,
        "gold_change": 0.80,
    }


# ==============================================================
# DADOS NEUTRAL
# ==============================================================

def dados_neutral():

    return {
        "timestamp": "2026-08-17 10:10:00",

        "us500": 6350.0,
        "nasdaq": 23500.0,
        "dxy": 99.0,
        "vix": 17.0,
        "us10y": 4.30,
        "oil": 65.0,
        "gold": 3350.0,

        "us500_change": 0.50,
        "nasdaq_change": -0.40,
        "dxy_change": 0.20,
        "vix_change": -2.00,
        "us10y_change": 0.10,
        "oil_change": 0.00,
        "gold_change": 0.10,
    }


# ==============================================================
# EXECUTAR CENÁRIO
# ==============================================================

def executar_cenario(
    nome,
    dados,
    esperado_risk,
    esperado_bias,
):

    print()
    print("=" * 72)
    print(
        f"TESTE INTEGRAÇÃO EXTERNA: {nome}"
    )
    print("=" * 72)

    # ----------------------------------------------------------
    # COLLECTOR
    # ----------------------------------------------------------

    collector = ExternalMarketCollector()

    state = collector.coletar(
        dados
    )

    # ----------------------------------------------------------
    # EXIBIR ESTADO COLETADO
    # ----------------------------------------------------------

    print()
    print("COLLECTOR")
    print("-" * 72)

    print(
        f"valid        : "
        f"{state.valid}"
    )

    print(
        f"timestamp    : "
        f"{state.timestamp}"
    )

    print(
        f"US500        : "
        f"{state.us500}"
    )

    print(
        f"NASDAQ       : "
        f"{state.nasdaq}"
    )

    print(
        f"DXY          : "
        f"{state.dxy}"
    )

    print(
        f"VIX          : "
        f"{state.vix}"
    )

    # ----------------------------------------------------------
    # VALIDAÇÃO DA COLETA
    # ----------------------------------------------------------

    if not state.valid:

        print()
        print(
            "❌ RESULTADO: FALHOU"
        )

        print(
            "Collector rejeitou dados válidos."
        )

        for reason in state.reasons:

            print(
                f" - {reason}"
            )

        return False

    # ----------------------------------------------------------
    # ENGINE
    # ----------------------------------------------------------

    engine = ExternalContextEngine()

    state = engine.executar(
        state
    )

    # ----------------------------------------------------------
    # RESULTADO
    # ----------------------------------------------------------

    print()
    print("EXTERNAL CONTEXT ENGINE")
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
        f"{state.confidence:.3f}"
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

    erros = []

    if not state.valid:

        erros.append(
            "State deveria permanecer válido."
        )

    if state.risk_on_off != esperado_risk:

        erros.append(
            f"Risk esperado: "
            f"{esperado_risk}; "
            f"obtido: "
            f"{state.risk_on_off}"
        )

    if state.global_bias != esperado_bias:

        erros.append(
            f"Bias esperado: "
            f"{esperado_bias}; "
            f"obtido: "
            f"{state.global_bias}"
        )

    # ----------------------------------------------------------
    # RESULTADO DO CENÁRIO
    # ----------------------------------------------------------

    print()
    print("=" * 72)

    if erros:

        print(
            "❌ RESULTADO: FALHOU"
        )

        for erro in erros:

            print(
                f" - {erro}"
            )

        return False

    print(
        "✅ RESULTADO: APROVADO"
    )

    return True


# ==============================================================
# TESTE DE DADOS INVÁLIDOS
# ==============================================================

def executar_teste_dados_invalidos():

    print()
    print("=" * 72)
    print("TESTE INTEGRAÇÃO EXTERNA: DADOS INVÁLIDOS")
    print("=" * 72)

    dados = {
        "timestamp": "2026-08-17 10:15:00",

        "us500": 0,
        "nasdaq": 0,
        "dxy": 0,
        "vix": 0,
        "us10y": 0,
        "oil": 0,
        "gold": 0,

        "us500_change": 0,
        "nasdaq_change": 0,
        "dxy_change": 0,
        "vix_change": 0,
    }

    state = ExternalMarketCollector().coletar(
        dados
    )

    print()
    print("RESULTADO")
    print("-" * 72)

    print(
        f"valid        : "
        f"{state.valid}"
    )

    for reason in state.reasons:

        print(
            f"- {reason}"
        )

    if state.valid:

        print()
        print(
            "❌ RESULTADO: FALHOU"
        )

        print(
            "Dados inválidos foram aceitos."
        )

        return False

    print()
    print(
        "✅ DADOS INVÁLIDOS BLOQUEADOS"
    )

    return True


# ==============================================================
# MAIN
# ==============================================================

def main():

    risk_on_ok = executar_cenario(
        "RISK ON",
        dados_risk_on(),
        "RISK_ON",
        "BULLISH",
    )

    risk_off_ok = executar_cenario(
        "RISK OFF",
        dados_risk_off(),
        "RISK_OFF",
        "BEARISH",
    )

    neutral_ok = executar_cenario(
        "NEUTRAL",
        dados_neutral(),
        "NEUTRAL",
        "NEUTRAL",
    )

    invalid_ok = (
        executar_teste_dados_invalidos()
    )

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print(
        f"RISK ON      : "
        f"{'PASSOU' if risk_on_ok else 'FALHOU'}"
    )

    print(
        f"RISK OFF     : "
        f"{'PASSOU' if risk_off_ok else 'FALHOU'}"
    )

    print(
        f"NEUTRAL      : "
        f"{'PASSOU' if neutral_ok else 'FALHOU'}"
    )

    print(
        f"INVÁLIDOS    : "
        f"{'PASSOU' if invalid_ok else 'FALHOU'}"
    )

    print()

    if (
        risk_on_ok
        and risk_off_ok
        and neutral_ok
        and invalid_ok
    ):

        print(
            "🏆 EXTERNAL CONTEXT PIPELINE RC1 APROVADO"
        )

    else:

        print(
            "⚠️ EXTERNAL CONTEXT PIPELINE "
            "PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()