"""Diagnóstico textual informativo de Order Flow RC4.1."""


class OrderFlowMonitor:

    NAME = "OrderFlowMonitor"
    VERSION = "RC4.1-INFORMATIVE"

    @classmethod
    def render(cls, context) -> str:
        result = context.order_flow

        status = getattr(
            result.status,
            "value",
            str(result.status),
        )

        lines = [
            "[ ORDER FLOW - INFORMATIVO ]",
            f"Status.........: {status}",
            f"Pressão........: {result.pressure}",
            f"Agressão compra: {result.buy_aggression:.0f}",
            f"Agressão venda.: {result.sell_aggression:.0f}",
            f"Delta atual....: {result.delta:+.0f}",
            f"Delta recente..: {result.recent_delta:+.0f}",
            f"Delta acumulado: {result.cumulative_delta:+.0f}",
            f"Média Delta....: {result.average_delta:+.2f}",
            f"Amostras.......: {result.sample_count}",
            f"Tendência......: {result.trend}",
            "Motivo..........: " + cls._reason(result),
            "Impacto.........: somente informativo",
        ]

        return "\n".join(lines)

    @staticmethod
    def _reason(result) -> str:
        if not result.reasons:
            return "Análise ainda não executada."
        return " | ".join(result.reasons)
