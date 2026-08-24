from external_context.providers.semantic_discovery_runner import (
    SemanticDiscoveryRunner,
)


class FakeDiscovery:

    def __init__(
        self,
        responses,
    ):

        self.responses = dict(
            responses
        )

        self.queries = []

    def search(
        self,
        query,
    ):

        self.queries.append(
            query
        )

        return self.responses.get(
            query,
            {
                "status": "NOT_FOUND",
                "error": "",
                "results": [],
            },
        )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SEMANTIC DISCOVERY RUNNER RC2.3"
    )
    print("=" * 72)

    # ==========================================================
    # FOUND
    # ==========================================================

    print()
    print(
        "TESTE: FOUND"
    )
    print("-" * 72)

    discovery = FakeDiscovery(
        {
            "Nasdaq Composite": {
                "status": "FOUND",
                "error": "",
                "results": [
                    {
                        "symbol": "TEST_NASDAQ",
                        "name": (
                            "Nasdaq Composite Index"
                        ),
                        "type": "Index",
                        "country": "United States",
                    }
                ],
            }
        }
    )

    runner = (
        SemanticDiscoveryRunner(
            discovery
        )
    )

    result = runner.search(
        "NASDAQ"
    )

    print(result)

    assert (
        result["status"]
        == "FOUND"
    )

    assert (
        result["query"]
        == "Nasdaq Composite"
    )

    assert (
        result["candidate_count"]
        == 1
    )

    assert (
        discovery.queries
        == [
            "Nasdaq Composite"
        ]
    )

    print(
        "✅ FOUND APROVADO"
    )

    # ==========================================================
    # PRIMEIRA QUERY NOT_FOUND
    # SEGUNDA QUERY FOUND
    # ==========================================================

    print()
    print(
        "TESTE: FALLBACK DE QUERY"
    )
    print("-" * 72)

    discovery = FakeDiscovery(
        {
            "Nasdaq Composite": {
                "status": "NOT_FOUND",
                "error": "",
                "results": [],
            },
            "Nasdaq Composite Index": {
                "status": "FOUND",
                "error": "",
                "results": [
                    {
                        "symbol": "TEST_NASDAQ",
                        "name": (
                            "Nasdaq Composite Index"
                        ),
                        "type": "Index",
                        "country": "United States",
                    }
                ],
            },
        }
    )

    runner = (
        SemanticDiscoveryRunner(
            discovery
        )
    )

    result = runner.search(
        "NASDAQ"
    )

    print(result)

    assert (
        result["status"]
        == "FOUND"
    )

    assert (
        result["query"]
        == "Nasdaq Composite Index"
    )

    assert (
        discovery.queries
        == [
            "Nasdaq Composite",
            "Nasdaq Composite Index",
        ]
    )

    print(
        "✅ FALLBACK APROVADO"
    )

    # ==========================================================
    # UNAVAILABLE
    # ==========================================================

    print()
    print(
        "TESTE: UNAVAILABLE"
    )
    print("-" * 72)

    discovery = FakeDiscovery(
        {
            "S&P 500": {
                "status": "UNAVAILABLE",
                "error": (
                    "Plano superior necessário."
                ),
                "results": [],
            }
        }
    )

    runner = (
        SemanticDiscoveryRunner(
            discovery
        )
    )

    result = runner.search(
        "US500"
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
    # PROVIDER ERROR
    # ==========================================================

    print()
    print(
        "TESTE: PROVIDER ERROR"
    )
    print("-" * 72)

    discovery = FakeDiscovery(
        {
            "Nasdaq Composite": {
                "status": "PROVIDER_ERROR",
                "error": (
                    "API indisponível."
                ),
                "results": [],
            }
        }
    )

    runner = (
        SemanticDiscoveryRunner(
            discovery
        )
    )

    result = runner.search(
        "NASDAQ"
    )

    print(result)

    assert (
        result["status"]
        == "PROVIDER_ERROR"
    )

    print(
        "✅ PROVIDER ERROR APROVADO"
    )

    # ==========================================================
    # UNKNOWN
    # ==========================================================

    print()
    print(
        "TESTE: STATUS DESCONHECIDO"
    )
    print("-" * 72)

    discovery = FakeDiscovery(
        {
            "Nasdaq Composite": {
                "status": "UNKNOWN",
                "error": "",
                "results": [],
            }
        }
    )

    runner = (
        SemanticDiscoveryRunner(
            discovery
        )
    )

    result = runner.search(
        "NASDAQ"
    )

    print(result)

    assert (
        result["status"]
        == "PROVIDER_ERROR"
    )

    print(
        "✅ UNKNOWN BLOQUEADO"
    )

    # ==========================================================
    # CLEAR
    # ==========================================================

    print()
    print(
        "TESTE: CLEAR"
    )
    print("-" * 72)

    runner.clear()

    result = runner.snapshot()

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
        result["results"]
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
        "🏆 SEMANTIC DISCOVERY "
        "RUNNER RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()