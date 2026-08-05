from market_data.collector import Collector
from core.analysis import Analysis


def main():

    print("=" * 60)
    print(" TESTE DO PIPELINE ")
    print("=" * 60)

    collector = Collector()
    analysis = Analysis()

    market_data = collector.get_data()

    if not market_data:
        print("❌ Nenhum dado recebido do Collector.")
        return

    print("\n✓ Dados recebidos com sucesso.\n")

    result = analysis.run(market_data)

    print("=" * 60)
    print("RESULTADO DA ANÁLISE")
    print("=" * 60)

    for key, value in result.items():
        print(f"\n{key.upper()}")
        print("-" * 40)
        print(value)

    print("\n")
    print("=" * 60)
    print("PIPELINE EXECUTADO COM SUCESSO")
    print("=" * 60)


if __name__ == "__main__":
    main()