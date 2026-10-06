"""Manual Massive CL crude-oil product and contract evidence probe RC1.

Uses provider-documented crude-oil product code CL. Evidence only: it does not
approve OIL mapping or select an expiry.
"""
from __future__ import annotations
import json, os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE="https://api.massive.com"
PRODUCT_FIELDS=("product_code","name","asset_class","asset_sub_class","sector","sub_sector","trading_venue","type","settlement_method","settlement_type","trade_currency_code","settlement_currency_code","price_quotation","unit_of_measure","unit_of_measure_qty","last_updated")
CONTRACT_FIELDS=("ticker","name","product_code","active","first_trade_date","last_trade_date","days_to_maturity","settlement_date","trading_venue","type","trade_tick_size")

def _get(path,key,params,opener):
    q=dict(params); q["apiKey"]=key
    req=Request(f"{BASE}{path}?{urlencode(q)}",headers={"User-Agent":"COPILOTO_PRICE_ACTION_AI/ExternalContext"})
    try:
        p=json.loads(opener(req,timeout=15.0).read().decode("utf-8"))
        return p,""
    except HTTPError as e: return None,f"HTTP_{e.code}"
    except (URLError,TimeoutError,OSError,UnicodeDecodeError,json.JSONDecodeError) as e: return None,type(e).__name__

def _rows(p):
    r=p.get("results",[]) if isinstance(p,dict) else []
    return r if isinstance(r,list) else []

def _safe(rows,fields):
    return [{k:r.get(k) for k in fields if k in r} for r in rows if isinstance(r,dict)]

def run(api_key,opener=urlopen):
    key=str(api_key or "").strip()
    if not key: raise ValueError("MASSIVE_API_KEY is required")
    pp,pe=_get("/futures/v1/products",key,{"product_code":"CL","limit":100},opener)
    cp,ce=_get("/futures/v1/contracts",key,{"product_code":"CL","active":"true","limit":100,"sort":"last_trade_date.asc"},opener)
    products=_safe(_rows(pp),PRODUCT_FIELDS)
    contracts=_safe(_rows(cp),CONTRACT_FIELDS)
    return {
      "name":"MassiveRealCLCrudeOilProbe","version":"RC1","provider":"Massive",
      "observational_only":True,"provider_documented_product_code":"CL",
      "candidate_is_approved_mapping":False,"creates_provider_symbol_map":False,
      "creates_manifest":False,"creates_router_route":False,
      "selects_futures_expiry":False,
      "product":{"status":"OK" if isinstance(pp,dict) else "ERROR","error":pe,"rows":products},
      "active_contracts":{"status":"OK" if isinstance(cp,dict) else "ERROR","error":ce,"rows":contracts},
    }

def main():
    key=os.getenv("MASSIVE_API_KEY","")
    if not key.strip():
        print("ERROR: MASSIVE_API_KEY is not configured."); raise SystemExit(2)
    print(json.dumps(run(key),indent=2,ensure_ascii=False))

if __name__=="__main__": main()
