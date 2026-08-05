"""
analysis/pipeline/pipeline_step.py

Classe base para qualquer etapa do pipeline.
"""


class PipelineStep:

    def executar(self, market):
        """
        Executa uma etapa da análise.

        Sempre retorna o objeto MarketData.
        """
        return market