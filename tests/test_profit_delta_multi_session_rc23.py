from market_data.profit_delta_multi_session_comparator import ProfitDeltaMultiSessionComparator
from market_data.profit_delta_session_report import ProfitDeltaSessionReport


def r(**kw):
    base=dict(status="STRONG_VALID_SESSION",recommendation="KEEP_OBSERVING",samples=100,valid_rate=.85,degraded_rate=.05,low_activity_rate=.05,average_dominance=.6,average_persistence=.7,average_zero_delta_rate=.1,average_duplicate_rate=.1,aggression_availability_rate=.95,total_anomalies=0,max_abs_delta=100.0)
    base.update(kw); return ProfitDeltaSessionReport(**base)


def test_empty(): assert ProfitDeltaMultiSessionComparator().compare([]).status=="INSUFFICIENT_DATA"
def test_min_sessions(): assert ProfitDeltaMultiSessionComparator().compare([r(samples=150),r(samples=150)]).status=="INSUFFICIENT_DATA"
def test_min_samples(): assert ProfitDeltaMultiSessionComparator().compare([r(samples=90),r(samples=90),r(samples=90)]).status=="INSUFFICIENT_DATA"
def test_strong(): assert ProfitDeltaMultiSessionComparator().compare([r(),r(valid_rate=.82),r(valid_rate=.88)]).status=="STABLE_STRONG"
def test_promising(): assert ProfitDeltaMultiSessionComparator().compare([r(status="PROMISING_VALID_SESSION",valid_rate=v) for v in (.62,.68,.70)]).status=="STABLE_PROMISING"
def test_weak(): assert ProfitDeltaMultiSessionComparator().compare([r(status="WEAK_VALID_SESSION",valid_rate=v) for v in (.45,.50,.55)]).status=="STABLE_WEAK"
def test_degraded_review():
    x=ProfitDeltaMultiSessionComparator().compare([r(),r(),r(status="DEGRADED_SESSION",valid_rate=.4,degraded_rate=.4)])
    assert x.status=="SOURCE_REVIEW_REQUIRED" and x.recommendation=="REVIEW_SOURCE"
def test_spread(): assert ProfitDeltaMultiSessionComparator().compare([r(valid_rate=.95),r(valid_rate=.80),r(valid_rate=.60)]).status=="INCONSISTENT"
def test_weighting(): assert ProfitDeltaMultiSessionComparator().compare([r(samples=200,valid_rate=.9),r(samples=50,valid_rate=.6),r(samples=50,valid_rate=.6)]).weighted_valid_rate==.8
def test_passive_extreme():
    x=ProfitDeltaMultiSessionComparator().compare([r(max_abs_delta=100),r(max_abs_delta=250),r(max_abs_delta=150)])
    assert x.passive_only and x.max_abs_delta==250
