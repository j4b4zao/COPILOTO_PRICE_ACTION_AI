"""
Diagnóstico textual M15/M5/M1 para os monitores do sistema.

RC3.4 - OBSERVABILIDADE / INFORMATIVO

Este componente apenas lê o AnalysisContext. Ele não altera Score,
Risk, Decision nem qualquer resultado produzido pela pipeline.
"""


class MultiTimeframeMonitor:

    NAME = "MultiTimeframeMonitor"

    VERSION = "RC3.4-INFORMATIVE"

    TIMEFRAMES = (
        ("M15", "Contexto"),
        ("M5", "Confirmação"),
        ("M1", "Gatilho"),
    )

    TREND_ATTRIBUTES = {
        "M15": "m15_trend",
        "M5": "m5_trend",
        "M1": "m1_trend",
    }

    # ==========================================================
    # FORMATAR
    # ==========================================================

    @classmethod
    def render(cls, context) -> str:

        result = context.multi_timeframe_analysis

        lines = [
            "[ MULTI-TIMEFRAME - INFORMATIVO ]",
            f"Status.........: {result.alignment}",
        ]

        state = context.multi_timeframe

        for timeframe, role in cls.TIMEFRAMES:

            trend = getattr(
                result,
                cls.TREND_ATTRIBUTES[timeframe],
            )

            trend_value = getattr(
                trend,
                "value",
                str(trend),
            )

            total_count = 0

            if state is not None:

                total_count = state.get(
                    timeframe
                ).candle_count

            closed_count = result.closed_candle_counts.get(
                timeframe,
                0,
            )

            lines.append(
                f"{timeframe} {role:<11}: "
                f"{trend_value} "
                f"| candles={total_count} "
                f"| fechados={closed_count}"
            )

        lines.extend(
            (
                f"Alinhado.......: {result.aligned}",
                f"Conflito.......: {result.conflict}",
                f"Viés...........: {result.bias}",
                f"Confiança......: {result.confidence:.2f}",
                "Motivo..........: " + cls._reason(result),
                "Impacto.........: somente informativo",
            )
        )

        return "\n".join(
            lines
        )

    # ==========================================================
    # MOTIVO
    # ==========================================================

    @staticmethod
    def _reason(result) -> str:

        if not result.reasons:

            return "Análise ainda não executada."

        return " | ".join(
            result.reasons
        )
