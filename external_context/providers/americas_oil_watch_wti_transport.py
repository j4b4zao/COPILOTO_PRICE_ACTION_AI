"""Americas Oil Watch WTI observational transport RC1.

Accepts only current intraday Yahoo Finance CL=F observations from the public
aggregator. Daily fallback data is deliberately rejected. observedAt is the
market observation timestamp; fetchedAt is never substituted for it.
"""
from __future__ import annotations
import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class AmericasOilWatchWTITransport:
    NAME="AmericasOilWatchWTITransport"
    VERSION="RC1"
    URL="https://americasoilwatch.com/api/v1/wti"

    def __init__(self, *, timeout=5.0, opener=None):
        self._timeout=float(timeout)
        if self._timeout <= 0: raise ValueError("timeout must be greater than zero")
        self._opener=opener or urlopen

    @staticmethod
    def _timestamp(value):
        text=str(value or "").strip()
        if not text: return None
        try:
            dt=datetime.fromisoformat(text.replace("Z","+00:00"))
        except ValueError:
            return None
        if dt.utcoffset() is None: return None
        return dt.isoformat()

    def fetch(self, provider_symbol="CL=F"):
        if str(provider_symbol or "").strip() != "CL=F":
            raise ValueError("provider_symbol must be CL=F")
        req=Request(self.URL,headers={"User-Agent":"COPILOTO_PRICE_ACTION_AI/ExternalContext"},method="GET")
        try:
            payload=json.loads(self._opener(req,timeout=self._timeout).read().decode("utf-8"))
        except (HTTPError,URLError,TimeoutError,OSError,UnicodeDecodeError,json.JSONDecodeError):
            return None
        if not isinstance(payload,dict): return None
        if payload.get("quoteType") != "intraday": return None
        if payload.get("quoteStatus") != "current": return None
        provider=str(payload.get("provider") or "")
        source=str(payload.get("dataSource") or "")
        if "Yahoo Finance" not in provider or "CL=F" not in provider: return None
        if "Yahoo Finance" not in source or "CL=F" not in source: return None
        try:
            price=float(payload["priceUsd"])
            change=float(payload["changePct"])
        except (KeyError,TypeError,ValueError):
            return None
        if price <= 0: return None
        timestamp=self._timestamp(payload.get("observedAt"))
        if timestamp is None: return None
        return {"price":price,"change":change,"timestamp":timestamp}

    def snapshot(self):
        return {
            "name":self.NAME,"version":self.VERSION,"url":self.URL,
            "configured":True,"observational_only":True,
            "requires_api_key":False,
            "accepted_provider_symbol":"CL=F",
            "accepted_quote_type":"intraday",
            "accepted_quote_status":"current",
            "accepted_upstream":"Yahoo Finance (CL=F)",
            "timestamp_semantics":"observedAt_timezone_aware_iso8601",
            "daily_fallback_accepted":False,
        }
