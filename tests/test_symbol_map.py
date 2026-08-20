"""
tests/test_symbol_map.py

Teste do mapa interno de símbolos externos.

RC1
"""

from external_context.providers.symbol_map import (
    ExternalSymbolMap,
)


def main():

    print()
    print("=" * 72)
    print("TESTE SYMBOL MAP")
    print("=" * 72)

    erros = []

    # ==========================================================
    # VERSÃO
    # ==========================================================

    print()
    print("VERSÃO")
    print("-" * 72)

    print(
        f"version      : "
        f"{ExternalSymbolMap.VERSION}"
    )

    if not ExternalSymbolMap.VERSION:

        erros.append(
            "VERSION não definida."
        )

    # ==========================================================
    # ATIVOS
    # ==========================================================

    print()
    print("ATIVOS INTERNOS")
    print("-" * 72)

    for asset in ExternalSymbolMap.ALL:

        print(
            f"- {asset}"
        )

    # ==========================================================
    # QUANTIDADE
    # ==========================================================

    expected_assets = 7

    if len(
        ExternalSymbolMap.ALL
    ) != expected_assets:

        erros.append(
            "Quantidade de ativos diferente "
            "do esperado."
        )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    print()
    print("VALIDAÇÃO")
    print("-" * 72)

    for asset in ExternalSymbolMap.ALL:

        valid = (
            ExternalSymbolMap.is_valid(
                asset
            )
        )

        print(
            f"{asset:<10} : "
            f"{valid}"
        )

        if not valid:

            erros.append(
                f"{asset} deveria ser válido."
            )

    # ==========================================================
    # ATIVO DESCONHECIDO
    # ==========================================================

    unknown = "BTCUSD"

    unknown_valid = (
        ExternalSymbolMap.is_valid(
            unknown
        )
    )

    print()
    print(
        f"{unknown:<10} : "
        f"{unknown_valid}"
    )

    if unknown_valid:

        erros.append(
            "Ativo desconhecido foi aceito."
        )

    # ==========================================================
    # DUPLICIDADES
    # ==========================================================

    if len(
        set(ExternalSymbolMap.ALL)
    ) != len(
        ExternalSymbolMap.ALL
    ):

        erros.append(
            "Existem ativos duplicados."
        )

    # ==========================================================
    # RESULTADO
    # ==========================================================

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

        return

    print(
        "✅ RESULTADO: APROVADO"
    )

    print()
    print(
        "🏆 SYMBOL MAP RC1 APROVADO"
    )


if __name__ == "__main__":

    main()