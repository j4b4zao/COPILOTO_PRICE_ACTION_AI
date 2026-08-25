from types import SimpleNamespace
from market_data.collector import Collector
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator


class Excel:
    def conectar(self, path): return True


class Reader:
    def __init__(self, rows): self.rows = iter(rows)
    def obter_dados(self): return next(self.rows)


def row(buy=100, sell=90, close=100000, volume=1000):
    return {"ativo":"WINV26","data":"23/08/2026","hora":"10:00:00","close":close,
            "volume":volume,"agressao_compra":buy,"agressao_venda":sell}


def collector(rows):
    return Collector(excel=Excel(), reader=Reader(rows), chart_mode="NORMAL")


def test_initial_quality_is_no_data():
    c = collector([row()])
    assert c.last_delta_quality.status == "NO_DATA"


def test_first_snapshot_keeps_quality_without_delta_sample():
    c = collector([row()]); c.get_data()
    assert c.last_delta_quality.status in {"NO_DATA", "INITIALIZING"}


def test_incremental_aggression_creates_quality_sample():
    c = collector([row(), row(120, 95, 100010, 1010)])
    c.get_data(); c.get_data()
    assert c.last_delta_quality.sample_count >= 1


def test_duplicate_updates_runtime_quality_without_new_sample():
    r = row(); c = collector([r, dict(r)])
    c.get_data(); before = c.last_delta_quality.sample_count
    assert c.get_data() is None
    assert c.last_delta_quality.sample_count == before


def test_missing_aggression_degrades_source_quality_contract():
    r = row(); r["agressao_compra"] = None; r["agressao_venda"] = None
    c = collector([r]); c.get_data()
    assert c.source_diagnostics.snapshot.status == "AGGRESSION_UNAVAILABLE"


def test_validator_instance_is_exposed():
    c = collector([row()])
    assert isinstance(c.delta_quality_validator, ProfitDeltaQualityValidator)


def test_last_quality_is_passive_only():
    c = collector([row()]); c.get_data()
    assert c.last_delta_quality.passive_only is True


def test_source_and_quality_are_kept_separate():
    c = collector([row(), row(120, 95, 100010, 1010)])
    c.get_data(); c.get_data()
    assert hasattr(c.source_diagnostics.snapshot, "aggression_availability_rate")
    assert hasattr(c.last_delta_quality, "dominance")


def test_symbol_change_resets_order_flow_then_quality_reinitializes():
    second = row(50, 40, 100100, 500); second["ativo"] = "WDOU26"
    c = collector([row(), second]); c.get_data(); c.get_data()
    assert c.source_diagnostics.snapshot.symbol_changes == 1
    assert c.last_delta_quality.status in {"NO_DATA", "INITIALIZING"}


def test_quality_does_not_modify_context_score():
    c = collector([row(), row(120, 95, 100010, 1010)])
    c.get_data(); context = c.get_data()
    assert context.score.total == 0.0
