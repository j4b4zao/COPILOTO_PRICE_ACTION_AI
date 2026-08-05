"""
analysis/volume_analysis.py

Engine de Volume

RC2
"""

from ai.engine_base import EngineBase
from enums.volume_level import VolumeLevel


class VolumeAnalysis(EngineBase):

    NAME = "VolumeAnalysis"

    VERSION = "RC2"

    ENABLED = True

    PRIORITY = 40

    HIGH_VOLUME = 10000
    MEDIUM_VOLUME = 5000

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

        volume = market.volume

        # ======================================================
        # VOLUME ALTO
        # ======================================================

        if volume >= self.HIGH_VOLUME:

            result.high = True

            result.level = VolumeLevel.HIGH

            result.strength = 1.00

            result.confidence = 0.90

            evidence.add("HIGH_VOLUME")

        # ======================================================
        # VOLUME MÉDIO
        # ======================================================

        elif volume >= self.MEDIUM_VOLUME:

            result.medium = True

            result.level = VolumeLevel.MEDIUM

            result.strength = 0.60

            result.confidence = 0.60

            evidence.add("MEDIUM_VOLUME")

        # ======================================================
        # VOLUME BAIXO
        # ======================================================

        else:

            result.low = True

            result.level = VolumeLevel.LOW

            result.strength = 0.30

            result.confidence = 0.30

            evidence.add("LOW_VOLUME")

        # ======================================================
        # ESTATÍSTICAS
        # ======================================================

        result.current = volume

        result.confluences = len(evidence.evidences)

        result.valid = True

        return context