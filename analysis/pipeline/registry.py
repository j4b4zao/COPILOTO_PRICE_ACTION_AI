"""
analysis/pipeline/registry.py

Registro central das etapas do pipeline.
"""


class PipelineRegistry:

    def __init__(self):

        self.steps = []

    def adicionar(self, step):

        self.steps.append(step)

    def executar(self, market):

        for step in self.steps:

            market = step.executar(market)

        return market