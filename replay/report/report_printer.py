"""
Imprime o relatório do Replay.
"""


class ReportPrinter:

    def print(self, report):

        print()

        print("=" * 60)
        print("COPILOTO PRICE ACTION AI")
        print("=" * 60)

        print(f"Candles........: {report.candles}")
        print(f"Operações......: {report.operations}")
        print(f"Wins...........: {report.wins}")
        print(f"Losses.........: {report.losses}")
        print(f"Win Rate.......: {report.win_rate:.2f}%")
        print(f"Profit Factor..: {report.profit_factor:.2f}")
        print(f"Lucro Líquido..: {report.net_profit:.2f}")

        print("=" * 60)

        for name, stats in report.setups.items():

            print(name)

            print(
                f"  Operações : {stats['operations']}"
            )

            print(
                f"  Wins      : {stats['wins']}"
            )

            print(
                f"  Losses    : {stats['losses']}"
            )

            print()