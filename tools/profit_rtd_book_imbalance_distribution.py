"""RC40 - analisa distribuicao de magnitude do imbalance do Book a partir de JSON RC39.

Observacional apenas. Nao altera thresholds, Score, Decision ou execucao.
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path

DEFAULT_BOOK_THRESHOLD = 0.062149


def _percentile(values, q):
    if not values:
        return None
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs)-1) * float(q)
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1-w) + xs[hi] * w


def analyze(payload, threshold=DEFAULT_BOOK_THRESHOLD):
    samples = payload.get("samples") or []
    values = [float(s.get("raw_imbalance", s.get("snapshot_imbalance", 0.0)) or 0.0) for s in samples]
    pos = [v for v in values if v > 0]
    neg_mag = [abs(v) for v in values if v < 0]
    zero = [v for v in values if v == 0]
    qs = (0.50,0.75,0.90,0.95,0.99)
    report = {
        "status":"COMPLETED",
        "samples":len(values),
        "positive_samples":len(pos),
        "negative_samples":len(neg_mag),
        "zero_samples":len(zero),
        "book_threshold":float(threshold),
        "positive_cross_count":sum(v >= threshold for v in pos),
        "negative_cross_count":sum(v >= threshold for v in neg_mag),
        "positive_max":max(pos) if pos else None,
        "negative_max_abs":max(neg_mag) if neg_mag else None,
        "observational_only":True,
        "score_influence_allowed":False,
        "decision_influence_allowed":False,
        "order_execution_allowed":False,
    }
    for q in qs:
        tag=f"p{int(q*100)}"
        report[f"positive_{tag}"]=_percentile(pos,q)
        report[f"negative_abs_{tag}"]=_percentile(neg_mag,q)
    reasons=[]
    if neg_mag and report["negative_cross_count"] == 0:
        reasons.append("NEGATIVE_BOOK_PRESENT_BUT_BELOW_CURRENT_THRESHOLD")
    if not neg_mag:
        reasons.append("NO_NEGATIVE_BOOK_SAMPLES")
    report["reasons"] = reasons or ["OK"]
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description="Analisa distribuicao do imbalance do Book a partir de JSON RC39.")
    p.add_argument("json_path")
    p.add_argument("--threshold",type=float,default=DEFAULT_BOOK_THRESHOLD)
    a=p.parse_args(argv)
    payload=json.loads(Path(a.json_path).expanduser().resolve().read_text(encoding="utf-8"))
    r=analyze(payload,a.threshold)
    print(f"PROFIT_RTD_BOOK_IMBALANCE_DISTRIBUTION={r['status']}")
    for k,v in r.items():
        if k=="status": continue
        if k=="reasons": v=",".join(v)
        print(f"{k}={v}")
    return 0

if __name__=="__main__": sys.exit(main())
