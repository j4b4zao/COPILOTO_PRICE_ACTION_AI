"""Manual no-key WTI aggregator probe RC1.

Evidence-only probe of AmericasOilWatch /api/v1/wti. The provider documents the
endpoint as WTI sourced from Yahoo Finance CL=F with EIA/FRED fallback. Because it
is an aggregator, successful output is not automatic approval for OIL mapping.
"""
from __future__ import annotations
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL="https://americasoilwatch.com/api/v1/wti"

def run(opener=urlopen):
    req=Request(URL,headers={"User-Agent":"COPILOTO_PRICE_ACTION_AI/ExternalContext"},method="GET")
    try:
        payload=json.loads(opener(req,timeout=15.0).read().decode("utf-8"))
        error=""
    except HTTPError as exc:
        payload,error=None,f"HTTP_{exc.code}"
    except (URLError,TimeoutError,OSError,UnicodeDecodeError,json.JSONDecodeError) as exc:
        payload,error=None,type(exc).__name__
    return {
        "name":"AmericasOilWatchWTIProbe","version":"RC1",
        "observational_only":True,"internal_asset":"OIL",
        "candidate_is_approved_mapping":False,
        "aggregator_source":True,
        "documented_upstream":"Yahoo Finance CL=F with EIA/FRED fallback",
        "creates_provider_symbol_map":False,"creates_manifest":False,"creates_router_route":False,
        "request_status":"OK" if isinstance(payload,dict) else "ERROR",
        "error":error,
        "payload":payload if isinstance(payload,dict) else {},
    }

def main():
    print(json.dumps(run(),indent=2,ensure_ascii=False,default=str))

if __name__=="__main__": main()
