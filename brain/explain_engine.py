"""
brain/explain_engine.py

Gera uma explicação detalhada da análise realizada
pelo Copiloto Price Action AI.
"""

from core.base_module import BaseModule


class ExplainEngine(BaseModule):

    def __init__(self):

        super().__init__()

    # ==================================================
    # EXECUTAR
    # ==================================================

    def executar(self, market):

        estrutura = market.estrutura
        setup = market.setup
        contexto = market.contexto
        score = market.score
        decisao = market.decisao

        linhas = []

        linhas.append("=" * 50)
        linhas.append("COPILOTO PRICE ACTION AI")
        linhas.append("=" * 50)

        linhas.append(f"Ativo............... {market.ativo}")

        linhas.append(f"Tendência........... {estrutura.get('tendencia','-')}")

        linhas.append(f"Setup............... {setup.get('nome','NENHUM')}")

        linhas.append(f"Lado................ {setup.get('lado','NEUTRO')}")

        linhas.append(f"Score............... {score.get('total',0)}")

        linhas.append(f"Classe.............. {score.get('classe','-')}")

        linhas.append(f"Confiança........... {score.get('confianca','-')}")

        linhas.append(f"Contexto............ {contexto.get('qualidade','-')}")

        linhas.append(f"Decisão............. {decisao.get('acao','-')}")

        linhas.append(f"Risco............... {decisao.get('risco','-')}")

        linhas.append("")

        linhas.append("Motivos:")

        motivos = score.get("motivos", [])

        if motivos:

            for motivo in motivos:

                linhas.append(f"  • {motivo}")

        else:

            linhas.append("  • Nenhum motivo registrado.")

        linhas.append("=" * 50)

        market.explicacao = "\n".join(linhas)

        return market