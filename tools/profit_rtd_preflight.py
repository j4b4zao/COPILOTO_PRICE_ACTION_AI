"""CLI para executar o preflight Profit RTD no ambiente real (RC20)."""

from __future__ import annotations

import argparse
import sys

from config.settings import ENABLE_ORDER_FLOW_SCORE, PROFIT_RTD_TIMES_TRADES_PATH
from market_data.excel_range_gateway import ExcelRangeGateway
from market_data.profit_rtd_live_preflight import ProfitRTDLivePreflight
from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa o preflight observacional do Times & Trades RTD do Profit."
    )
    parser.add_argument(
        "symbol",
        help="Ativo esperado no workbook RTD, por exemplo WINV26 ou WDOU26.",
    )
    return parser


def _default_excel_factory():
    # xlwings só é necessário no Windows/ambiente real. O import tardio
    # mantém o CLI importável nos gates offline Linux do GitHub Actions.
    from connectors.excel_connector import ExcelConnector

    return ExcelConnector


def run_preflight(symbol: str, *, excel_factory=None) -> int:
    factory = excel_factory or _default_excel_factory()
    excel = factory()
    if not excel.conectar(PROFIT_RTD_TIMES_TRADES_PATH):
        print("PROFIT_RTD_PREFLIGHT=ERROR")
        print("reason=TIMES_TRADES_EXCEL_CONNECT_FAILED")
        return 1

    gateway = ExcelRangeGateway(excel)
    reader = ProfitRTDTimesTradesReader(gateway)
    result = ProfitRTDLivePreflight(reader).run(
        symbol,
        order_flow_score_enabled=ENABLE_ORDER_FLOW_SCORE,
    )

    print(f"PROFIT_RTD_PREFLIGHT={result.status}")
    print(f"symbol={result.symbol}")
    print(f"source={result.source}")
    print(f"trade_count={result.trade_count}")
    print(f"observational_only={result.observational_only}")
    print(f"score_influence_allowed={result.score_influence_allowed}")
    print(f"decision_influence_allowed={result.decision_influence_allowed}")
    print(f"order_execution_allowed={result.order_execution_allowed}")
    if result.reasons:
        print("reasons=" + "|".join(result.reasons))
    else:
        print("reasons=OK")

    return 0 if result.ready else 2


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return run_preflight(args.symbol)


if __name__ == "__main__":
    sys.exit(main())
