from dataclasses import dataclass

from tools.profit_rtd_validate import run_validation


@dataclass
class FakeEvaluation:
    status: str
    approved: bool
    symbol: str = "WINV26"
    total_cycles: int = 30
    continuity_rate: float = 0.9667
    update_rate: float = 0.80
    total_new_trades: int = 120
    baseline_resets: int = 1
    continuity_loss_cycles: int = 0
    symbol_reset_cycles: int = 0
    reasons: tuple[str, ...] = ()
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class FakeEvaluator:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.paths = []

    def evaluate_file(self, path):
        self.paths.append(path)
        if self.error is not None:
            raise self.error
        return self.result


def test_approved_returns_zero():
    evaluator = FakeEvaluator(FakeEvaluation("APPROVED", True))
    assert run_validation("session.json", evaluator=evaluator) == 0
    assert evaluator.paths == ["session.json"]


def test_rejected_returns_two():
    evaluator = FakeEvaluator(
        FakeEvaluation("REJECTED", False, reasons=("LOW_CONTINUITY_RATE",))
    )
    assert run_validation("session.json", evaluator=evaluator) == 2


def test_invalid_file_returns_one():
    evaluator = FakeEvaluator(error=ValueError("schema invalido"))
    assert run_validation("bad.json", evaluator=evaluator) == 1


def test_contract_remains_observational():
    result = FakeEvaluation("APPROVED", True)
    assert result.observational_only is True
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False


def main():
    tests = [
        test_approved_returns_zero,
        test_rejected_returns_two,
        test_invalid_file_returns_one,
        test_contract_remains_observational,
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC19 APROVADO")


if __name__ == "__main__":
    main()
