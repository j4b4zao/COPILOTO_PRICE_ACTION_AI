"""
analysis/smart_money/fair_value_gap.py

Fair Value Gap Engine

RC12
FVG ativo baseado em histórico de candles fechados.
"""

from ai.engine_base import EngineBase


class FairValueGap(EngineBase):

    NAME = "FairValueGap"

    VERSION = "RC12"

    ENABLED = True

    PRIORITY = 55

    # ==========================================================
    # CONFIGURAÇÃO
    # ==========================================================

    BASE_SCORE = 60

    STRONG_GAP = 20

    # Quantidade máxima de candles fechados analisados.
    LOOKBACK = 30

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        if not market.ready:
            return context

        result = context.fair_value_gap

        evidence = context.evidence

        result.clear()

        # ======================================================
        # CANDLES FECHADOS
        #
        # O último candle pode estar em formação.
        # Ele não cria um novo FVG.
        # Pode apenas testar/preencher um FVG já existente.
        # ======================================================

        all_candles = market.candles.all()

        if len(all_candles) < 3:
            return context

        closed_candles = all_candles[:-1]

        if len(closed_candles) < 3:
            return context

        if len(closed_candles) > self.LOOKBACK:

            closed_candles = closed_candles[-self.LOOKBACK:]

        # ======================================================
        # PROCURAR FVG ATIVO
        #
        # Procuramos do candle mais recente para trás.
        #
        # Isso garante que, se existirem vários FVGs ativos,
        # utilizaremos o mais recente.
        # ======================================================

        active_fvg = None

        total = len(closed_candles)

        for i in range(total - 3, -1, -1):

            c1 = closed_candles[i]

            c3 = closed_candles[i + 2]

            # ==================================================
            # BULLISH FVG
            # ==================================================

            if c1.high < c3.low:

                fvg = {

                    "bullish": True,

                    "bearish": False,

                    "high": c3.low,

                    "low": c1.high,

                    "formation_index": i + 2,

                }

            # ==================================================
            # BEARISH FVG
            # ==================================================

            elif c1.low > c3.high:

                fvg = {

                    "bullish": False,

                    "bearish": True,

                    "high": c1.low,

                    "low": c3.high,

                    "formation_index": i + 2,

                }

            else:

                continue

            # ==================================================
            # TAMANHO
            # ==================================================

            gap_size = abs(

                fvg["high"] -

                fvg["low"]

            )

            # ==================================================
            # VERIFICAR O QUE ACONTECEU DEPOIS DA FORMAÇÃO
            #
            # O candle que criou o FVG não conta como teste.
            # Começamos pelo candle seguinte.
            # ==================================================

            tested = False

            filled = False

            touches = 0

            formation_index = fvg["formation_index"]

            for j in range(

                formation_index + 1,

                total,

            ):

                candle = closed_candles[j]

                # ==============================================
                # BULLISH
                # ==============================================

                if fvg["bullish"]:

                    if candle.low <= fvg["high"]:

                        tested = True

                        touches += 1

                    if candle.close <= fvg["low"]:

                        filled = True

                        break

                # ==============================================
                # BEARISH
                # ==============================================

                elif fvg["bearish"]:

                    if candle.high >= fvg["low"]:

                        tested = True

                        touches += 1

                    if candle.close >= fvg["high"]:

                        filled = True

                        break

            # ==================================================
            # FVG PREENCHIDO
            #
            # Não é mais considerado ativo.
            # Continuamos procurando um FVG anterior.
            # ==================================================

            if filled:

                continue

            # ==================================================
            # ENCONTRAMOS O FVG ATIVO MAIS RECENTE
            # ==================================================

            active_fvg = fvg

            active_fvg["gap_size"] = gap_size

            active_fvg["tested"] = tested

            active_fvg["touches"] = touches

            break

        # ======================================================
        # NENHUM FVG ATIVO
        # ======================================================

        if active_fvg is None:

            return context

        # ======================================================
        # PREENCHER RESULTADO
        # ======================================================

        result.valid = True

        result.bullish = active_fvg["bullish"]

        result.bearish = active_fvg["bearish"]

        result.high = active_fvg["high"]

        result.low = active_fvg["low"]

        result.midpoint = (

            result.high +

            result.low

        ) / 2

        result.tested = active_fvg["tested"]

        result.filled = False

        result.touches = active_fvg["touches"]

        # ======================================================
        # SCORE
        # ======================================================

        result.score = self.BASE_SCORE

        gap_size = active_fvg["gap_size"]

        if gap_size > 20:

            result.strength = 1.0

            result.score += self.STRONG_GAP

        elif gap_size > 10:

            result.strength = 0.75

            result.score += 10

        else:

            result.strength = 0.50

        # ======================================================
        # EVIDÊNCIA
        # ======================================================

        if result.bullish:

            evidence.add("BULLISH_FVG")

        elif result.bearish:

            evidence.add("BEARISH_FVG")

        # ======================================================
        # CANDLE ATUAL
        #
        # O candle atual NÃO cria FVG.
        # Ele somente pode testar/preencher o FVG ativo.
        # ======================================================

        last = market.last_candle

        if last is not None:

            if result.bullish:

                if last.low <= result.high:

                    result.tested = True

                    result.touches += 1

                if last.close <= result.low:

                    result.filled = True

            elif result.bearish:

                if last.high >= result.low:

                    result.tested = True

                    result.touches += 1

                if last.close >= result.high:

                    result.filled = True

        # ======================================================
        # SE O CANDLE ATUAL PREENCHEU
        # ======================================================

        if result.filled:

            result.valid = False

        # ======================================================
        # FINALIZAÇÃO
        # ======================================================

        result.score = min(

            result.score,

            100,

        )

        result.confidence = (

            result.score / 100

        )

        return context