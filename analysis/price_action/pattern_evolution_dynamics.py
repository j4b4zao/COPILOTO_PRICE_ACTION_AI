"""Evolução informativa de padrões inspirada em Brooks Trends, capítulo 12."""


class PatternEvolutionDynamics:

    @classmethod
    def analyze(cls, result):
        if result.brooks_breakout_failed:
            original_direction = result.brooks_breakout_direction
            direction = cls._opposite(original_direction)
            return cls._metrics(
                state="FAILED_PATTERN_REVERSAL",
                original=f"{original_direction}_BREAKOUT",
                evolved="REVERSAL",
                direction=direction,
                failure=True,
                trapped_side=cls._trapped_side(original_direction),
                confirmed=True,
            )

        if result.brooks_failed_reversal:
            direction = result.brooks_failed_reversal_direction
            return cls._metrics(
                state="FAILED_REVERSAL_CONTINUATION",
                original="REVERSAL",
                evolved="TREND_CONTINUATION",
                direction=direction,
                failure=True,
                trapped_side=cls._trapped_side(cls._opposite(direction)),
                confirmed=True,
            )

        if result.brooks_outside_range_like:
            return cls._metrics(
                state="EXPANDED_PATTERN",
                original="OUTSIDE_BAR",
                evolved="EXPANDED_RANGE",
                direction="BOTH",
                expanded=True,
                breakout_mode=True,
            )

        if (
            result.brooks_ioi_pattern
            or result.brooks_inside_sequence_count >= 2
        ):
            original = (
                "IOI"
                if result.brooks_ioi_pattern
                else "INSIDE_SEQUENCE"
            )
            return cls._metrics(
                state="PATTERN_DEVELOPING",
                original=original,
                evolved="BREAKOUT_MODE",
                direction="BOTH",
                expanded=result.brooks_inside_sequence_count >= 3,
                breakout_mode=True,
            )

        return cls._metrics()

    @staticmethod
    def _metrics(
        *,
        state="STABLE",
        original="NONE",
        evolved="NONE",
        direction="NONE",
        failure=False,
        expanded=False,
        breakout_mode=False,
        trapped_side="NONE",
        confirmed=False,
    ):
        return {
            "brooks_evolution_state": state,
            "brooks_evolution_original_pattern": original,
            "brooks_evolution_pattern": evolved,
            "brooks_evolution_direction": direction,
            "brooks_evolution_failure": failure,
            "brooks_evolution_expanded": expanded,
            "brooks_evolution_breakout_mode": breakout_mode,
            "brooks_evolution_trapped_side": trapped_side,
            "brooks_evolution_confirmed": confirmed,
        }

    @staticmethod
    def _opposite(direction):
        if direction in ("UP", "BUY"):
            return "DOWN"
        if direction in ("DOWN", "SELL"):
            return "UP"
        return "NONE"

    @staticmethod
    def _trapped_side(direction):
        if direction in ("UP", "BUY"):
            return "BULLS"
        if direction in ("DOWN", "SELL"):
            return "BEARS"
        return "NONE"
