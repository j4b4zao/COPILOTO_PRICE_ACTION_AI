"""
Context Validator

RC6
"""


class ContextValidator:

    @staticmethod
    def is_valid(context):

        return context.context.valid

    @staticmethod
    def is_buy(context):

        return (

            context.context.valid

            and

            context.context.bias == "BUY"

        )

    @staticmethod
    def is_sell(context):

        return (

            context.context.valid

            and

            context.context.bias == "SELL"

        )

    @staticmethod
    def confidence(context):

        return context.context.confidence