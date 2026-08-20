"""
Registro oficial dos detectores do COPILOTO.
"""

from analysis.detectors.pullback_detector import PullbackDetector


class DetectorRegistry:

    @staticmethod
    def build():

        return [

            PullbackDetector(),

        ]