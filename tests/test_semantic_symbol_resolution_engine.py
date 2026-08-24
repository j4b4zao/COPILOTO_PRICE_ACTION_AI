"""
tests/test_semantic_symbol_resolution_engine.py

Teste offline do SemanticSymbolResolutionEngine RC2.3.
"""

from external_context.providers.semantic_symbol_resolution_engine import (
    SemanticSymbolResolutionEngine,
)


class FakePipeline:

    def __init__(self):

        self.responses = {}

    def resolve(
        self,
        internal_symbol,
        candidates,
    ):

        return self.responses.get(
            internal_symbol,
            {
                "name": "SemanticSymbolResolutionPipeline",
                "version": "RC2.3",
                "internal_symbol": internal_symbol,
                "status": "NOT_FOUND",
                "symbol": None,
                "resolved": False,
                "confidence": 0.0,
                "reason": "Não encontrado.",
                "candidate_count": len(candidates),
            },
        )


def mapped(symbol, internal_symbol):

    return {
        "name": "SemanticSymbolResolutionPipeline",
        "version": "RC2.3",
        "internal_symbol": internal_symbol,
        "status": "MAPPED",
        "symbol": symbol,
        "resolved": True,
        "confidence": 1.0,
        "reason": "Candidato resolvido.",
        "candidate_count": 1,
    }


def unresolved(internal_symbol):

    return {
        "name": "SemanticSymbolResolutionPipeline",
        "version": "RC2.3",
        "internal_symbol": internal_symbol,
        "status": "UNRESOLVED",
        "symbol": None,
        "resolved": False,
        "confidence": 0.0,
        "reason": "Sem correspondência.",
        "candidate_count": 2,
    }


def ambiguous(internal_symbol):

    return {
        "name": "SemanticSymbolResolutionPipeline",
        "version": "RC2.3",
        "internal_symbol": internal_symbol,
        "status": "AMBIGUOUS",
        "symbol": None,
        "resolved": False,
        "confidence": 1.0,
        "reason": "Múltiplos candidatos.",
        "candidate_count": 2,
    }


def unavailable(internal_symbol):

    return {
        "name": "SemanticSymbolResolutionPipeline",
        "version": "RC2.3",
        "internal_symbol": internal_symbol,
        "status": "UNAVAILABLE",
        "symbol": None,
        "resolved": False,
        "confidence": 0.0,
        "reason": "Plano sem acesso.",
        "candidate_count": 0,
    }


def provider_error(internal_symbol):

    return {
        "name": "SemanticSymbolResolutionPipeline",
        "version": "RC2.3",
        "internal_symbol": internal_symbol,
        "status": "PROVIDER_ERROR",
        "symbol": None,
        "resolved": False,
        "confidence": 0.0,
        "reason": "Provider indisponível.",
        "candidate_count": 0,
    }


def not_found(internal_symbol):

    return {
        "name": "SemanticSymbolResolutionPipeline",
        "version": "RC2.3",
        "internal_symbol": internal_symbol,
        "status": "NOT_FOUND",
        "symbol": None,
        "resolved": False,
        "confidence": 0.0,
        "reason": "Nenhum candidato.",
        "candidate_count": 0,
    }


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SEMANTIC SYMBOL "
        "RESOLUTION ENGINE RC2.3"
    )
    print("=" * 72)

    pipeline = FakePipeline()

    pipeline.responses["OIL"] = mapped(
        "TEST_OIL",
        "OIL",
    )

    pipeline.responses["NASDAQ"] = unresolved(
        "NASDAQ"
    )

    pipeline.responses["DXY"] = ambiguous(
        "DXY"
    )

    pipeline.responses["US500"] = unavailable(
        "US500"
    )

    pipeline.responses["VIX"] = provider_error(
        "VIX"
    )

    pipeline.responses["GOLD"] = not_found(
        "GOLD"
    )

    engine = (
        SemanticSymbolResolutionEngine(
            pipeline
        )
    )

    # ==========================================================
    # MAPPED
    # ==========================================================

    print()
    print(
        "TESTE: MAPPED"
    )
    print("-" * 72)

    result = engine.resolve(
        "OIL",
        [
            {
                "symbol": "TEST_OIL",
                "name": "WTI Crude Oil",
                "type": "Commodity",
            }
        ],
    )

    print(result)

    assert (
        result["status"]
        == "MAPPED"
    )

    assert (
        result["symbol"]
        == "TEST_OIL"
    )

    assert (
        engine.resolved["OIL"]
        == "TEST_OIL"
    )

    print(
        "✅ MAPPED APROVADO"
    )

    # ==========================================================
    # UNRESOLVED
    # ==========================================================

    print()
    print(
        "TESTE: UNRESOLVED"
    )
    print("-" * 72)

    result = engine.resolve(
        "NASDAQ",
        [],
    )

    print(result)

    assert (
        result["status"]
        == "UNRESOLVED"
    )

    assert (
        result["symbol"]
        is None
    )

    assert (
        "NASDAQ"
        in engine.unresolved
    )

    assert (
        "NASDAQ"
        not in engine.resolved
    )

    print(
        "✅ UNRESOLVED BLOQUEADO"
    )

    # ==========================================================
    # AMBIGUOUS
    # ==========================================================

    print()
    print(
        "TESTE: AMBIGUOUS"
    )
    print("-" * 72)

    result = engine.resolve(
        "DXY",
        [],
    )

    print(result)

    assert (
        result["status"]
        == "AMBIGUOUS"
    )

    assert (
        result["symbol"]
        is None
    )

    assert (
        "DXY"
        in engine.ambiguous
    )

    assert (
        "DXY"
        not in engine.resolved
    )

    print(
        "✅ AMBIGUOUS BLOQUEADO"
    )

    # ==========================================================
    # UNAVAILABLE
    # ==========================================================

    print()
    print(
        "TESTE: UNAVAILABLE"
    )
    print("-" * 72)

    result = engine.resolve(
        "US500",
        [],
    )

    print(result)

    assert (
        result["status"]
        == "UNAVAILABLE"
    )

    assert (
        "US500"
        in engine.unavailable
    )

    assert (
        "US500"
        not in engine.resolved
    )

    print(
        "✅ UNAVAILABLE BLOQUEADO"
    )

    # ==========================================================
    # PROVIDER ERROR
    # ==========================================================

    print()
    print(
        "TESTE: PROVIDER_ERROR"
    )
    print("-" * 72)

    result = engine.resolve(
        "VIX",
        [],
    )

    print(result)

    assert (
        result["status"]
        == "PROVIDER_ERROR"
    )

    assert (
        "VIX"
        in engine.provider_errors
    )

    assert (
        "VIX"
        not in engine.resolved
    )

    print(
        "✅ PROVIDER_ERROR BLOQUEADO"
    )

    # ==========================================================
    # NOT FOUND
    # ==========================================================

    print()
    print(
        "TESTE: NOT_FOUND"
    )
    print("-" * 72)

    result = engine.resolve(
        "GOLD",
        [],
    )

    print(result)

    assert (
        result["status"]
        == "NOT_FOUND"
    )

    assert (
        "GOLD"
        in engine.not_found
    )

    assert (
        "GOLD"
        not in engine.resolved
    )

    print(
        "✅ NOT_FOUND BLOQUEADO"
    )

    # ==========================================================
    # MAPPED SEM SYMBOL
    # ==========================================================

    print()
    print(
        "TESTE: MAPPED SEM SYMBOL"
    )
    print("-" * 72)

    pipeline.responses[
        "BAD_MAPPED"
    ] = {
        "name": "SemanticSymbolResolutionPipeline",
        "version": "RC2.3",
        "internal_symbol": "BAD_MAPPED",
        "status": "MAPPED",
        "symbol": None,
        "resolved": True,
        "confidence": 1.0,
        "reason": "Inválido.",
        "candidate_count": 1,
    }

    result = engine.resolve(
        "BAD_MAPPED",
        [],
    )

    print(result)

    assert (
        result["status"]
        == "UNRESOLVED"
    )

    assert (
        result["symbol"]
        is None
    )

    assert (
        "BAD_MAPPED"
        not in engine.resolved
    )

    assert (
        "BAD_MAPPED"
        in engine.unresolved
    )

    print(
        "✅ MAPPED SEM SYMBOL BLOQUEADO"
    )

    # ==========================================================
    # RESOLVE MANY
    # ==========================================================

    print()
    print(
        "TESTE: RESOLVE MANY"
    )
    print("-" * 72)

    candidates = {
        "OIL": [
            {
                "symbol": "TEST_OIL",
                "name": "WTI Crude Oil",
                "type": "Commodity",
            }
        ],
        "NASDAQ": [],
        "US500": [],
        "DXY": [],
        "VIX": [],
        "GOLD": [],
    }

    snapshot = engine.resolve_many(
        candidates
    )

    print(
        "RESOLVIDOS"
    )
    print("-" * 72)

    print(
        snapshot["resolved"]
    )

    print()
    print(
        "UNAVAILABLE"
    )
    print("-" * 72)

    print(
        snapshot["unavailable"]
    )

    print()
    print(
        "AMBIGUOUS"
    )
    print("-" * 72)

    print(
        snapshot["ambiguous"]
    )

    print()
    print(
        "UNRESOLVED"
    )
    print("-" * 72)

    print(
        snapshot["unresolved"]
    )

    print()
    print(
        "PROVIDER ERRORS"
    )
    print("-" * 72)

    print(
        snapshot["provider_errors"]
    )

    print()
    print(
        "NOT FOUND"
    )
    print("-" * 72)

    print(
        snapshot["not_found"]
    )

    assert (
        snapshot["resolved"]
        == {
            "OIL": "TEST_OIL"
        }
    )

    assert (
        "NASDAQ"
        in snapshot["unresolved"]
    )

    assert (
        "US500"
        in snapshot["unavailable"]
    )

    assert (
        "DXY"
        in snapshot["ambiguous"]
    )

    assert (
        "VIX"
        in snapshot["provider_errors"]
    )

    assert (
        "GOLD"
        in snapshot["not_found"]
    )

    assert (
        snapshot["count"]
        == 1
    )

    print()
    print(
        "✅ RESOLVE MANY APROVADO"
    )

    # ==========================================================
    # MAPA FINAL
    # ==========================================================

    print()
    print(
        "TESTE: MAPA FINAL"
    )
    print("-" * 72)

    mapping = engine.mapping()

    print(
        mapping
    )

    assert mapping == {
        "OIL": "TEST_OIL"
    }

    print(
        "✅ MAPA FINAL APROVADO"
    )

    # ==========================================================
    # CLEAR
    # ==========================================================

    print()
    print(
        "TESTE: CLEAR"
    )
    print("-" * 72)

    engine.clear()

    snapshot = engine.snapshot()

    print(
        snapshot
    )

    assert (
        snapshot["resolved"]
        == {}
    )

    assert (
        snapshot["results"]
        == {}
    )

    assert (
        snapshot["count"]
        == 0
    )

    assert (
        snapshot["unavailable"]
        == []
    )

    assert (
        snapshot["ambiguous"]
        == []
    )

    assert (
        snapshot["unresolved"]
        == []
    )

    assert (
        snapshot["provider_errors"]
        == []
    )

    assert (
        snapshot["not_found"]
        == []
    )

    print(
        "✅ CLEAR APROVADO"
    )

    # ==========================================================
    # RESULTADO
    # ==========================================================

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SEMANTIC SYMBOL "
        "RESOLUTION ENGINE RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()