"""Manual Bonds API US10Y intraday probe RC1."""
from __future__ import annotations
import argparse,json,os,re
from datetime import datetime
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
BASE_URL="https://api.bonds-api.com/v1/intraday"
DATE_RE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
def _aware_iso(v):
    s=str(v or "").strip()
    if not s:return None
    try:d=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError:return None
    return d.isoformat() if d.utcoffset() is not None else None
def run(api_key,reference_date,opener=urlopen):
    key=str(api_key or "").strip(); date=str(reference_date or "").strip()
    if not key:raise ValueError("BONDS_API_KEY is required")
    if not DATE_RE.fullmatch(date):raise ValueError("reference_date must be explicit YYYY-MM-DD")
    try:datetime.strptime(date,"%Y-%m-%d")
    except ValueError:raise ValueError("reference_date must be a valid YYYY-MM-DD")
    url=f"{BASE_URL}?{urlencode({'country':'US','maturity':'10Y','date':date})}"
    req=Request(url,headers={"Authorization":f"Bearer {key}","Accept":"application/json","User-Agent":"COPILOTO_PRICE_ACTION_AI/ExternalContext"},method="GET")
    try:p=json.loads(opener(req,timeout=15.0).read().decode());err=""
    except HTTPError as e:p,err=None,f"HTTP_{e.code}"
    except (URLError,TimeoutError,OSError,UnicodeDecodeError,json.JSONDecodeError) as e:p,err=None,type(e).__name__
    rows=p if isinstance(p,list) else next((p[x] for x in ("data","results","snapshots") if isinstance(p,dict) and isinstance(p.get(x),list)),[])
    obs=[]
    for r in rows:
        if not isinstance(r,dict):continue
        ts=r.get("fetched_at") or r.get("fetchedAt")
        try:y=float(r.get("yield"))
        except (TypeError,ValueError):y=None
        obs.append({"yield":y,"fetched_at":ts,"timestamp_utc_iso":_aware_iso(ts)})
    valid=[x for x in obs if x["yield"] is not None and x["yield"]>0 and x["timestamp_utc_iso"]]
    return {"name":"BondsAPIUS10YIntradayProbe","version":"RC1","provider":"Bonds API","observational_only":True,"internal_asset":"US10Y","country":"US","maturity":"10Y","reference_date":date,"candidate_is_approved_mapping":False,"creates_provider_symbol_map":False,"creates_manifest":False,"creates_router_route":False,"timestamp_semantics":"provider_fetched_at_timezone_aware_iso8601","request_status":"OK" if p is not None else "ERROR","error":err,"row_count":len(obs),"valid_observation_count":len(valid),"observations":obs}
def main():
    a=argparse.ArgumentParser();a.add_argument("--date",required=True);args=a.parse_args()
    key=os.getenv("BONDS_API_KEY","")
    if not key.strip():print("ERROR: BONDS_API_KEY is not configured.");raise SystemExit(2)
    print(json.dumps(run(key,args.date),indent=2,ensure_ascii=False))
if __name__=="__main__":main()
