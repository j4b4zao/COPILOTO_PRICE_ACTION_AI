from dataclasses import dataclass

from tools.profit_rtd_validation_session import (
    MAX_VALIDATION_CYCLES,
    build_parser,
    run_validation_session,
)


@dataclass
class FakePreflightResult:
    status: str = "READY"
    reasons: tuple[str, ...] = ()

    @property
    def ready(self):
        return self.status == "READY"


class FakePreflight:
    def __init__(self, result=None):
        self.result = result or FakePreflightResult()
        self.calls = []

    def run(self, symbol, *, order_flow_score_enabled=False):
        self.calls.append((symbol, order_flow_score_enabled))
        return self.result


@dataclass
class FakeCloseReceipt:
    path: str = "/tmp/profit_rtd_validation_WINV26_test.json"
    sha256: str = "b" * 64
    total_cycles: int = 0


class FakeCloseUtility:
    def __init__(self):
        self.calls = []

    def close(self, collector, output_dir, *, session_id=None, overwrite=False):
        self.calls.append((collector, output_dir, session_id, overwrite))
        return FakeCloseReceipt(total_cycles=collector.calls)


class FakeCollector:
    def __init__(self, *, outputs=None, interrupt_at=None):
        self.enable_profit_rtd_order_flow = True
        self.outputs = list(outputs or [])
        self.interrupt_at = interrupt_at
        self.calls = 0

    def get_data(self):
        if self.interrupt_at is not None and self.calls == self.interrupt_at:
            raise KeyboardInterrupt()
        self.calls += 1
        if self.outputs:
            return self.outputs.pop(0)
        return None


def test_parser_requires_explicit_operational_parameters():
    parser = build_parser()
    args = parser.parse_args(
        [
            "WINV26",
            "--cycles",
            "20",
            "--output-dir",
            "/tmp",
            "--execute",
        ]
    )
    assert args.symbol == "WINV26"
    assert args.cycles == 20
    assert args.output_dir == "/tmp"
    assert args.execute is True


def test_execute_flag_blocks_before_any_dependency_is_needed(capsys):
    code = run_validation_session(
        "WINV26",
        "/tmp",
        cycles=10,
        execute=False,
        order_flow_score_enabled=False,
    )
    output = capsys.readouterr().out
    assert code == 2
    assert "EXECUTE_FLAG_REQUIRED" in output


def test_score_blocks_before_collector_or_preflight(capsys):
    code = run_validation_session(
        "WINV26",
        "/tmp",
        cycles=10,
        execute=True,
        order_flow_score_enabled=True,
    )
    output = capsys.readouterr().out
    assert code == 2
    assert "ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED" in output


def test_cycle_limit_is_hard_gate(capsys):
    code = run_validation_session(
        "WINV26",
        "/tmp",
        cycles=MAX_VALIDATION_CYCLES + 1,
        execute=True,
        order_flow_score_enabled=False,
    )
    output = capsys.readouterr().out
    assert code == 2
    assert f"CYCLES_MUST_BE_1_TO_{MAX_VALIDATION_CYCLES}" in output


def test_ready_session_completes_and_exports(capsys):
    collector = FakeCollector(outputs=[object(), None, object()])
    preflight = FakePreflight()
    closer = FakeCloseUtility()
    code = run_validation_session(
        "winv26",
        "/tmp",
        cycles=3,
        interval_seconds=0,
        session_id="teste",
        execute=True,
        collector=collector,
        preflight=preflight,
        close_utility=closer,
        order_flow_score_enabled=False,
    )
    output = capsys.readouterr().out
    assert code == 0
    assert "PROFIT_RTD_SESSION=COMPLETED" in output
    assert "symbol=WINV26" in output
    assert "completed_cycles=3" in output
    assert "emitted_contexts=2" in output
    assert "score_influence_allowed=False" in output
    assert "decision_influence_allowed=False" in output
    assert "order_execution_allowed=False" in output
    assert collector.calls == 3
    assert preflight.calls == [("WINV26", False)]
    assert len(closer.calls) == 1


def test_not_ready_never_collects_or_exports(capsys):
    collector = FakeCollector()
    preflight = FakePreflight(FakePreflightResult("NOT_READY", ("NO_TRADES",)))
    closer = FakeCloseUtility()
    code = run_validation_session(
        "WINV26",
        "/tmp",
        cycles=5,
        interval_seconds=0,
        execute=True,
        collector=collector,
        preflight=preflight,
        close_utility=closer,
        order_flow_score_enabled=False,
    )
    output = capsys.readouterr().out
    assert code == 2
    assert "PROFIT_RTD_SESSION=NOT_STARTED" in output
    assert "NO_TRADES" in output
    assert collector.calls == 0
    assert closer.calls == []


def test_operator_interrupt_exports_partial_and_returns_130(capsys):
    collector = FakeCollector(outputs=[object()], interrupt_at=1)
    preflight = FakePreflight()
    closer = FakeCloseUtility()
    code = run_validation_session(
        "WINV26",
        "/tmp",
        cycles=10,
        interval_seconds=0,
        execute=True,
        collector=collector,
        preflight=preflight,
        close_utility=closer,
        order_flow_score_enabled=False,
    )
    output = capsys.readouterr().out
    assert code == 130
    assert "PROFIT_RTD_SESSION=INTERRUPTED" in output
    assert "OPERATOR_INTERRUPTED" in output
    assert collector.calls == 1
    assert len(closer.calls) == 1


def test_bootstrap_error_is_sanitized(capsys):
    class BadPreflight:
        pass

    code = run_validation_session(
        "WINV26",
        "/tmp",
        cycles=1,
        execute=True,
        collector=FakeCollector(),
        preflight=BadPreflight(),
        close_utility=FakeCloseUtility(),
        order_flow_score_enabled=False,
    )
    output = capsys.readouterr().out
    assert code == 1
    assert "PROFIT_RTD_SESSION=ERROR" in output
    assert "BOOTSTRAP_ERROR:TypeError" in output


def main():
    print("Execute este gate com pytest: python -m pytest -q tests/test_profit_rtd_rc17.py")


if __name__ == "__main__":
    main()
