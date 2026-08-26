"""CLI RC37 para auditoria Delta x Book em JSONs shadow pos-RC35."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from market_data.order_flow_delta_book_symmetry import OrderFlowDeltaBookSymmetryAnalyzer

def main(argv=None):
    p=argparse.ArgumentParser(description="Audita simetria Delta x Book sem efeito operacional.")
    p.add_argument("session_json",nargs="+")
    args=p.parse_args(argv)
    try:
        sessions=[json.loads(Path(x).expanduser().resolve().read_text(encoding="utf-8")) for x in args.session_json]
        r=OrderFlowDeltaBookSymmetryAnalyzer().evaluate(sessions)
    except Exception as exc:
        print("PROFIT_RTD_ORDER_FLOW_DELTA_BOOK_SYMMETRY=ERROR")
        print(f"reason={type(exc).__name__}:{exc}")
        return 1
    print(f"PROFIT_RTD_ORDER_FLOW_DELTA_BOOK_SYMMETRY={r.status}")
    for key,value in r.to_dict().items():
        if key=="status": continue
        if key=="reasons": value=",".join(value)
        print(f"{key}={value}")
    return 0

if __name__=="__main__": sys.exit(main())
