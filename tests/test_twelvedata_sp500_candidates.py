"""
tests/test_twelvedata_sp500_candidates.py

Investigação controlada de possíveis símbolos
do índice S&P 500 na Twelve Data.

RC2

IMPORTANTE:
Este teste NÃO seleciona automaticamente
nenhum símbolo.
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


CANDIDATOS = [
    "SPX",
    "SP500",
    "SPX500",
    "GSPC",
    "S&P500",
    "S&P 500",
    "US500",
]


def consultar(
    api_key: str,
    symbol: str,
):

    params = {
        "symbol": symbol,
        "apikey": api_key,
    }

    url = (
        f"{BASE_URL}/quote?"
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

        try:

            body = exc.read().decode(
                "utf-8"
            )

        except Exception:

            body = ""

        return {
            "status": "HTTP_ERROR",
            "code": exc.code,
            "message": str(
                exc.reason
            ),
            "body": body,
        }

    except URLError as exc:

        return {
            "status": "URL_ERROR",
            "message": str(
                exc.reason
            ),
        }

    except Exception as exc:

        return {
            "status": "ERROR",
            "message": str(
                exc
            ),
        }


def imprimir_resultado(
    symbol: str,
    payload: dict,
):

    print()
    print(
        f"[{symbol}]"
    )

    print("-" * 72)

    if not isinstance(
        payload,
        dict,
    ):

        print(
            "resposta      : inválida"
        )

        return

    print(
        f"status        : "
        f"{payload.get('status', '')}"
    )

    print(
        f"symbol        : "
        f"{payload.get('symbol', '')}"
    )

    print(
        f"name          : "
        f"{payload.get('name', '')}"
    )

    print(
        f"exchange      : "
        f"{payload.get('exchange', '')}"
    )

    print(
        f"mic_code       : "
        f"{payload.get('mic_code', '')}"
    )

    print(
        f"type          : "
        f"{payload.get('type', '')}"
    )

    print(
        f"country       : "
        f"{payload.get('country', '')}"
    )

    print(
        f"currency      : "
        f"{payload.get('currency', '')}"
    )

    print(
        f"close         : "
        f"{payload.get('close', '')}"
    )

    if payload.get(
        "status"
    ) == "HTTP_ERROR":

        print(
            f"HTTP code     : "
            f"{payload.get('code', '')}"
        )

        print(
            f"message       : "
            f"{payload.get('message', '')}"
        )

        print(
            f"body          : "
            f"{payload.get('body', '')}"
        )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE TWELVE DATA: "
        "CANDIDATOS S&P 500"
    )
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
    print("CONSULTANDO CANDIDATOS")
    print("-" * 72)

    for symbol in CANDIDATOS:

        payload = consultar(
            api_key,
            symbol,
        )

        imprimir_resultado(
            symbol,
            payload,
        )

    print()
    print("=" * 72)

    print(
        "⚠️ INVESTIGAÇÃO CONCLUÍDA"
    )

    print()
    print(
        "Nenhum candidato será "
        "selecionado automaticamente."
    )


if __name__ == "__main__":

    main()