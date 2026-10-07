"""RC4 breakeven statistics contract."""

from types import SimpleNamespace

import pytest

from replay.replay_statistics import ReplayStatistics


def strategy(name="TEST_SETUP"):
    return SimpleNamespace(name=name)


def test_positive_profit_is_win():
    statistics = ReplayStatistics()

    statistics.register_operation(strategy(), 10)
    result = statistics.finish()

    assert result.operations == 1
    assert result.wins == 1
    assert result.losses == 0
    assert result.breakevens == 0
    assert result.gross_profit == 10
    assert result.gross_loss == 0
    assert result.net_profit == 10
    assert result.win_rate == 100

    setup = result.setups["TEST_SETUP"]
    assert setup["operations"] == 1
    assert setup["wins"] == 1
    assert setup["losses"] == 0
    assert setup["breakevens"] == 0


def test_negative_profit_is_loss():
    statistics = ReplayStatistics()

    statistics.register_operation(strategy(), -10)
    result = statistics.finish()

    assert result.operations == 1
    assert result.wins == 0
    assert result.losses == 1
    assert result.breakevens == 0
    assert result.gross_profit == 0
    assert result.gross_loss == 10
    assert result.net_profit == -10
    assert result.win_rate == 0

    setup = result.setups["TEST_SETUP"]
    assert setup["operations"] == 1
    assert setup["wins"] == 0
    assert setup["losses"] == 1
    assert setup["breakevens"] == 0


def test_zero_profit_is_breakeven_not_win_or_loss():
    statistics = ReplayStatistics()

    statistics.register_operation(strategy(), 0)
    result = statistics.finish()

    assert result.operations == 1
    assert result.wins == 0
    assert result.losses == 0
    assert result.breakevens == 1
    assert result.gross_profit == 0
    assert result.gross_loss == 0
    assert result.net_profit == 0
    assert result.win_rate == 0

    setup = result.setups["TEST_SETUP"]
    assert setup["operations"] == 1
    assert setup["wins"] == 0
    assert setup["losses"] == 0
    assert setup["breakevens"] == 1


def test_mixed_results_preserve_statistics_identity():
    statistics = ReplayStatistics()

    statistics.register_operation(strategy(), 10)
    statistics.register_operation(strategy(), -5)
    statistics.register_operation(strategy(), 0)

    result = statistics.finish()

    assert result.operations == 3
    assert result.wins == 1
    assert result.losses == 1
    assert result.breakevens == 1

    assert result.operations == (
        result.wins
        + result.losses
        + result.breakevens
    )

    assert result.gross_profit == 10
    assert result.gross_loss == 5
    assert result.net_profit == 5
    assert result.profit_factor == 2
    assert result.win_rate == pytest.approx(100 / 3)

    setup = result.setups["TEST_SETUP"]

    assert setup["operations"] == 3
    assert setup["wins"] == 1
    assert setup["losses"] == 1
    assert setup["breakevens"] == 1

    assert setup["operations"] == (
        setup["wins"]
        + setup["losses"]
        + setup["breakevens"]
    )


def test_statistics_instances_are_isolated():
    first = ReplayStatistics()
    first.register_operation(strategy("FIRST"), 0)
    first_result = first.finish()

    second = ReplayStatistics()
    second_result = second.finish()

    assert first_result.operations == 1
    assert first_result.breakevens == 1

    assert second_result.operations == 0
    assert second_result.wins == 0
    assert second_result.losses == 0
    assert second_result.breakevens == 0
    assert second_result.setups == {}