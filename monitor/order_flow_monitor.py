"""Diagnóstico textual informativo de Order Flow RC4.4."""


class OrderFlowMonitor:

    NAME = "OrderFlowMonitor"
    VERSION = "RC4.4-INFORMATIVE"

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
            f"Amostragem.....: {result.sampling_mode}",
            f"Unidades fonte.: {result.source_units}",
            f"Pressão........: {result.pressure}",
            f"Agressão compra: {result.buy_aggression:.0f}",
            f"Agressão venda.: {result.sell_aggression:.0f}",
            f"Delta atual....: {result.delta:+.0f}",
            f"Delta recente..: {result.recent_delta:+.0f}",
            f"Delta acumulado: {result.cumulative_delta:+.0f}",
            f"Média Delta....: {result.average_delta:+.2f}",
            f"Amostras.......: {result.sample_count}",
            f"Tendência......: {result.trend}",
            f"Padrões prontos: {result.patterns_ready}",
            f"Variação preço.: {result.recent_price_change:+.2f}",
            f"Atividade......: {result.aggression_activity_ratio:.2f}",
            f"Divergência....: {result.divergence}",
            f"Absorção.......: {result.absorption}",
            f"Exaustão.......: {result.exhaustion}",
            f"Dominância Delta: {result.delta_dominance:.2f}",
            f"Eficiência preço: {result.price_efficiency:.2f}",
            f"Maturidade hist.: {result.history_maturity:.2f}",
            f"Conf. padrão....: {result.pattern_confidence:.2f}",
            f"Qualidade.......: {result.pattern_quality}",
            f"Confirmado......: {result.pattern_confirmed}",
            "Motivo..........: " + cls._reason(result),
            "Impacto.........: somente informativo",
        ]

        return "\n".join(lines)

    @staticmethod
    def _reason(result) -> str:
        if not result.reasons:
            return "Análise ainda não executada."
        return " | ".join(result.reasons)
