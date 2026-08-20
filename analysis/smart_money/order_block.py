"""
analysis/smart_money/order_block.py

Order Block Engine

RC11
Order Blocks ativos baseados em histórico de candles fechados.
"""

from ai.engine_base import EngineBase


class OrderBlock(EngineBase):

    NAME = "OrderBlock"

    VERSION = "RC11"

    ENABLED = True

    PRIORITY = 50

    # ==========================================================
    # CONFIGURAÇÃO
    # ==========================================================

    BASE_SCORE = 60

    STRONG_SCORE = 20

    LOOKBACK = 30

    # Quantidade máxima de candles posteriores utilizados
    # para confirmar o candle-base.
    CONFIRMATION_LOOKAHEAD = 5

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        if not market.ready:
            return context

        result = context.order_block

        evidence = context.evidence

        result.clear()

        # ======================================================
        # CANDLES
        # ======================================================

        all_candles = market.candles.all()

        if len(all_candles) < 4:
            return context

        # O candle atual pode estar em formação.
        # Ele não cria/confirmará um novo OB.
        closed_candles = all_candles[:-1]

        if len(closed_candles) < 3:
            return context

        if len(closed_candles) > self.LOOKBACK:

            closed_candles = closed_candles[-self.LOOKBACK:]

        total = len(closed_candles)

        # ======================================================
        # PROCURAR O OB ATIVO MAIS RECENTE
        #
        # Procuramos do candle-base mais recente para trás.
        # ======================================================

        active_ob = None

        for i in range(total - 2, -1, -1):

            base = closed_candles[i]

            # ==================================================
            # DEFINIR DIREÇÃO DO CANDLE-BASE
            # ==================================================

            base_bullish = base.close > base.open

            base_bearish = base.close < base.open

            if not (base_bullish or base_bearish):
                continue

            # ==================================================
            # PROCURAR CONFIRMAÇÃO POSTERIOR
            # ==================================================

            confirmation_end = min(

                total,

                i + 1 + self.CONFIRMATION_LOOKAHEAD,

            )

            confirmation_index = None

            bullish_ob = False

            bearish_ob = False

            # --------------------------------------------------
            # BULLISH ORDER BLOCK
            #
            # Último candle-base é bearish.
            # Um candle posterior fecha acima da máxima da base.
            # --------------------------------------------------

            if base_bearish:

                for j in range(

                    i + 1,

                    confirmation_end,

                ):

                    candle = closed_candles[j]

                    if candle.close > base.high:

                        bullish_ob = True

                        confirmation_index = j

                        break

            # --------------------------------------------------
            # BEARISH ORDER BLOCK
            #
            # Último candle-base é bullish.
            # Um candle posterior fecha abaixo da mínima da base.
            # --------------------------------------------------

            elif base_bullish:

                for j in range(

                    i + 1,

                    confirmation_end,

                ):

                    candle = closed_candles[j]

                    if candle.close < base.low:

                        bearish_ob = True

                        confirmation_index = j

                        break

            # ==================================================
            # SEM CONFIRMAÇÃO
            # ==================================================

            if not (bullish_ob or bearish_ob):

                continue

            # ==================================================
            # CONSTRUIR CANDIDATO
            # ==================================================

            ob = {

                "bullish": bullish_ob,

                "bearish": bearish_ob,

                "high": base.high,

                "low": base.low,

                "formation_index": i,

                "confirmation_index": confirmation_index,

            }

            # ==================================================
            # AVALIAR O QUE ACONTECEU DEPOIS DA CONFIRMAÇÃO
            # ==================================================

            tested = False

            touches = 0

            mitigated = False

            start = confirmation_index + 1

            for j in range(start, total):

                candle = closed_candles[j]

                # ==============================================
                # BULLISH OB
                # ==============================================

                if bullish_ob:

                    # O preço entrou na zona.
                    if candle.low <= ob["high"]:

                        tested = True

                        touches += 1

                    # Fechamento abaixo da base invalida
                    # o Order Block.
                    if candle.close < ob["low"]:

                        mitigated = True

                        break

                # ==============================================
                # BEARISH OB
                # ==============================================

                elif bearish_ob:

                    # O preço entrou na zona.
                    if candle.high >= ob["low"]:

                        tested = True

                        touches += 1

                    # Fechamento acima da base invalida
                    # o Order Block.
                    if candle.close > ob["high"]:

                        mitigated = True

                        break

            # ==================================================
            # OB MITIGADO
            #
            # Não é mais operacional.
            # Procuramos um OB anterior ainda ativo.
            # ==================================================

            if mitigated:

                continue

            # ==================================================
            # OB ATIVO ENCONTRADO
            # ==================================================

            active_ob = ob

            active_ob["tested"] = tested

            active_ob["touches"] = touches

            break

        # ======================================================
        # NENHUM OB ATIVO
        # ======================================================

        if active_ob is None:

            return context

        # ======================================================
        # RESULTADO
        # ======================================================

        result.valid = True

        result.bullish = active_ob["bullish"]

        result.bearish = active_ob["bearish"]

        result.high = active_ob["high"]

        result.low = active_ob["low"]

        result.entry_price = (

            result.high +

            result.low

        ) / 2

        result.tested = active_ob["tested"]

        result.touches = active_ob["touches"]

        result.mitigated = False

        # ======================================================
        # FORÇA DO OB
        # ======================================================

        base_range = abs(

            result.high -

            result.low

        )

        if base_range <= 0:

            result.valid = False

            return context

        # ======================================================
        # SCORE BASE
        # ======================================================

        result.score = self.BASE_SCORE

        # ======================================================
        # CONFIRMAÇÃO ESTRUTURAL
        # ======================================================

        structure = context.structure

        if result.bullish and structure.bos_up:

            result.score += self.STRONG_SCORE

        elif result.bearish and structure.bos_down:

            result.score += self.STRONG_SCORE

        # ======================================================
        # STRENGTH
        # ======================================================

        if result.score >= 80:

            result.strength = 1.0

        elif result.score >= 70:

            result.strength = 0.75

        else:

            result.strength = 0.50

        # ======================================================
        # EVIDÊNCIA
        # ======================================================

        if result.bullish:

            evidence.add("BULLISH_ORDER_BLOCK")

        elif result.bearish:

            evidence.add("BEARISH_ORDER_BLOCK")

        # ======================================================
        # CANDLE ATUAL
        #
        # O candle atual não cria um novo OB.
        # Ele apenas pode testar ou mitigar o OB existente.
        # ======================================================

        last = market.last_candle

        if last is not None:

            if result.bullish:

                if last.low <= result.high:

                    result.tested = True

                    result.touches += 1

                if last.close < result.low:

                    result.mitigated = True

            elif result.bearish:

                if last.high >= result.low:

                    result.tested = True

                    result.touches += 1

                if last.close > result.high:

                    result.mitigated = True

        # ======================================================
        # SE O CANDLE ATUAL MITIGOU
        # ======================================================

        if result.mitigated:

            result.valid = False

        # ======================================================
        # SCORE FINAL
        # ======================================================

        result.score = min(

            result.score,

            100,

        )

        result.confidence = (

            result.score / 100

        )

        return context