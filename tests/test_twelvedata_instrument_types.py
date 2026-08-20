"""
tests/test_twelvedata_instrument_types.py

Consulta os tipos de instrumentos disponíveis
na Twelve Data.

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
        "apikey": api_key,
    }

    url = (
        f"{BASE_URL}/instrument_type?"
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
    print("TESTE REAL TWELVE DATA: INSTRUMENT TYPES")
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
        "endpoint     : /instrument_type"
    )

    payload = consultar(
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

    types = payload.get(
        "result",
        [],
    )

    print()
    print("TIPOS DISPONÍVEIS")
    print("-" * 72)

    for item in types:

        print(
            f"- {item}"
        )

    print()
    print(
        f"COUNT        : "
        f"{len(types)}"
    )

    # ==========================================================
    # VERIFICAÇÃO
    # ==========================================================

    print()
    print("=" * 72)

    if not types:

        print(
            "❌ NENHUM TIPO RETORNADO"
        )

        return

    print(
        "✅ INSTRUMENT TYPES DISPONÍVEIS"
    )

    print()
    print(
        "🏆 TWELVE DATA INSTRUMENT TYPES "
        "RC2 APROVADO"
    )


if __name__ == "__main__":

    main()