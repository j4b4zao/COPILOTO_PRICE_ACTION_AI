
"""
analysis/market_structure.py

Engine responsável por identificar a estrutura
do mercado através de swings confirmados.

RC17 - CLOSED CANDLE STRUCTURE
"""

from ai.engine_base import EngineBase
from enums.trend import Trend


class MarketStructure(EngineBase):

    NAME = "MarketStructure"

    VERSION = "RC17-CLOSED-CANDLE"

    ENABLED = True

    PRIORITY = 20

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        # ======================================================
        # MERCADO
        # ======================================================

        if not market.ready:
            return context

        candles = market.candles.all()

        # ======================================================
        # O ÚLTIMO CANDLE ESTÁ EM FORMAÇÃO
        #
        # Portanto ele não participa da confirmação estrutural.
        # ======================================================

        if len(candles) < 6:
            return context

        closed_candles = candles[:-1]

        if len(closed_candles) < 5:
            return context

        result = context.structure

        # ======================================================
        # LIMPAR RESULTADO ANTERIOR
        # ======================================================

        result.clear()

        # ======================================================
        # DIAGNÓSTICO
        # ======================================================

        print()
        print("------------------------------------------------------------")
        print("MARKET STRUCTURE DIAGNOSTIC")
        print("------------------------------------------------------------")

        print(
            f"Candles recebidos : {len(candles)}"
        )

        print(
            f"Candles fechados  : {len(closed_candles)}"
        )

        print(
            "Candle atual      : excluído da confirmação"
        )

        print()

        for index, candle in enumerate(
            closed_candles,
            start=1,
        ):

            print(
                f"C{index:02d} | "
                f"O={candle.open:.2f} "
                f"H={candle.high:.2f} "
                f"L={candle.low:.2f} "
                f"C={candle.close:.2f}"
            )

        print("------------------------------------------------------------")

        # ======================================================
        # IDENTIFICAR SWINGS
        # ======================================================

        swing_highs = []

        swing_lows = []

        swing_high_indexes = []

        swing_low_indexes = []

        for i in range(
            2,
            len(closed_candles) - 2,
        ):

            current = closed_candles[i]

            left_1 = closed_candles[i - 1]

            left_2 = closed_candles[i - 2]

            right_1 = closed_candles[i + 1]

            right_2 = closed_candles[i + 2]

            # ==================================================
            # SWING HIGH
            # ==================================================

            is_swing_high = (

                current.high > left_1.high

                and current.high > left_2.high

                and current.high > right_1.high

                and current.high > right_2.high

            )

            if is_swing_high:

                swing_highs.append(
                    current.high
                )

                swing_high_indexes.append(
                    i + 1
                )

            # ==================================================
            # SWING LOW
            # ==================================================

            is_swing_low = (

                current.low < left_1.low

                and current.low < left_2.low

                and current.low < right_1.low

                and current.low < right_2.low

            )

            if is_swing_low:

                swing_lows.append(
                    current.low
                )

                swing_low_indexes.append(
                    i + 1
                )

        # ======================================================
        # DIAGNÓSTICO DOS SWINGS
        # ======================================================

        print()

        print(
            f"Swing Highs encontrados: "
            f"{len(swing_highs)}"
        )

        for index, price in zip(
            swing_high_indexes,
            swing_highs,
        ):

            print(
                f"  Swing High C{index}: "
                f"{price:.2f}"
            )

        print()

        print(
            f"Swing Lows encontrados: "
            f"{len(swing_lows)}"
        )

        for index, price in zip(
            swing_low_indexes,
            swing_lows,
        ):

            print(
                f"  Swing Low C{index}: "
                f"{price:.2f}"
            )

        print("------------------------------------------------------------")

        # ======================================================
        # NENHUM SWING
        # ======================================================

        if not swing_highs and not swing_lows:

            print(
                "RESULTADO: Nenhum swing confirmado."
            )

            print("------------------------------------------------------------")
            print()

            result.trend = Trend.UNKNOWN

            result.confidence = 0.0

            result.valid = False

            result.add_reason(
                "Nenhum swing confirmado."
            )

            return context

        # ======================================================
        # ÚLTIMOS SWINGS
        # ======================================================

        if swing_highs:

            result.swing_high = swing_highs[-1]

            result.last_high = swing_highs[-1]

        if swing_lows:

            result.swing_low = swing_lows[-1]

            result.last_low = swing_lows[-1]

        # ======================================================
        # ESTRUTURA DE ALTA
        # ======================================================

        higher_high = False

        higher_low = False

        if len(swing_highs) >= 2:

            previous_high = swing_highs[-2]

            current_high = swing_highs[-1]

            if current_high > previous_high:

                higher_high = True

                result.hh = True

                result.add_reason(
                    "Higher High confirmado."
                )

        if len(swing_lows) >= 2:

            previous_low = swing_lows[-2]

            current_low = swing_lows[-1]

            if current_low > previous_low:

                higher_low = True

                result.hl = True

                result.add_reason(
                    "Higher Low confirmado."
                )

        # ======================================================
        # ESTRUTURA DE BAIXA
        # ======================================================

        lower_high = False

        lower_low = False

        if len(swing_highs) >= 2:

            previous_high = swing_highs[-2]

            current_high = swing_highs[-1]

            if current_high < previous_high:

                lower_high = True

                result.lh = True

                result.add_reason(
                    "Lower High confirmado."
                )

        if len(swing_lows) >= 2:

            previous_low = swing_lows[-2]

            current_low = swing_lows[-1]

            if current_low < previous_low:

                lower_low = True

                result.ll = True

                result.add_reason(
                    "Lower Low confirmado."
                )

        # ======================================================
        # TENDÊNCIA
        # ======================================================

        if higher_high and higher_low:

            result.trend = Trend.UP

            result.confidence = 0.80

            result.add_reason(
                "Estrutura de alta confirmada."
            )

        elif lower_high and lower_low:

            result.trend = Trend.DOWN

            result.confidence = 0.80

            result.add_reason(
                "Estrutura de baixa confirmada."
            )

        elif swing_highs or swing_lows:

            result.trend = Trend.SIDEWAYS

            result.confidence = 0.40

            result.add_reason(
                "Estrutura sem tendência definida."
            )

        else:

            result.trend = Trend.UNKNOWN

            result.confidence = 0.0

        # ======================================================
        # ÚLTIMO CANDLE FECHADO
        # ======================================================

        last_closed_candle = closed_candles[-1]

        # ======================================================
        # BOS DE ALTA
        # ======================================================

        if (
            len(swing_highs) >= 1
            and last_closed_candle.close
            > swing_highs[-1]
        ):

            result.bos_up = True

            result.confidence = min(
                result.confidence + 0.10,
                1.0,
            )

            result.add_reason(
                "Break Of Structure de alta "
                "confirmado em candle fechado."
            )

        # ======================================================
        # BOS DE BAIXA
        # ======================================================

        if (
            len(swing_lows) >= 1
            and last_closed_candle.close
            < swing_lows[-1]
        ):

            result.bos_down = True

            result.confidence = min(
                result.confidence + 0.10,
                1.0,
            )

            result.add_reason(
                "Break Of Structure de baixa "
                "confirmado em candle fechado."
            )

        # ======================================================
        # CHOCH DE BAIXA
        # ======================================================

        if (
            len(swing_lows) >= 2
            and higher_high
            and last_closed_candle.close
            < swing_lows[-2]
        ):

            result.choch = True

            result.confidence = min(
                result.confidence + 0.10,
                1.0,
            )

            result.add_reason(
                "Change Of Character de baixa "
                "confirmado em candle fechado."
            )

        # ======================================================
        # CHOCH DE ALTA
        # ======================================================

        if (
            len(swing_highs) >= 2
            and lower_low
            and last_closed_candle.close
            > swing_highs[-2]
        ):

            result.choch = True

            result.confidence = min(
                result.confidence + 0.10,
                1.0,
            )

            result.add_reason(
                "Change Of Character de alta "
                "confirmado em candle fechado."
            )

        # ======================================================
        # DIAGNÓSTICO FINAL
        # ======================================================

        print()

        print("ESTRUTURA DETECTADA:")

        print(f"  HH       : {result.hh}")

        print(f"  HL       : {result.hl}")

        print(f"  LH       : {result.lh}")

        print(f"  LL       : {result.ll}")

        print(f"  Trend    : {result.trend}")

        print(f"  BOS UP   : {result.bos_up}")

        print(f"  BOS DOWN : {result.bos_down}")

        print(f"  CHOCH    : {result.choch}")

        print("------------------------------------------------------------")
        print()

        # ======================================================
        # RESULTADO
        # ======================================================

        result.valid = True

        return context

