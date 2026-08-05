"""
Price Action Validator

RC6
"""


class PriceActionValidator:

    @staticmethod
    def has_pullback(context):

        return context.price_action.pullback

    @staticmethod
    def has_breakout(context):

        return context.price_action.breakout

    @staticmethod
    def has_hammer(context):

        return context.price_action.hammer

    @staticmethod
    def has_shooting_star(context):

        return context.price_action.shooting_star

    @staticmethod
    def has_bullish_engulfing(context):

        return context.price_action.bullish_engulfing

    @staticmethod
    def has_bearish_engulfing(context):

        return context.price_action.bearish_engulfing

    @staticmethod
    def has_buy_confirmation(context):

        return (

            context.price_action.hammer

            or

            context.price_action.bullish_engulfing

        )

    @staticmethod
    def has_sell_confirmation(context):

        return (

            context.price_action.shooting_star

            or

            context.price_action.bearish_engulfing

        )