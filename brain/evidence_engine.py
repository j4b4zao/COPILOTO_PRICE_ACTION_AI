"""
brain/evidence_engine.py

Evidence Engine RC1

Centraliza todas as evidências produzidas
pelas engines de análise.

Não toma decisões.

Não gera sinais.

Apenas organiza as evidências que serão
utilizadas pelo StrategyEngine,
ScoreEngine e AI Brain.
"""

from ai.engine_base import EngineBase


class EvidenceEngine(EngineBase):

    NAME = "EvidenceEngine"

    VERSION = "RC1"

    ENABLED = True

    PRIORITY = 65

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        result = context.evidence

        result.clear()

        self._structure(context)

        self._liquidity(context)

        self._volume(context)

        self._price_action(context)

        self._context(context)

        result.score = len(result.evidences) * 10

        result.confidence = min(result.score, 100) / 100

        result.valid = len(result.evidences) > 0

        return context

    # ==========================================================
    # MARKET STRUCTURE
    # ==========================================================

    def _structure(self, context):

        result = context.evidence

        structure = context.structure

        if structure.bos_up:
            result.add("BOS_UP")

        if structure.bos_down:
            result.add("BOS_DOWN")

        if structure.choch:
            result.add("CHOCH")

        if structure.hh:
            result.add("HH")

        if structure.hl:
            result.add("HL")

        if structure.lh:
            result.add("LH")

        if structure.ll:
            result.add("LL")

    # ==========================================================
    # LIQUIDITY
    # ==========================================================

    def _liquidity(self, context):

        result = context.evidence

        liquidity = context.liquidity

        if liquidity.sweep_low:
            result.add("SWEEP_LOW")

        if liquidity.sweep_high:
            result.add("SWEEP_HIGH")

        if liquidity.equal_high:
            result.add("EQUAL_HIGH")

        if liquidity.equal_low:
            result.add("EQUAL_LOW")

    # ==========================================================
    # VOLUME
    # ==========================================================

    def _volume(self, context):

        result = context.evidence

        volume = context.volume

        if volume.high:
            result.add("HIGH_VOLUME")

        elif volume.medium:
            result.add("MEDIUM_VOLUME")

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    def _price_action(self, context):

        result = context.evidence

        pa = context.price_action

        if pa.pullback:
            result.add("PULLBACK")

        if pa.hammer:
            result.add("HAMMER")

        if pa.shooting_star:
            result.add("SHOOTING_STAR")

        if pa.bullish_engulfing:
            result.add("BULLISH_ENGULFING")

        if pa.bearish_engulfing:
            result.add("BEARISH_ENGULFING")

    # ==========================================================
    # CONTEXT
    # ==========================================================

    def _context(self, context):

        result = context.evidence

        ctx = context.context

        if ctx.favorable:
            result.add("FAVORABLE_CONTEXT")