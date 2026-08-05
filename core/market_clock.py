"""
core/market_clock.py

Controle de horário do mercado.
"""

from datetime import datetime, time


class MarketClock:

    @staticmethod
    def now():

        return datetime.now()

    @staticmethod
    def is_open():

        agora = datetime.now().time()

        return time(9, 0) <= agora <= time(18, 0)

    @staticmethod
    def is_lunch():

        agora = datetime.now().time()

        return time(12, 0) <= agora <= time(13, 0)

    @staticmethod
    def is_pre_market():

        agora = datetime.now().time()

        return time(8, 45) <= agora < time(9, 0)

    @staticmethod
    def is_after_market():

        agora = datetime.now().time()

        return agora > time(18, 0)