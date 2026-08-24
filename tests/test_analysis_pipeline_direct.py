from market_data.collector import Collector
from analysis.analysis_pipeline import AnalysisPipeline


def main():

    print("=" * 72)
    print(" TESTE DIRETO ANALYSIS PIPELINE RC14 ")
    print("=" * 72)

    collector = Collector()

    print()
    print("COLETOR")
    print("-" * 72)

    context = collector.get_data()

    if context is None:

        print("❌ Collector não retornou contexto.")
        return

    print(
        f"Context type : "
        f"{type(context).__name__}"
    )

    print(
        f"Market symbol: "
        f"{context.market.symbol}"
    )

    print(
        f"Price        : "
        f"{context.market.last_price}"
    )

    print(
        f"Candles      : "
        f"{context.market.candle_count}"
    )

    print()
    print("ANALYSIS PIPELINE")
    print("-" * 72)

    pipeline = AnalysisPipeline()

    result = pipeline.executar(
        context
    )

    print()
    print(
        f"Result type  : "
        f"{type(result).__name__}"
    )

    print()
    print("RESULTADOS")
    print("-" * 72)

    print(
        f"Structure    : "
        f"{result.structure}"
    )

    print(
        f"Liquidity    : "
        f"{result.liquidity}"
    )

    print(
        f"Volume       : "
        f"{result.volume}"
    )

    print(
        f"Price Action : "
        f"{result.price_action}"
    )

    print(
        f"Context      : "
        f"{result.context}"
    )

    print(
        f"Strategy     : "
        f"{result.strategy}"
    )

    print(
        f"Score        : "
        f"{result.score}"
    )

    print(
        f"Risk         : "
        f"{result.risk}"
    )

    print(
        f"Decision     : "
        f"{result.decision}"
    )

    print()
    print("=" * 72)
    print("🏆 ANALYSIS PIPELINE EXECUTADO")
    print("=" * 72)


if __name__ == "__main__":

    main()