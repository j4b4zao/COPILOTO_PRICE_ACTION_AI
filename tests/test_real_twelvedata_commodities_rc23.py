"""
tests/test_real_twelvedata_commodities_rc23.py

Teste REAL Twelve Data - endpoint /commodities.

RC2.3

Objetivo:
    Descobrir os instrumentos de commodity diretamente
    pelo endpoint oficial de commodities.

IMPORTANTE:
    Este teste NÃO altera mapa.
    Este teste NÃO seleciona símbolo automaticamente.
"""

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://api.twelvedata.com/commodities"


def consultar(params):

    query = urlencode(params)

    url = f"{BASE_URL}?{query}"

    request = Request(
        url,
        headers={
            "User-Agent": "COPILOTO_PRICE_ACTION_AI"
        },
        method="GET",
    )

    try:

        with urlopen(
            request,
            timeout=15,
        ) as response:

            status_code = response.status

            body = response.read().decode(
                "utf-8"
            )

            return status_code, body

    except HTTPError as exc:

        try:

            body = (
                exc.read()
                .decode("utf-8")
            )

        except Exception:

            body = ""

        return exc.code, body

    except URLError as exc:

        return None, str(exc)

    except Exception as exc:

        return None, str(exc)


def main():

    print()
    print("=" * 72)
    print("TESTE REAL TWELVE DATA: COMMODITIES RC2.3")
    print("=" * 72)

    api_key = os.getenv(
        "TWELVE_DATA_API_KEY"
    )

    print()
    print("API KEY")
    print("-" * 72)

    print(
        "TWELVE_DATA_API_KEY :",
        "configurada"
        if api_key
        else "não configurada",
    )

    if not api_key:

        print()
        print(
            "❌ API KEY NÃO CONFIGURADA"
        )

        return

    # ==========================================================
    # TESTE 1 — LISTA DE COMMODITIES
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE 1: /commodities")
    print("=" * 72)

    status_code, body = consultar(
        {
            "apikey": api_key,
        }
    )

    print()
    print(
        "HTTP STATUS :",
        status_code,
    )

    print()
    print("BODY")
    print("-" * 72)

    print(body)

    if status_code != 200:

        print()
        print(
            "❌ ENDPOINT /commodities "
            "NÃO DISPONÍVEL"
        )

        return

    try:

        data = json.loads(body)

    except Exception:

        print()
        print(
            "❌ RESPOSTA NÃO É JSON"
        )

        return

    commodities = data.get(
        "data",
        []
    )

    print()
    print("=" * 72)
    print("RESULTADO DA LISTA")
    print("=" * 72)

    print()
    print(
        "COUNT :",
        len(commodities),
    )

    # ==========================================================
    # FILTRO LOCAL WTI / OIL
    # ==========================================================

    encontrados = []

    for item in commodities:

        texto = " ".join(
            [
                str(
                    item.get(
                        "symbol",
                        "",
                    )
                ),
                str(
                    item.get(
                        "name",
                        "",
                    )
                ),
                str(
                    item.get(
                        "description",
                        "",
                    )
                ),
                str(
                    item.get(
                        "category",
                        "",
                    )
                ),
            ]
        ).upper()

        if any(
            termo in texto
            for termo in [
                "WTI",
                "CRUDE OIL",
                "OIL",
            ]
        ):

            encontrados.append(
                item
            )

    print()
    print("=" * 72)
    print("CANDIDATOS OIL / WTI")
    print("=" * 72)

    print()
    print(
        "COUNT :",
        len(encontrados),
    )

    for item in encontrados:

        print(item)

    # ==========================================================
    # TESTE 2 — FILTRO SYMBOL OIL
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE 2: /commodities?symbol=OIL")
    print("=" * 72)

    status_code, body = consultar(
        {
            "symbol": "OIL",
            "apikey": api_key,
        }
    )

    print()
    print(
        "HTTP STATUS :",
        status_code,
    )

    print()
    print("BODY")
    print("-" * 72)

    print(body)

    # ==========================================================
    # TESTE 3 — FILTRO SYMBOL WTI
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE 3: /commodities?symbol=WTI")
    print("=" * 72)

    status_code, body = consultar(
        {
            "symbol": "WTI",
            "apikey": api_key,
        }
    )

    print()
    print(
        "HTTP STATUS :",
        status_code,
    )

    print()
    print("BODY")
    print("-" * 72)

    print(body)

    # ==========================================================
    # RESULTADO FINAL
    # ==========================================================

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print()

    if encontrados:

        print(
            "✅ COMMODITIES OIL/WTI "
            "ENCONTRADAS"
        )

        print()
        print(
            "⚠️ NENHUM SÍMBOLO SERÁ "
            "SELECIONADO AUTOMATICAMENTE."
        )

    else:

        print(
            "⚠️ NENHUMA COMMODITY "
            "OIL/WTI ENCONTRADA NA LISTA."
        )


if __name__ == "__main__":

    main()