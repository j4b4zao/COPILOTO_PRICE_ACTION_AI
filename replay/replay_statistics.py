"""
Replay Statistics

RC6
"""

from replay.replay_result import ReplayResult


class ReplayStatistics:

    def __init__(self):

        self.result = ReplayResult()

    def register_operation(

        self,

        strategy,

        profit

    ):

        self.result.operations += 1

        if profit >= 0:

            self.result.wins += 1

            self.result.gross_profit += profit

        else:

            self.result.losses += 1

            self.result.gross_loss += abs(profit)

        name = strategy.name

        if name not in self.result.setups:

            self.result.setups[name] = {

                "operations": 0,

                "wins": 0,

                "losses": 0,

            }

        stats = self.result.setups[name]

        stats["operations"] += 1

        if profit >= 0:

            stats["wins"] += 1

        else:

            stats["losses"] += 1

    def finish(self):

        self.result.calculate()

        return self.result