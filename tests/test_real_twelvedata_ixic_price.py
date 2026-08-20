"""
tests/test_real_twelvedata_ixic_price.py

Teste direto Twelve Data: IXIC via /price
RC2.3

Sem dependência externa de requests.
"""

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://api.twelvedata.com/price"


def main():

    print()
    print("=" * 72)
    print("TESTE REAL TWELVE DATA: IXIC / PRICE")
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

    params = urlencode(
        {
            "symbol": "IXIC",
            "apikey": api_key,
        }
    )

    url = (
        f"{BASE_URL}?{params}"
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "COPILOTO_PRICE_ACTION_AI"
            )
        },
        method="GET",
    )

    print()
    print("REQUISIÇÃO")
    print("-" * 72)

    print(
        "endpoint : /price"
    )

    print(
        "symbol   : IXIC"
    )

    try:

        with urlopen(
            request,
            timeout=15,
        ) as response:

            status_code = (
                response.status
            )

            body = response.read().decode(
                "utf-8"
            )

    except HTTPError as exc:

        status_code = exc.code

        try:

            body = (
                exc.read()
                .decode("utf-8")
            )

        except Exception:

            body = ""

    except URLError as exc:

        print()
        print(
            "❌ ERRO DE CONEXÃO"
        )

        print(
            "error :",
            exc,
        )

        return

    except Exception as exc:

        print()
        print(
            "❌ ERRO INESPERADO"
        )

        print(
            "error :",
            exc,
        )

        return

    print()
    print("HTTP")
    print("-" * 72)

    print(
        "status_code :",
        status_code,
    )

    print()
    print("BODY")
    print("-" * 72)

    print(body)

    print()
    print("=" * 72)
    print("RESULTADO")
    print("=" * 72)

    if status_code != 200:

        print()
        print(
            "⚠️ IXIC NÃO DISPONÍVEL "
            "COMO COTAÇÃO DIRETA"
        )

        return

    try:

        data = json.loads(
            body
        )

    except Exception:

        print()
        print(
            "❌ RESPOSTA NÃO É JSON"
        )

        return

    if (
        isinstance(data, dict)
        and "price" in data
    ):

        print()
        print(
            "✅ IXIC ACEITO PELO /price"
        )

        print(
            "PRICE :",
            data["price"],
        )

    else:

        print()
        print(
            "⚠️ /price NÃO RETORNOU "
            "UM PREÇO PARA IXIC"
        )


if __name__ == "__main__":

    main()