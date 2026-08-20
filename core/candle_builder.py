"""
core/candle_builder.py

Responsável pela construção dos candles.

O CandleBuilder recebe o último preço (ULT) do mercado
e constrói os candles M1/M5/M15 a partir dos preços
observados em tempo real.

O volume recebido pelo Collector representa o volume
acumulado fornecido pelo Profit. O CandleBuilder transforma
esse acumulado em volume negociado no período.

RC4
"""

from __future__ import annotations

from datetime import datetime

from models.candle import Candle


class CandleBuilder:

    def __init__(self):

        self.current = None

        self.current_period = None

        # =====================================================
        # CONTROLE DO VOLUME ACUMULADO
        # =====================================================

        # Último volume acumulado recebido do Profit.
        self.last_cumulative_volume = None

        # Volume acumulado no início do candle atual.
        self.period_start_volume = None

    # =====================================================
    # NORMALIZAÇÃO DO PERÍODO
    # =====================================================

    def _normalize_period(
        self,
        timestamp: datetime,
        timeframe: str,
    ):

        timeframe = timeframe.upper()

        if timeframe == "M1":

            return timestamp.replace(
                second=0,
                microsecond=0,
            )

        if timeframe == "M5":

            minute = (timestamp.minute // 5) * 5

            return timestamp.replace(
                minute=minute,
                second=0,
                microsecond=0,
            )

        if timeframe == "M15":

            minute = (timestamp.minute // 15) * 15

            return timestamp.replace(
                minute=minute,
                second=0,
                microsecond=0,
            )

        return timestamp.replace(
            second=0,
            microsecond=0,
        )

    # =====================================================
    # VOLUME DO PERÍODO
    # =====================================================

    def _calculate_period_volume(
        self,
        cumulative_volume: float,
        new_period: bool,
    ) -> float:

        cumulative_volume = float(
            cumulative_volume
        )

        # =================================================
        # PRIMEIRA LEITURA
        # =================================================

        if self.last_cumulative_volume is None:

            self.last_cumulative_volume = (
                cumulative_volume
            )

            self.period_start_volume = (
                cumulative_volume
            )

            return 0.0

        # =================================================
        # RESET DO ACUMULADOR
        # =================================================

        if cumulative_volume < self.last_cumulative_volume:

            # O acumulador provavelmente foi reiniciado
            # ou houve mudança de sessão/contrato.
            #
            # Não permitimos volume negativo.

            self.last_cumulative_volume = (
                cumulative_volume
            )

            self.period_start_volume = (
                cumulative_volume
            )

            return 0.0

        # =================================================
        # NOVO PERÍODO
        # =================================================

        if new_period:

            self.period_start_volume = (
                self.last_cumulative_volume
            )

        # =================================================
        # VOLUME NEGOCIADO NO PERÍODO
        # =================================================

        if self.period_start_volume is None:

            self.period_start_volume = (
                self.last_cumulative_volume
            )

        period_volume = (
            cumulative_volume
            - self.period_start_volume
        )

        # Atualiza a última leitura somente depois
        # do cálculo do delta.

        self.last_cumulative_volume = (
            cumulative_volume
        )

        return max(
            0.0,
            period_volume,
        )

    # =====================================================
    # UPDATE
    # =====================================================

    def update(
        self,
        open_price,
        high,
        low,
        close,
        volume,
        timeframe="M1",
        timestamp=None,
    ):

        timestamp = timestamp or datetime.now()

        period = self._normalize_period(
            timestamp,
            timeframe,
        )

        # =================================================
        # PREÇO REAL DO MERCADO
        # =================================================

        price = float(close)

        cumulative_volume = float(
            volume
        )

        # =================================================
        # PRIMEIRO CANDLE
        # =================================================

        if self.current is None:

            self.current_period = period

            period_volume = (
                self._calculate_period_volume(
                    cumulative_volume,
                    new_period=True,
                )
            )

            self.current = Candle(

                open=price,

                high=price,

                low=price,

                close=price,

                volume=period_volume,

                timestamp=period,

            )

            return self.current, True

        # =================================================
        # MESMO CANDLE
        # =================================================

        if period == self.current_period:

            period_volume = (
                self._calculate_period_volume(
                    cumulative_volume,
                    new_period=False,
                )
            )

            self.current.high = max(
                self.current.high,
                price,
            )

            self.current.low = min(
                self.current.low,
                price,
            )

            self.current.close = price

            self.current.volume = period_volume

            return self.current, False

        # =================================================
        # NOVO CANDLE
        # =================================================

        period_volume = (
            self._calculate_period_volume(
                cumulative_volume,
                new_period=True,
            )
        )

        self.current = Candle(

            open=price,

            high=price,

            low=price,

            close=price,

            volume=period_volume,

            timestamp=period,

        )

        self.current_period = period

        return self.current, True