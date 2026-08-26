from market_data.order_flow_shadow_stability import OrderFlowShadowStabilityAnalyzer


def _session(samples):
    return {
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
        "samples": samples,
    }


def _sample(official, shadow):
    return {
        "official_alignment": official,
        "shadow_alignment": shadow,
        "changed": official != shadow,
    }


def test_rc33_counts_transitions_and_runs():
    samples = []
    samples += [_sample("NEUTRAL", "BULLISH_ALIGNED")] * 40
    samples += [_sample("NEUTRAL", "DIVERGENT")] * 20
    samples += [_sample("NEUTRAL", "NEUTRAL")] * 30
    samples += [_sample("DIVERGENT", "DIVERGENT")] * 30
    report = OrderFlowShadowStabilityAnalyzer().evaluate([_session(samples)])
    assert report.samples == 120
    assert report.changed_count == 60
    assert report.transitions["NEUTRAL->BULLISH_ALIGNED"] == 40
    assert report.shadow_runs["BULLISH_ALIGNED"]["max_run"] == 40
    assert report.directional_balance_status == "ONE_SIDED_SAMPLE"
    assert report.score_influence_allowed is False
    assert report.decision_influence_allowed is False
    assert report.order_execution_allowed is False


def test_rc33_rejects_non_observational_session():
    bad = _session([_sample("NEUTRAL", "NEUTRAL")] * 120)
    bad["score_influence_allowed"] = True
    try:
        OrderFlowShadowStabilityAnalyzer().evaluate([bad])
    except ValueError:
        return
    raise AssertionError("RC33 deveria rejeitar sessao com score habilitado")


def test_rc33_requires_minimum_samples():
    try:
        OrderFlowShadowStabilityAnalyzer().evaluate([_session([_sample("NEUTRAL", "NEUTRAL")] * 20)])
    except ValueError:
        return
    raise AssertionError("RC33 deveria rejeitar amostra insuficiente")


if __name__ == "__main__":
    test_rc33_counts_transitions_and_runs()
    test_rc33_rejects_non_observational_session()
    test_rc33_requires_minimum_samples()
    print("PROFIT_RTD_RC33=OK")
