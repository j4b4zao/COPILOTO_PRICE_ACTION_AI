"""RC38 - auditoria observacional de polaridade do Livro RTD.

Lê snapshots reais do Book e registra quantidades Bid/Ask e imbalance bruto,
sem alterar thresholds, Score, Decision ou execução.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from config.settings import ENABLE_ORDER_FLOW_SCORE, PROFIT_RTD_ORDER_BOOK_PATH
from connectors.excel_connector import ExcelConnector
from market_data.book_depth_level2_provider import NormalizedLevel2BookDepthProvider
from market_data.excel_range_gateway import ExcelRangeGateway
from market_data.profit_rtd_workbook_reader import ProfitRTDBookDepthReader

MAX_CYCLES = 3600


def _build_provider():
    excel = ExcelConnector()
    if not excel.conectar(PROFIT_RTD_ORDER_BOOK_PATH):
        raise RuntimeError("Nao foi possivel conectar ao Livro de Ofertas RTD.")
    reader = ProfitRTDBookDepthReader(ExcelRangeGateway(excel))
    return NormalizedLevel2BookDepthProvider(reader, source="PROFIT_RTD", max_levels=50), excel


def run(symbol, *, cycles, interval, output_dir, execute=False, sleeper=time.sleep):
    if not execute:
        print("PROFIT_RTD_BOOK_POLARITY_AUDIT=NOT_STARTED")
        print("reason=EXECUTE_FLAG_REQUIRED")
        return 2
    if ENABLE_ORDER_FLOW_SCORE:
        print("PROFIT_RTD_BOOK_POLARITY_AUDIT=NOT_STARTED")
        print("reason=ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED")
        return 2
    if not (1 <= int(cycles) <= MAX_CYCLES) or float(interval) < 0:
        print("PROFIT_RTD_BOOK_POLARITY_AUDIT=NOT_STARTED")
        print("reason=INVALID_CYCLES_OR_INTERVAL")
        return 2

    symbol = str(symbol or "").strip().upper()
    target = Path(output_dir).expanduser().resolve(); target.mkdir(parents=True, exist_ok=True)
    try:
        provider, excel = _build_provider()
    except Exception as exc:
        print("PROFIT_RTD_BOOK_POLARITY_AUDIT=ERROR")
        print(f"reason=BOOTSTRAP_ERROR:{type(exc).__name__}:{exc}")
        return 1

    samples=[]; errors=0
    pos=neg=zero=0
    min_imb=None; max_imb=None
    for cycle in range(1, int(cycles)+1):
        try:
            snap=provider.snapshot(symbol)
            if not snap.available:
                raise ValueError("BOOK_UNAVAILABLE")
            bid=float(snap.bid_quantity); ask=float(snap.ask_quantity); imb=float(snap.imbalance)
            pos += imb > 0; neg += imb < 0; zero += imb == 0
            min_imb = imb if min_imb is None else min(min_imb, imb)
            max_imb = imb if max_imb is None else max(max_imb, imb)
            samples.append({"cycle":cycle,"timestamp":datetime.now().isoformat(timespec="milliseconds"),"bid_quantity":bid,"ask_quantity":ask,"imbalance":imb,"best_bid":snap.best_bid,"best_ask":snap.best_ask,"spread":snap.spread,"levels_bid":len(snap.bids),"levels_ask":len(snap.asks)})
            print(f"[BOOK POLARITY] cycle={cycle}/{cycles} bid_qty={bid:.2f} ask_qty={ask:.2f} imbalance={imb:.6f}")
        except Exception as exc:
            errors += 1
            print(f"[BOOK POLARITY] cycle={cycle}/{cycles} error={type(exc).__name__}:{exc}")
        if cycle < int(cycles) and float(interval)>0: sleeper(float(interval))

    completed=len(samples)
    status="COMPLETED" if completed==int(cycles) and errors==0 else "COMPLETED_WITH_WARNINGS"
    reasons=[]
    if neg==0 and completed: reasons.append("NO_NEGATIVE_IMBALANCE_OBSERVED")
    if errors: reasons.append("COLLECTION_ERRORS_OR_SKIPPED_CYCLES")
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    path=target/f"profit_rtd_book_polarity_{symbol}_{stamp}.json"
    payload={"status":status,"symbol":symbol,"requested_cycles":int(cycles),"completed_cycles":completed,"positive_imbalance_count":pos,"negative_imbalance_count":neg,"zero_imbalance_count":zero,"min_imbalance":min_imb,"max_imbalance":max_imb,"collection_errors":errors,"observational_only":True,"score_influence_allowed":False,"decision_influence_allowed":False,"order_execution_allowed":False,"reasons":reasons,"samples":samples}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PROFIT_RTD_BOOK_POLARITY_AUDIT={status}")
    print(f"symbol={symbol}")
    print(f"completed_cycles={completed}")
    print(f"positive_imbalance_count={pos}")
    print(f"negative_imbalance_count={neg}")
    print(f"zero_imbalance_count={zero}")
    print(f"min_imbalance={min_imb}")
    print(f"max_imbalance={max_imb}")
    print(f"collection_errors={errors}")
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    print("reasons="+("|".join(reasons) if reasons else "OK"))
    print(f"output_path={path}")
    return 0 if status=="COMPLETED" else 1


def main(argv=None):
    p=argparse.ArgumentParser(description="Audita polaridade bruta do Book RTD.")
    p.add_argument("symbol")
    p.add_argument("--cycles",required=True,type=int)
    p.add_argument("--interval",type=float,default=0.25)
    p.add_argument("--output-dir",default=r"C:\COPILOTO_PRICE_ACTION_AI\data\profit_rtd_book_polarity")
    p.add_argument("--execute",action="store_true")
    a=p.parse_args(argv)
    return run(a.symbol,cycles=a.cycles,interval=a.interval,output_dir=a.output_dir,execute=a.execute)

if __name__=="__main__": sys.exit(main())
