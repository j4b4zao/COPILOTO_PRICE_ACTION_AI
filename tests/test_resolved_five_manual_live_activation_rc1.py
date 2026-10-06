from datetime import datetime
import json

import pytest

import tools.resolved_five_manual_live_activation_rc1 as target


class Response:
    def __init__(self, payload):
        self.payload = payload
    def read(self):
        return json.dumps(self.payload).encode()


def test_disabled_fails_before_provider_construction(monkeypatch):
    monkeypatch.setattr(target, "build_resolved_five_observational_router",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not build")))
    with pytest.raises(PermissionError):
        target.run(enabled=False, reference_timestamp="2026-10-06T15:30:00+00:00",
                   maximum_staleness_seconds=3600, fmp_api_key="f", twelvedata_api_key="t")


def test_naive_reference_timestamp_fails_closed():
    with pytest.raises(ValueError, match="timezone-aware"):
        target.run(enabled=True, reference_timestamp="2026-10-06T15:30:00",
                   maximum_staleness_seconds=3600, fmp_api_key="f", twelvedata_api_key="t")


def test_missing_credentials_fail_before_network():
    with pytest.raises(ValueError, match="API keys"):
        target.run(enabled=True, reference_timestamp="2026-10-06T15:30:00+00:00",
                   maximum_staleness_seconds=3600, fmp_api_key="", twelvedata_api_key="")


def test_manual_run_reports_five_assets_and_fail_closed_readiness(monkeypatch):
    from external_context.providers.resolved_five_observational_configuration import (
        build_resolved_five_observational_router as real_builder,
    )
    def fmp(req, timeout):
        from urllib.parse import parse_qs, urlparse
        symbol = parse_qs(urlparse(req.full_url).query)["symbol"][0]
        return Response([{"symbol":symbol,"price":100,"changePercentage":1.0,"timestamp":1791300000}])
    def td(req, timeout):
        return Response({"close":"4155","percent_change":"0.3","timestamp":1791300000})
    def oil(req, timeout):
        return Response({"quoteType":"intraday","quoteStatus":"current",
            "provider":"Yahoo Finance (CL=F)","dataSource":"Yahoo Finance (CL=F)",
            "priceUsd":87.26,"changePct":-2.43,"observedAt":"2026-10-06T15:20:00Z"})
    monkeypatch.setattr(target, "build_resolved_five_observational_router",
        lambda **kwargs: real_builder(fmp_api_key="f", twelvedata_api_key="t",
            fmp_opener=fmp,twelvedata_opener=td,oil_opener=oil))
    result=target.run(enabled=True,reference_timestamp="2026-10-06T15:30:00+00:00",
        maximum_staleness_seconds=3600,fmp_api_key="f",twelvedata_api_key="t")
    assert result["observational_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["collector_state_valid"] is False
    assert result["readiness"]["status"]=="DATA_NOT_READY"
    assert result["readiness"]["missing_assets"]==["DXY"]
    assert result["assets"]["US10Y"]["status"]=="MISSING"
    for asset in ("US500","NASDAQ","VIX","OIL","GOLD"):
        assert result["assets"][asset]["status"]=="AVAILABLE"
