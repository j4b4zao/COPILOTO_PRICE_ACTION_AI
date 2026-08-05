"""
monitor/monitor.py

Painel de monitoramento do Copiloto Price Action AI.
"""

from datetime import datetime


class Monitor:

    def __init__(self):

        self.status = "INICIALIZANDO"

    # =====================================================
    # ATUALIZAR
    # =====================================================

    def atualizar(self, market):

        self.status = "OPERANDO"

        estrutura = market.estrutura or {}
        setup = market.setup or {}
        decisao = market.decisao or {}
        sinal = market.sinal or {}

        print("\n" * 2)

        print("=" * 70)
        print("              COPILOTO PRICE ACTION AI")
        print("=" * 70)

        print(f"Status..............: {self.status}")
        print(f"Hora................: {datetime.now().strftime('%H:%M:%S')}")

        print()

        print("MERCADO")

        print(f"Ativo...............: {market.ativo}")
        print(f"TimeFrame...........: {market.timeframe}")
        print(f"Preço...............: {market.close}")
        print(f"Volume..............: {market.volume}")
        print(f"ADX.................: {market.adx}")
        print(f"MACD................: {market.macd}")

        print()

        print("ESTRUTURA")

        print(f"Tendência...........: {estrutura.get('tendencia', 'N/D')}")
        print(f"Evento..............: {estrutura.get('evento', 'N/D')}")
        print(f"Regime..............: {estrutura.get('regime', 'N/D')}")

        print()

        print("SETUP")

        print(f"Setup...............: {setup.get('setup', 'N/D')}")
        print(f"Lado................: {setup.get('lado', 'N/D')}")
        print(f"Confiança...........: {setup.get('confianca', 0)}")

        print()

        print("DECISÃO")

        print(f"Score...............: {market.score:.2f}")
        print(f"Ação................: {decisao.get('acao', 'N/D')}")
        print(f"Confiança...........: {decisao.get('confianca', 0)}")

        print()

        print("SINAL")

        print(f"Status..............: {sinal.get('status', 'N/D')}")
        print(f"Entrada.............: {sinal.get('entrada', 'N/D')}")
        print(f"Lado................: {sinal.get('lado', 'N/D')}")

        print()

        print("EXPLICAÇÃO")

        if market.explicacao:
            print(market.explicacao)
        else:
            print("Aguardando análise...")

        print("=" * 70)