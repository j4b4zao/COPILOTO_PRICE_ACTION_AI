"""
analysis/pipeline/pipeline_executor.py

Executor responsável por percorrer todas as etapas
do pipeline.
"""


class PipelineExecutor:

    def __init__(self):

        self.steps = []

    def adicionar(self, step):

        self.steps.append(step)

    def executar(self, market):

        for step in self.steps:

            market = step.executar(market)

        return market