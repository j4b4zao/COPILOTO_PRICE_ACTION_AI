"""
tests/test_twelvedata_auth.py

Teste mínimo de autenticação Twelve Data.

Não faz parte do pipeline do Copiloto.

RC2
"""

import json
import os
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.error import URLError


BASE_URL = "https://api.twelvedata.com"


def consultar(api_key: str):

    params = {
        "symbol": "AAPL",
        "apikey": api_key,
    }

    url = (
        f"{BASE_URL}/price?"
        f"{urlencode(params)}"
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "COPILOTO_PRICE_ACTION_AI/RC2"
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
            f"HTTP ERROR: "
            f"{exc.code} {exc.reason}"
        )

    except URLError as exc:

        print(
            f"URL ERROR: "
            f"{exc.reason}"
        )

    except Exception as exc:

        print(
            f"ERROR: {exc}"
        )

    return None


def main():

    print()
    print("=" * 72)
    print("TESTE TWELVE DATA: AUTENTICAÇÃO")
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
    print("TESTE")
    print("-" * 72)

    print(
        "endpoint     : /price"
    )

    print(
        "symbol       : AAPL"
    )

    payload = consultar(
        api_key
    )

    print()
    print("RESPOSTA")
    print("-" * 72)

    print(
        payload
    )

    print()
    print("=" * 72)

    if not isinstance(
        payload,
        dict,
    ):

        print(
            "❌ RESPOSTA INVÁLIDA"
        )

        return

    if (
        payload.get("status")
        == "error"
    ):

        print(
            "❌ API RETORNOU ERRO"
        )

        print(
            f"code         : "
            f"{payload.get('code')}"
        )

        print(
            f"message      : "
            f"{payload.get('message')}"
        )

        return

    if "price" not in payload:

        print(
            "❌ PRICE NÃO RETORNADO"
        )

        return

    print(
        "✅ AUTENTICAÇÃO/API CONFIRMADA"
    )

    print()
    print(
        f"Preço AAPL   : "
        f"{payload['price']}"
    )


if __name__ == "__main__":

    main()