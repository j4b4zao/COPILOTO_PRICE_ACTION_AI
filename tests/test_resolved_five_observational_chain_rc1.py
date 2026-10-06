from datetime import datetime
import json

from external_context.external_market_collector import ExternalMarketCollector
from external_context.providers.resolved_five_observational_configuration import (
    build_resolved_five_observational_router,
)


class R:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()


def fmp(req, timeout):
    from urllib.parse import parse_qs, urlparse
    symbol = parse_qs(urlparse(req.full_url).query)["symbol"][0]
    return R([{"symbol": symbol, "price": 100, "changePercentage": 1.0, "timestamp": 1791300000}])


def td(req, timeout):
    return R({"close": "4155", "percent_change": "0.3", "timestamp": 1791300000})


def oil(req, timeout):
    return R({
        "quoteType": "intraday",
        "quoteStatus": "current",
        "provider": "Yahoo Finance (CL=F)",
        "dataSource": "Yahoo Finance (CL=F)",
        "priceUsd": 87.26,
        "changePct": -2.43,
        "observedAt": "2026-10-06T15:20:00Z",
    })


def router():
    return build_resolved_five_observational_router(
        fmp_api_key="f",
        twelvedata_api_key="t",
        fmp_opener=fmp,
        twelvedata_opener=td,
        oil_opener=oil,
    )


def test_five_quotes_cross_collector_but_official_state_fails_closed_without_dxy():
    collector = ExternalMarketCollector(provider=router(), preserve_quotes=True)
    state = collector.collect()

    assert state.valid is False
    assert state.us500 > 0
    assert state.nasdaq > 0
    assert state.vix > 0
    assert state.oil > 0
    assert state.gold > 0
    assert state.dxy == 0
    assert state.us10y == 0
    assert any("DXY" in reason for reason in state.reasons)

    assert collector.observational_snapshot is not None
    quotes = collector.observational_snapshot.to_quotes()
    for asset in ("US500", "NASDAQ", "VIX", "OIL", "GOLD"):
        assert quotes[asset] is not None
    assert quotes["DXY"] is None
    assert quotes["US10Y"] is None


def test_readiness_reports_required_dxy_and_audits_optional_us10y_separately():
    collector = ExternalMarketCollector(provider=router(), preserve_quotes=True)
    collector.collect()

    audit = collector.observational_snapshot.audit(
        reference_timestamp=datetime.fromisoformat("2026-10-06T15:30:00+00:00"),
        maximum_staleness_seconds=3600,
    )

    assert audit.readiness.status == "DATA_NOT_READY"
    assert set(audit.readiness.missing_assets) == {"DXY"}
    assert set(audit.readiness.available_assets) == {"US500", "NASDAQ", "VIX"}

    by_asset = {item.canonical_symbol: item for item in audit.assets}
    assert by_asset["US10Y"].status == "MISSING"
    assert by_asset["OIL"].status == "AVAILABLE"
    assert by_asset["GOLD"].status == "AVAILABLE"
