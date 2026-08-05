"""
Trend Validator

RC6
"""

from enums.trend import Trend


class TrendValidator:

    @staticmethod
    def is_up(context):

        return context.structure.trend == Trend.UP

    @staticmethod
    def is_down(context):

        return context.structure.trend == Trend.DOWN

    @staticmethod
    def has_bos_up(context):

        return context.structure.bos_up

    @staticmethod
    def has_bos_down(context):

        return context.structure.bos_down

    @staticmethod
    def has_choch(context):

        return context.structure.choch

    @staticmethod
    def is_trending(context):

        return context.structure.trend != Trend.UNKNOWN