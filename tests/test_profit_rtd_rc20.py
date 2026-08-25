from pathlib import PureWindowsPath
import inspect

from config import settings
from tools import profit_rtd_preflight
from tools import profit_rtd_validation_session


class FakeExcel:
    def __init__(self):
        self.connected_path = None

    def conectar(self, path):
        self.connected_path = path
        return False


class FakeExcelFactory:
    last = None

    def __new__(cls):
        cls.last = FakeExcel()
        return cls.last


def test_settings_separate_workbooks():
    assert PureWindowsPath(settings.EXCEL_PATH).name == "Profit.xlsx"
    assert PureWindowsPath(settings.PROFIT_RTD_TIMES_TRADES_PATH).name == "times&trades.xlsx"
    assert PureWindowsPath(settings.PROFIT_RTD_ORDER_BOOK_PATH).name == "livroOfertas.xlsx"
    assert settings.EXCEL_PATH != settings.PROFIT_RTD_TIMES_TRADES_PATH
    assert settings.PROFIT_RTD_TIMES_TRADES_PATH != settings.PROFIT_RTD_ORDER_BOOK_PATH


def test_preflight_connects_dedicated_times_trades_path():
    code = profit_rtd_preflight.run_preflight("WINV26", excel_factory=FakeExcelFactory)
    assert code == 1
    assert FakeExcelFactory.last.connected_path == settings.PROFIT_RTD_TIMES_TRADES_PATH
    assert FakeExcelFactory.last.connected_path != settings.EXCEL_PATH


def test_validation_session_builder_declares_dedicated_tt_connection():
    source = inspect.getsource(profit_rtd_validation_session._build_real_collector)
    assert "Collector(enable_profit_rtd_order_flow=False)" in source
    assert "PROFIT_RTD_TIMES_TRADES_PATH" in source
    assert "profit_rtd_times_trades_excel" in source
    assert "collector.enable_profit_rtd_order_flow = True" in source


def test_global_score_and_rtd_flags_remain_disabled():
    assert settings.ENABLE_PROFIT_RTD_ORDER_FLOW is False
    assert settings.ENABLE_ORDER_FLOW_SCORE is False


def main():
    tests = [
        test_settings_separate_workbooks,
        test_preflight_connects_dedicated_times_trades_path,
        test_validation_session_builder_declares_dedicated_tt_connection,
        test_global_score_and_rtd_flags_remain_disabled,
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC20 APROVADO")


if __name__ == "__main__":
    main()
