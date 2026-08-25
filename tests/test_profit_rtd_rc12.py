"""Offline gate do Profit RTD RC12: utilitario de encerramento de sessao."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from market_data.profit_rtd_session_close_utility import ProfitRTDSessionCloseUtility


class FakeCollector:
    def __init__(self):
        self.calls = []
        self.summary = {
            "last_symbol": "WINV26",
            "total_cycles": 7,
        }

    def profit_rtd_validation_summary(self):
        return dict(self.summary)

    def export_profit_rtd_validation_session(self, target, overwrite=False):
        path = Path(target)
        self.calls.append((path, overwrite))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            path=str(path),
            sha256="a" * 64,
            byte_size=3,
            schema="PROFIT_RTD_VALIDATION_SESSION_V1",
            total_cycles=7,
        )


def test_rc12_builds_deterministic_session_path_and_exports_once():
    collector = FakeCollector()
    utility = ProfitRTDSessionCloseUtility()
    timestamp = datetime(2026, 8, 25, 16, 40, 5, tzinfo=timezone.utc)

    with TemporaryDirectory() as tmp:
        receipt = utility.close(
            collector,
            Path(tmp),
            timestamp=timestamp,
        )
        target = Path(receipt.path)
        assert target.name == "profit_rtd_validation_WINV26_20260825_164005.json"
        assert target.exists()
        assert collector.calls == [(target, False)]
        assert receipt.total_cycles == 7
        assert receipt.symbol == "WINV26"
        assert receipt.session_id == "20260825_164005"
        assert receipt.observational_only is True
        assert receipt.score_influence_allowed is False
        assert receipt.decision_influence_allowed is False
        assert receipt.order_execution_allowed is False


def test_rc12_sanitizes_session_id_and_symbol():
    collector = FakeCollector()
    collector.summary["last_symbol"] = "WIN V26/TESTE"
    utility = ProfitRTDSessionCloseUtility()

    with TemporaryDirectory() as tmp:
        receipt = utility.close(
            collector,
            Path(tmp),
            session_id="pregao 25/08 tarde",
            timestamp=datetime(2026, 8, 25, 16, 40, 5, tzinfo=timezone.utc),
        )
        assert Path(receipt.path).name == "profit_rtd_validation_WIN_V26_TESTE_pregao_25_08_tarde.json"
        assert receipt.symbol == "WIN_V26_TESTE"
        assert receipt.session_id == "pregao_25_08_tarde"


def test_rc12_rejects_relative_output_dir():
    collector = FakeCollector()
    utility = ProfitRTDSessionCloseUtility()
    try:
        utility.close(collector, "relatorios")
    except ValueError:
        pass
    else:
        raise AssertionError("output_dir relativo deveria ser rejeitado")


def test_rc12_forwards_overwrite_explicitly():
    collector = FakeCollector()
    utility = ProfitRTDSessionCloseUtility()

    with TemporaryDirectory() as tmp:
        receipt = utility.close(
            collector,
            Path(tmp),
            session_id="sessao_1",
            overwrite=True,
        )
        target = Path(receipt.path)
        assert collector.calls == [(target, True)]


def test_rc12_requires_collector_contract():
    utility = ProfitRTDSessionCloseUtility()
    with TemporaryDirectory() as tmp:
        try:
            utility.close(object(), Path(tmp))
        except TypeError:
            pass
        else:
            raise AssertionError("collector sem contrato deveria ser rejeitado")


def main():
    test_rc12_builds_deterministic_session_path_and_exports_once()
    test_rc12_sanitizes_session_id_and_symbol()
    test_rc12_rejects_relative_output_dir()
    test_rc12_forwards_overwrite_explicitly()
    test_rc12_requires_collector_contract()
    print("Profit RTD RC12: OK")


if __name__ == "__main__":
    main()
