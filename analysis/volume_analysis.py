"""
analysis/volume_analysis.py

Engine de Volume

Analisa o volume negociado do candle
em relação ao histórico recente.

RC3
"""

from statistics import median

from ai.engine_base import EngineBase
from enums.volume_level import VolumeLevel


class VolumeAnalysis(EngineBase):

    NAME = "VolumeAnalysis"

    VERSION = "RC3"

    ENABLED = True

    PRIORITY = 40

    # ==========================================================
    # CONFIGURAÇÃO
    # ==========================================================

    HISTORY_SIZE = 20

    LOW_RATIO = 0.70

    HIGH_RATIO = 1.30

    EXTREME_RATIO = 2.00

    MIN_HISTORY = 5

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        if not market.ready:

            return context

        result = context.volume

        evidence = context.evidence

        result.clear()

        # ======================================================
        # HISTÓRICO DE CANDLES
        # ======================================================

        candles = market.candles.all()

        if not candles:

            return context

        # ======================================================
        # CANDLE ATUAL
        # ======================================================

        current_candle = candles[-1]

        current_volume = float(
            getattr(
                current_candle,
                "volume",
                0.0
            ) or 0.0
        )

        # ======================================================
        # CANDLES FECHADOS
        # ======================================================

        closed_candles = candles[:-1]

        historical_volumes = []

        for candle in closed_candles:

            candle_volume = float(
                getattr(
                    candle,
                    "volume",
                    0.0
                ) or 0.0
            )

            # Volume zero não entra na referência.
            if candle_volume <= 0:

                continue

            historical_volumes.append(
                candle_volume
            )

        # ======================================================
        # HISTÓRICO INSUFICIENTE
        # ======================================================

        if len(historical_volumes) < self.MIN_HISTORY:

            result.current = current_volume

            result.average = (
                median(historical_volumes)
                if historical_volumes
                else 0.0
            )

            result.valid = False

            result.confidence = 0.0

            evidence.add(
                "INSUFFICIENT_VOLUME_HISTORY"
            )

            result.confluences = len(
                evidence.evidences
            )

            return context

        # ======================================================
        # LIMITAR À JANELA MAIS RECENTE
        # ======================================================

        reference_volumes = historical_volumes[
            -self.HISTORY_SIZE:
        ]

        reference_volume = median(
            reference_volumes
        )

        # ======================================================
        # PROTEÇÃO
        # ======================================================

        if reference_volume <= 0:

            result.current = current_volume

            result.average = 0.0

            result.valid = False

            result.confidence = 0.0

            evidence.add(
                "INVALID_VOLUME_REFERENCE"
            )

            result.confluences = len(
                evidence.evidences
            )

            return context

        # ======================================================
        # VOLUME ATUAL
        # ======================================================

        result.current = current_volume

        result.average = reference_volume

        # ======================================================
        # VOLUME INVÁLIDO / ZERO
        # ======================================================

        if current_volume <= 0:

            result.low = True

            result.level = VolumeLevel.LOW

            result.strength = 0.30

            result.confidence = 0.30

            result.valid = True

            evidence.add(
                "LOW_VOLUME"
            )

            result.confluences = len(
                evidence.evidences
            )

            return context

        # ======================================================
        # RELAÇÃO VOLUME / REFERÊNCIA
        # ======================================================

        ratio = (
            current_volume
            / reference_volume
        )

        # ======================================================
        # VOLUME BAIXO
        # ======================================================

        if ratio < self.LOW_RATIO:

            result.low = True

            result.level = VolumeLevel.LOW

            result.strength = 0.30

            result.confidence = 0.85

            evidence.add(
                "LOW_VOLUME"
            )

        # ======================================================
        # VOLUME NORMAL / MÉDIO
        # ======================================================

        elif ratio < self.HIGH_RATIO:

            result.medium = True

            result.level = VolumeLevel.MEDIUM

            result.strength = 0.50

            result.confidence = 0.75

            evidence.add(
                "NORMAL_VOLUME"
            )

        # ======================================================
        # VOLUME ALTO
        # ======================================================

        elif ratio < self.EXTREME_RATIO:

            result.high = True

            result.level = VolumeLevel.HIGH

            result.strength = 0.80

            result.confidence = 0.85

            evidence.add(
                "HIGH_VOLUME"
            )

        # ======================================================
        # VOLUME EXTREMO
        # ======================================================

        else:

            result.high = True

            result.level = VolumeLevel.HIGH

            result.strength = 1.00

            result.confidence = 0.95

            evidence.add(
                "EXTREME_VOLUME"
            )

        # ======================================================
        # FINALIZAÇÃO
        # ======================================================

        result.valid = True

        result.confluences = len(
            evidence.evidences
        )

        return context