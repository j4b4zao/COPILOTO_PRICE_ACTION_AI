"""
Gera um relatório a partir das estatísticas.
"""

from replay.report.report_model import ReportModel


class ReportGenerator:

    def generate(self, statistics):

        report = ReportModel()

        result = statistics.result

        report.candles = result.candles
        report.operations = result.operations
        report.wins = result.wins
        report.losses = result.losses
        report.win_rate = result.win_rate
        report.profit_factor = result.profit_factor
        report.net_profit = result.net_profit
        report.setups = result.setups

        return report