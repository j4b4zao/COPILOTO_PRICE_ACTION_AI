"""
analysis/setup_detector.py

Responsável por transformar as análises em setups.
"""


class SetupDetector:

    def __init__(self):

        self.enabled = True

    # ==================================================

    def executar(self, context):

        setup = context.setup

        setup.clear()

        structure = context.structure

        pa = context.price_action

        # ===============================================
        # BREAKOUT DE COMPRA
        # ===============================================

        if (

            structure.trend == "UP"

            and structure.bos

            and pa.bullish_engulfing

        ):

            setup.valid = True

            setup.name = "BREAKOUT"

            setup.direction = "BUY"

            setup.score = 90

            setup.confidence = 0.90

            setup.reasons.extend([

                "Tendência de alta",

                "BOS confirmado",

                "Engolfo comprador"

            ])

            return context

        # ===============================================
        # BREAKOUT DE VENDA
        # ===============================================

        if (

            structure.trend == "DOWN"

            and structure.bos

            and pa.bearish_engulfing

        ):

            setup.valid = True

            setup.name = "BREAKOUT"

            setup.direction = "SELL"

            setup.score = 90

            setup.confidence = 0.90

            setup.reasons.extend([

                "Tendência de baixa",

                "BOS confirmado",

                "Engolfo vendedor"

            ])

            return context

        # ===============================================
        # PULLBACK
        # ===============================================

        if pa.pullback:

            setup.valid = True

            setup.name = "PULLBACK"

            setup.score = 80

            setup.confidence = 0.80

            if structure.trend == "UP":

                setup.direction = "BUY"

            elif structure.trend == "DOWN":

                setup.direction = "SELL"

            setup.reasons.append("Pullback identificado")

        return context