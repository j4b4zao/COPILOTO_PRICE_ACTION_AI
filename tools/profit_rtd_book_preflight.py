"""Preflight real do Livro de Ofertas RTD do Profit (RC26)."""

from __future__ import annotations

import sys

from config.settings import PROFIT_RTD_ORDER_BOOK_PATH
from connectors.excel_connector import ExcelConnector
from market_data.excel_range_gateway import ExcelRangeGateway
from market_data.profit_rtd_book_preflight import ProfitRTDBookPreflight
from market_data.profit_rtd_workbook_reader import ProfitRTDBookDepthReader


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    symbol = str(argv[0] if argv else "").strip().upper()
    if not symbol:
        print("PROFIT_RTD_BOOK_PREFLIGHT=NOT_READY")
        print("reasons=SYMBOL_REQUIRED")
        return 2

    excel = ExcelConnector()
    if not excel.conectar(PROFIT_RTD_ORDER_BOOK_PATH):
        print("PROFIT_RTD_BOOK_PREFLIGHT=NOT_READY")
        print(f"symbol={symbol}")
        print("source=PROFIT_RTD")
        print("bid_levels=0")
        print("ask_levels=0")
        print("observational_only=True")
        print("score_influence_allowed=False")
        print("decision_influence_allowed=False")
        print("order_execution_allowed=False")
        print("reasons=EXCEL_CONNECTION_ERROR")
        return 1

    try:
        gateway = ExcelRangeGateway(excel)
        reader = ProfitRTDBookDepthReader(gateway)
        payload = reader.read_book_depth(symbol)
        result = ProfitRTDBookPreflight.evaluate(payload)
    except Exception as exc:
        result = {
            "status": "NOT_READY",
            "symbol": symbol,
            "source": "PROFIT_RTD",
            "bid_levels": 0,
            "ask_levels": 0,
            "best_bid": None,
            "best_ask": None,
            "spread": None,
            "observational_only": True,
            "score_influence_allowed": False,
            "decision_influence_allowed": False,
            "order_execution_allowed": False,
            "reasons": [f"READ_ERROR:{type(exc).__name__}:{exc}"],
        }

    print(f"PROFIT_RTD_BOOK_PREFLIGHT={result['status']}")
    print(f"symbol={result['symbol']}")
    print(f"source={result['source']}")
    print(f"bid_levels={result['bid_levels']}")
    print(f"ask_levels={result['ask_levels']}")
    print(f"best_bid={result['best_bid']}")
    print(f"best_ask={result['best_ask']}")
    print(f"spread={result['spread']}")
    print(f"observational_only={result['observational_only']}")
    print(f"score_influence_allowed={result['score_influence_allowed']}")
    print(f"decision_influence_allowed={result['decision_influence_allowed']}")
    print(f"order_execution_allowed={result['order_execution_allowed']}")
    print(f"reasons={'|'.join(result['reasons']) if result['reasons'] else 'OK'}")
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
