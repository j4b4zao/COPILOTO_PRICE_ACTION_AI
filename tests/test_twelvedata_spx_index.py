"""
tests/test_twelvedata_spx_index.py

Validação controlada de SPX como índice.

RC2
"""

import json
import os

from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen


BASE_URL = (
    "https://api.twelvedata.com"
)


def consultar(
    api_key: str,
):

    params = {
        "symbol": "SPX",
        "type": "Index",
        "country": "United States",
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

        try:

            body = exc.read().decode(
                "utf-8"
            )

            print(
                f"BODY: {body}"
            )

        except Exception:

            pass

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
    print("TESTE TWELVE DATA: SPX COMO INDEX")
    print("=" * 72)

    api_key = os.getenv(
        "TWELVE_DATA_API_KEY"
    )

    if not api_key:

        print(
            "❌ API KEY NÃO ENCONTRADA"
        )

        return

    print()
    print("REQUISIÇÃO")
    print("-" * 72)

    print(
        "symbol       : SPX"
    )

    print(
        "type         : Index"
    )

    print(
        "country      : United States"
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
            "❌ API REJEITOU A CONSULTA"
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
        "PRICE RETORNADO"
    )

    print(
        f"price        : "
        f"{payload.get('price')}"
    )

    print()
    print(
        "⚠️ PREÇO RETORNADO NÃO "
        "SIGNIFICA VALIDAÇÃO AUTOMÁTICA."
    )

    print(
        "Ainda precisamos confirmar "
        "os metadados do instrumento."
    )


if __name__ == "__main__":

    main()