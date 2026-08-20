"""
tests/test_twelvedata_indices.py

Consulta real do catálogo de índices
da Twelve Data.

Objetivo:
encontrar o S&P 500 no catálogo de índices.

Não seleciona automaticamente o símbolo.

RC1
"""

import json
import os
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.error import URLError


BASE_URL = (
    "https://api.twelvedata.com"
)


def consultar_indices(
    api_key: str,
):

    params = {
        "apikey": api_key,
        "outputsize": 120,
    }

    url = (
        f"{BASE_URL}/indices?"
        f"{urlencode(params)}"
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "COPILOTO_PRICE_ACTION_AI/RC1"
        },
    )

    try:

        with urlopen(
            request,
            timeout=10.0,
        ) as response:

            raw = response.read()

        return json.loads(
            raw.decode("utf-8")
        )

    except HTTPError as exc:

        print(
            f"HTTP ERROR: {exc.code} "
            f"{exc.reason}"
        )

    except URLError as exc:

        print(
            f"URL ERROR: {exc.reason}"
        )

    except Exception as exc:

        print(
            f"ERROR: {exc}"
        )

    return None


def main():

    print()
    print("=" * 72)
    print("TESTE REAL TWELVE DATA: ÍNDICES")
    print("=" * 72)

    api_key = os.getenv(
        "TWELVE_DATA_API_KEY"
    )

    if not api_key:

        print()
        print(
            "❌ API KEY NÃO ENCONTRADA"
        )

        return

    print()
    print("API KEY")
    print("-" * 72)

    print(
        "TWELVE_DATA_API_KEY : configurada"
    )

    print()
    print("CONSULTA")
    print("-" * 72)

    print(
        "endpoint     : /indices"
    )

    payload = consultar_indices(
        api_key
    )

    if not isinstance(
        payload,
        dict,
    ):

        print()
        print(
            "❌ RESPOSTA INVÁLIDA"
        )

        return

    print()
    print(
        f"status       : "
        f"{payload.get('status')}"
    )

    if (
        payload.get("status")
        == "error"
    ):

        print(
            f"message      : "
            f"{payload.get('message', '')}"
        )

        return

    data = payload.get(
        "data",
        [],
    )

    print(
        f"resultados   : "
        f"{len(data)}"
    )

    # ==========================================================
    # PROCURAR S&P 500
    # ==========================================================

    print()
    print("CANDIDATOS S&P 500")
    print("-" * 72)

    encontrados = []

    for item in data:

        if not isinstance(
            item,
            dict,
        ):

            continue

        text = (
            f"{item.get('symbol', '')} "
            f"{item.get('name', '')}"
        ).upper()

        if (
            "S&P 500" in text
            or "S&P500" in text
            or "SP500" in text
        ):

            encontrados.append(
                item
            )

    for index, item in enumerate(
        encontrados,
        start=1,
    ):

        print()
        print(
            f"[{index}]"
        )

        print(
            f"symbol       : "
            f"{item.get('symbol', '')}"
        )

        print(
            f"name         : "
            f"{item.get('name', '')}"
        )

        print(
            f"country      : "
            f"{item.get('country', '')}"
        )

        print(
            f"exchange     : "
            f"{item.get('exchange', '')}"
        )

        print(
            f"mic_code     : "
            f"{item.get('mic_code', '')}"
        )

        print(
            f"type         : "
            f"{item.get('type', '')}"
        )

        print(
            f"currency     : "
            f"{item.get('currency', '')}"
        )

    print()
    print("=" * 72)

    if not encontrados:

        print(
            "⚠️ S&P 500 NÃO ENCONTRADO "
            "NO CATÁLOGO."
        )

        print()
        print(
            "Não vamos inventar um símbolo."
        )

        return

    print(
        "✅ S&P 500 ENCONTRADO NO CATÁLOGO"
    )

    print()
    print(
        "⚠️ Ainda NÃO selecionar automaticamente."
    )

    print(
        "Vamos analisar os candidatos antes "
        "de gravar o ProviderSymbolMap."
    )


if __name__ == "__main__":

    main()