from dataclasses import dataclass

from market_data.profit_rtd_validation_session_runner import (
    ProfitRTDValidationSessionRunner,
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
    path: str = "/tmp/session.json"
    sha256: str = "a" * 64
    total_cycles: int = 3


class FakeCloseUtility:
    def __init__(self):
        self.calls = []

    def close(self, collector, output_dir, *, session_id=None, overwrite=False):
        self.calls.append((collector, output_dir, session_id, overwrite))
        return FakeCloseReceipt(total_cycles=collector.calls)


class FakeCollector:
    def __init__(self, *, enabled=True, outputs=None, error_at=None):
        self.enable_profit_rtd_order_flow = enabled
        self.outputs = list(outputs or [])
        self.error_at = error_at
        self.calls = 0

    def get_data(self):
        if self.error_at is not None and self.calls == self.error_at:
            raise RuntimeError("boom")
        self.calls += 1
        if self.outputs:
            return self.outputs.pop(0)
        return None


def build_runner(preflight=None, close=None, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return ProfitRTDValidationSessionRunner(
        preflight or FakePreflight(),
        close or FakeCloseUtility(),
        sleeper=lambda value: sleeps.append(value),
    )


def test_ready_runs_bounded_cycles_and_exports():
    preflight = FakePreflight()
    close = FakeCloseUtility()
    sleeps = []
    collector = FakeCollector(outputs=[object(), None, object()])
    result = build_runner(preflight, close, sleeps).run(
        collector,
        "winv26",
        "/tmp",
        cycles=3,
        interval_seconds=0.5,
        session_id="sessao_1",
    )
    assert result.status == "COMPLETED"
    assert result.symbol == "WINV26"
    assert result.completed_cycles == 3
    assert result.emitted_contexts == 2
    assert result.exported_cycles == 3
    assert result.sha256 == "a" * 64
    assert sleeps == [0.5, 0.5]
    assert preflight.calls == [("WINV26", False)]
    assert len(close.calls) == 1


def test_not_ready_never_collects_or_exports():
    preflight = FakePreflight(FakePreflightResult("NOT_READY", ("NO_TRADES",)))
    close = FakeCloseUtility()
    collector = FakeCollector()
    result = build_runner(preflight, close).run(
        collector, "WINV26", "/tmp", cycles=10
    )
    assert result.status == "NOT_STARTED"
    assert result.reasons == ("NO_TRADES",)
    assert collector.calls == 0
    assert close.calls == []


def test_score_enabled_blocks_before_preflight():
    preflight = FakePreflight()
    close = FakeCloseUtility()
    collector = FakeCollector()
    result = build_runner(preflight, close).run(
        collector,
        "WINV26",
        "/tmp",
        cycles=5,
        order_flow_score_enabled=True,
    )
    assert result.status == "NOT_STARTED"
    assert result.reasons == ("ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED",)
    assert preflight.calls == []
    assert collector.calls == 0
    assert close.calls == []


def test_rtd_must_be_explicitly_enabled_only_for_session():
    preflight = FakePreflight()
    collector = FakeCollector(enabled=False)
    result = build_runner(preflight).run(
        collector, "WINV26", "/tmp", cycles=2
    )
    assert result.status == "NOT_STARTED"
    assert result.reasons == ("RTD_SOURCE_NOT_ENABLED_FOR_SESSION",)
    assert preflight.calls == []
    assert collector.calls == 0


def test_collection_error_exports_partial_session():
    close = FakeCloseUtility()
    collector = FakeCollector(error_at=1, outputs=[object()])
    result = build_runner(close=close).run(
        collector, "WINV26", "/tmp", cycles=4
    )
    assert result.status == "ERROR"
    assert result.completed_cycles == 1
    assert result.emitted_contexts == 1
    assert result.reasons[0].startswith("COLLECTION_ERROR:RuntimeError:")
    assert len(close.calls) == 1


def test_contract_remains_observational():
    result = build_runner().run(FakeCollector(), "WINV26", "/tmp", cycles=1)
    assert result.observational_only is True
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False


def main():
    tests = [
        test_ready_runs_bounded_cycles_and_exports,
        test_not_ready_never_collects_or_exports,
        test_score_enabled_blocks_before_preflight,
        test_rtd_must_be_explicitly_enabled_only_for_session,
        test_collection_error_exports_partial_session,
        test_contract_remains_observational,
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC16 APROVADO")


if __name__ == "__main__":
    main()
