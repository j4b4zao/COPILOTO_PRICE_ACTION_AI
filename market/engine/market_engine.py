from datetime import datetime

from core.candle import Candle, CandleHistory


class MarketEngine:

    def __init__(self):

        self.history = CandleHistory()

        self.current_candle = None

        self.current_period = None


    def atualizar(
        self,
        open_price,
        high,
        low,
        close,
        volume
    ):

        agora = datetime.now()

        periodo = (
            agora.year,
            agora.month,
            agora.day,
            agora.hour,
            agora.minute // 5
        )


        if self.current_period != periodo:

            if self.current_candle is not None:

                self.history.add(
                    self.current_candle
                )

            self.current_period = periodo

            self.current_candle = Candle(
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                date=agora.strftime("%d/%m/%Y"),
                time=agora.strftime("%H:%M")
            )

        else:

            self.current_candle.high = max(
                self.current_candle.high,
                high
            )

            self.current_candle.low = min(
                self.current_candle.low,
                low
            )

            self.current_candle.close = close

            self.current_candle.volume = volume


    def ultimo_candle(self):

        return self.current_candle


    def historico(self):

        return self.history