from external_context.providers.instrument_resolution_investigator import (
    InstrumentResolutionInvestigator,
)


class FakeDiscovery:

    def __init__(self):

        self.last_status = ""

        self.last_error = ""

        self.responses = {}

        self.queries = []

    def search(
        self,
        query,
    ):

        self.queries.append(
            query
        )

        response = self.responses.get(
            query,
            {
                "status": "NOT_FOUND",
                "results": [],
                "error": "",
            },
        )

        self.last_status = response[
            "status"
        ]

        self.last_error = response.get(
            "error",
            "",
        )

        return response.get(
            "results",
            [],
        )


def candidato(
    symbol,
    name,
    instrument_type,
    country="United States",
):

    return {
        "symbol": symbol,
        "name": name,
        "type": instrument_type,
        "exchange": "TEST",
        "mic_code": "TEST",
        "country": country,
        "currency": "USD",
    }


def main():

    print()
    print("=" * 72)
    print(
        "TESTE INSTRUMENT RESOLUTION "
        "INVESTIGATOR RC2.3"
    )
    print("=" * 72)

    # ==========================================================
    # INDEX VÁLIDO
    # ==========================================================

    print()
    print(
        "TESTE: INDEX VÁLIDO"
    )
    print("-" * 72)

    discovery = FakeDiscovery()

    discovery.responses[
        "Nasdaq Composite"
    ] = {
        "status": "FOUND",
        "error": "",
        "results": [
            candidato(
                "TEST_NASDAQ",
                "Nasdaq Composite Index",
                "Index",
            ),
            candidato(
                "ONEQ",
                "Fidelity Nasdaq Composite Index Fund",
                "ETF",
            ),
            candidato(
                "FNCMX",
                "Fidelity Nasdaq Composite Index Fund",
                "Mutual Fund",
            ),
            candidato(
                "FOREIGN",
                "Nasdaq Composite Index",
                "Index",
                "Germany",
            ),
        ],
    }

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    result = investigator.investigate(
        "NASDAQ",
        "Nasdaq Composite",
    )

    print(result)

    assert (
        result["status"]
        == "FOUND"
    )

    assert (
        len(
            result[
                "index_candidates"
            ]
        )
        == 1
    )

    assert (
        result[
            "index_candidates"
        ][0]["symbol"]
        == "TEST_NASDAQ"
    )

    print(
        "✅ INDEX VÁLIDO APROVADO"
    )

    # ==========================================================
    # ETF NÃO É INDEX
    # ==========================================================

    print()
    print(
        "TESTE: ETF NÃO É INDEX"
    )
    print("-" * 72)

    discovery = FakeDiscovery()

    discovery.responses[
        "Nasdaq Composite"
    ] = {
        "status": "FOUND",
        "error": "",
        "results": [
            candidato(
                "ONEQ",
                "Fidelity Nasdaq Composite Index Fund",
                "ETF",
            ),
        ],
    }

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    result = investigator.investigate(
        "NASDAQ",
        "Nasdaq Composite",
    )

    print(result)

    assert (
        result[
            "index_candidates"
        ]
        == []
    )

    assert (
        result[
            "investigated"
        ][0]["verdict"]
        == "ETF_CANDIDATE"
    )

    print(
        "✅ ETF BLOQUEADO COMO INDEX"
    )

    # ==========================================================
    # FUNDO NÃO É INDEX
    # ==========================================================

    print()
    print(
        "TESTE: FUND NÃO É INDEX"
    )
    print("-" * 72)

    discovery = FakeDiscovery()

    discovery.responses[
        "Nasdaq Composite"
    ] = {
        "status": "FOUND",
        "error": "",
        "results": [
            candidato(
                "FNCMX",
                "Fidelity Nasdaq Composite Index Fund",
                "Mutual Fund",
            ),
        ],
    }

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    result = investigator.investigate(
        "NASDAQ",
        "Nasdaq Composite",
    )

    print(result)

    assert (
        result[
            "index_candidates"
        ]
        == []
    )

    assert (
        result[
            "investigated"
        ][0]["verdict"]
        == "FUND_CANDIDATE"
    )

    print(
        "✅ FUND BLOQUEADO COMO INDEX"
    )

    # ==========================================================
    # PAÍS ESTRANGEIRO
    # ==========================================================

    print()
    print(
        "TESTE: INDEX ESTRANGEIRO"
    )
    print("-" * 72)

    discovery = FakeDiscovery()

    discovery.responses[
        "Nasdaq Composite"
    ] = {
        "status": "FOUND",
        "error": "",
        "results": [
            candidato(
                "FOREIGN",
                "Nasdaq Composite Index",
                "Index",
                "Germany",
            ),
        ],
    }

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    result = investigator.investigate(
        "NASDAQ",
        "Nasdaq Composite",
    )

    print(result)

    assert (
        result[
            "index_candidates"
        ]
        == []
    )

    assert (
        result[
            "investigated"
        ][0]["acceptance"]
        == "REJECTED"
    )

    print(
        "✅ INDEX ESTRANGEIRO BLOQUEADO"
    )

    # ==========================================================
    # NOT FOUND
    # ==========================================================

    print()
    print(
        "TESTE: NOT_FOUND"
    )
    print("-" * 72)

    discovery = FakeDiscovery()

    discovery.responses[
        "Nasdaq Composite"
    ] = {
        "status": "NOT_FOUND",
        "error": "",
        "results": [],
    }

    discovery.responses[
        "Nasdaq Composite Index"
    ] = {
        "status": "NOT_FOUND",
        "error": "",
        "results": [],
    }

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    result = investigator.investigate(
        "NASDAQ"
    )

    print(result)

    assert (
        result["status"]
        == "NOT_FOUND"
    )

    assert (
        result[
            "investigated"
        ]
        == []
    )

    print(
        "✅ NOT_FOUND APROVADO"
    )

    # ==========================================================
    # UNAVAILABLE
    # ==========================================================

    print()
    print(
        "TESTE: UNAVAILABLE"
    )
    print("-" * 72)

    discovery = FakeDiscovery()

    discovery.responses[
        "S&P 500"
    ] = {
        "status": "UNAVAILABLE",
        "error": (
            "Plano superior necessário."
        ),
        "results": [],
    }

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    result = investigator.investigate(
        "US500",
        "S&P 500",
    )

    print(result)

    assert (
        result["status"]
        == "UNAVAILABLE"
    )

    print(
        "✅ UNAVAILABLE APROVADO"
    )

    # ==========================================================
    # CLEAR
    # ==========================================================

    print()
    print(
        "TESTE: CLEAR"
    )
    print("-" * 72)

    investigator.clear()

    result = investigator.snapshot()

    print(result)

    assert (
        result["internal_symbol"]
        == ""
    )

    assert (
        result["status"]
        == ""
    )

    assert (
        result["candidate_count"]
        == 0
    )

    assert (
        result["investigated"]
        == []
    )

    print(
        "✅ CLEAR APROVADO"
    )

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 INSTRUMENT RESOLUTION "
        "INVESTIGATOR RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()