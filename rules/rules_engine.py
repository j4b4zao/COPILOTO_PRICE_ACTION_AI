"""
Motor de validação das regras.
"""


class RulesEngine:

    @staticmethod
    def validate(checklist, rules):

        for rule in rules:

            if not checklist.has(rule):
                return False

        return True