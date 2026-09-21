from types import SimpleNamespace

from tools.historical_microstructure_confluence_report import (
    HistoricalMicrostructureConfluenceReporter,
)


def _result(
    pa="BUY",
    flow="BUY",
    book="BID_DOMINANT",
    state="CONFIRMED",
    independent=2,
    correlated=0,
    conflicts=0,
    eligibility="NOT_ELIGIBLE",
    reason="WEAK_OR_LOW_CONFIDENCE",
):
    return SimpleNamespace(
        price_action_bias=pa,
        order_flow_pressure=flow,
        book_pressure=book,

        confluence={
            "state": state,
            "independent_evidence_count": independent,
            "correlated_evidence_count": correlated,
            "conflict_count": conflicts,
        },

        eligibility={
            "state": eligibility,
            "reason": reason,
        },
    )


def test_three_way_alignment():

    report = HistoricalMicrostructureConfluenceReporter().build([
        _result()
    ])

    assert report.samples == 1

    assert report.pa_flow_aligned == 1
    assert report.pa_book_aligned == 1
    assert report.pa_flow_book_aligned == 1

    assert report.pa_flow_conflict == 0
    assert report.pa_book_conflict == 0

    assert report.flow_book_aligned == 1
    assert report.flow_book_conflict == 0


def test_pa_flow_conflict():

    report = HistoricalMicrostructureConfluenceReporter().build([
        _result(
            pa="BUY",
            flow="SELL",
            book="BALANCED",
            state="CONFLICT",
            conflicts=1,
            reason="CONFLICT_PRESENT",
        )
    ])

    assert report.pa_flow_aligned == 0
    assert report.pa_flow_conflict == 1

    assert report.pa_book_aligned == 0
    assert report.pa_book_conflict == 0


def test_pa_book_conflict():

    report = HistoricalMicrostructureConfluenceReporter().build([
        _result(
            pa="BUY",
            flow="BALANCED",
            book="ASK_DOMINANT",
            state="CONFLICT",
            conflicts=1,
            reason="CONFLICT_PRESENT",
        )
    ])

    assert report.pa_book_aligned == 0
    assert report.pa_book_conflict == 1


def test_flow_book_conflict():

    report = HistoricalMicrostructureConfluenceReporter().build([
        _result(
            pa="BUY",
            flow="BUY",
            book="ASK_DOMINANT",
            state="CONFLICT",
            independent=1,
            conflicts=1,
            reason="CONFLICT_PRESENT",
        )
    ])

    assert report.flow_book_aligned == 0
    assert report.flow_book_conflict == 1


def test_balanced_sources_do_not_create_alignment():

    report = HistoricalMicrostructureConfluenceReporter().build([
        _result(
            pa="BUY",
            flow="BALANCED",
            book="BALANCED",
            state="INSUFFICIENT_DATA",
            independent=1,
            reason="INSUFFICIENT_DATA",
        )
    ])

    assert report.pa_flow_aligned == 0
    assert report.pa_book_aligned == 0
    assert report.pa_flow_book_aligned == 0
    assert report.flow_book_aligned == 0


def test_counters_are_preserved():

    report = HistoricalMicrostructureConfluenceReporter().build([
        _result(
            independent=2,
            correlated=1,
            conflicts=0,
        ),
        _result(
            pa="SELL",
            flow="SELL",
            book="ASK_DOMINANT",
            independent=2,
            correlated=0,
            conflicts=0,
        ),
    ])

    assert report.samples == 2

    assert report.independent_evidence == {2: 2}
    assert report.correlated_evidence == {
        0: 1,
        1: 1,
    }

    assert report.conflict_counts == {0: 2}


def test_safety_is_passive():

    report = HistoricalMicrostructureConfluenceReporter().build([
        _result()
    ])

    assert report.observational_only is True
    assert report.score_influence_allowed is False
    assert report.risk_influence_allowed is False
    assert report.decision_influence_allowed is False
    assert report.alert_influence_allowed is False
    assert report.order_execution_allowed is False
