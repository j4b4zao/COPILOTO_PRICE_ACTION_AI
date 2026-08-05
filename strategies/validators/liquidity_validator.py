"""
Liquidity Validator

RC6
"""


class LiquidityValidator:

    @staticmethod
    def buy_side(context):

        return context.liquidity.buy_side

    @staticmethod
    def sell_side(context):

        return context.liquidity.sell_side

    @staticmethod
    def sweep_up(context):

        return context.liquidity.sweep_up

    @staticmethod
    def sweep_down(context):

        return context.liquidity.sweep_down