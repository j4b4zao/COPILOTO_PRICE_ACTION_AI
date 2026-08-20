"""
tests/test_external_market_collector.py

Teste controlado do ExternalMarketCollector RC1.

Objetivos:

- validar coleta;
- validar conversão numérica;
- validar timestamp;
- validar rejeição de dados inválidos.

Não utiliza internet.
"""

from external_context.external_market_collector import (
    ExternalMarketCollector,
)


def teste_dados_validos():

    print()
    print("=" * 72)
    print("TESTE COLLECTOR: DADOS VÁLIDOS")
    print("=" * 72)

    data = {
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

    state = ExternalMarketCollector().coletar(
        data
    )

    print()
    print("RESULTADO")
    print("-" * 72)

    print(
        f"valid        : {state.valid}"
    )

    print(
        f"timestamp    : {state.timestamp}"
    )

    print(
        f"US500        : {state.us500}"
    )

    print(
        f"NASDAQ       : {state.nasdaq}"
    )

    print(
        f"DXY          : {state.dxy}"
    )

    print(
        f"VIX          : {state.vix}"
    )

    print(
        f"US10Y        : {state.us10y}"
    )

    print(
        f"OIL          : {state.oil}"
    )

    print(
        f"GOLD         : {state.gold}"
    )

    print()
    print("REASONS")
    print("-" * 72)

    for reason in state.reasons:

        print(
            f"- {reason}"
        )

    errors = []

    if not state.valid:

        errors.append(
            "Dados válidos foram rejeitados."
        )

    if state.us500 != 6400.0:

        errors.append(
            "US500 incorreto."
        )

    if state.nasdaq != 23700.0:

        errors.append(
            "NASDAQ incorreto."
        )

    if state.dxy != 98.5:

        errors.append(
            "DXY incorreto."
        )

    if state.vix != 15.0:

        errors.append(
            "VIX incorreto."
        )

    if state.timestamp != "2026-08-17 10:00:00":

        errors.append(
            "Timestamp incorreto."
        )

    if errors:

        print()
        print("❌ TESTE FALHOU")

        for error in errors:

            print(
                f" - {error}"
            )

        return False

    print()
    print("✅ DADOS VÁLIDOS APROVADOS")

    return True


def teste_dados_invalidos():

    print()
    print("=" * 72)
    print("TESTE COLLECTOR: DADOS INVÁLIDOS")
    print("=" * 72)

    data = {
        "timestamp": "2026-08-17 10:05:00",

        "us500": 0,
        "nasdaq": 0,
        "dxy": 0,
        "vix": 0,
        "us10y": 0,
        "oil": 0,
        "gold": 0,
    }

    state = ExternalMarketCollector().coletar(
        data
    )

    print()
    print("RESULTADO")
    print("-" * 72)

    print(
        f"valid        : {state.valid}"
    )

    for reason in state.reasons:

        print(
            f"- {reason}"
        )

    if state.valid:

        print()
        print(
            "❌ TESTE FALHOU"
        )

        print(
            "Dados inválidos foram aceitos."
        )

        return False

    print()
    print(
        "✅ DADOS INVÁLIDOS REJEITADOS"
    )

    return True


def main():

    valid_ok = teste_dados_validos()

    invalid_ok = teste_dados_invalidos()

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print(
        f"VÁLIDOS   : "
        f"{'PASSOU' if valid_ok else 'FALHOU'}"
    )

    print(
        f"INVÁLIDOS : "
        f"{'PASSOU' if invalid_ok else 'FALHOU'}"
    )

    print()

    if valid_ok and invalid_ok:

        print(
            "🏆 EXTERNAL MARKET COLLECTOR RC1 APROVADO"
        )

    else:

        print(
            "⚠️ EXTERNAL MARKET COLLECTOR "
            "PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()