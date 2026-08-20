from time import sleep
from core.candle_builder import CandleBuilder
from core.market_clock import MarketClock


builder = CandleBuilder()

for i in range(10):

    agora = MarketClock.now()

    candle, novo = builder.update(
        open_price=172500,
        high=172500,
        low=172500,
        close=172500 + i,
        volume=1000,
        timeframe="M1",
        timestamp=agora,
    )

    print(
        agora.strftime("%H:%M:%S"),
        "| período:",
        candle.timestamp.strftime("%H:%M"),
        "| novo:",
        novo,
        "| close:",
        candle.close,
    )

    sleep(1)