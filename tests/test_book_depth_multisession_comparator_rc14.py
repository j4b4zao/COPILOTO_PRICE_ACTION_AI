from types import SimpleNamespace
from market_data.book_depth_multisession_comparator import BookDepthMultiSessionComparator


def report(status="STRONG_VALID_SESSION", samples=100, valid=.85, degraded=.02, shallow=.05,
           bid=5, ask=5, duplicate=.10, availability=.95, anomalies=0):
    return SimpleNamespace(status=status, samples=samples, valid_rate=valid,
        degraded_rate=degraded, shallow_rate=shallow, average_bid_levels=bid,
        average_ask_levels=ask, average_duplicate_rate=duplicate,
        average_availability_rate=availability, total_anomalies=anomalies)


def test_insufficient_sessions():
    x=BookDepthMultiSessionComparator().compare([report(), report()]); assert x.status=="INSUFFICIENT_DATA"

def test_insufficient_samples():
    x=BookDepthMultiSessionComparator().compare([report(samples=50),report(samples=50),report(samples=50)]); assert x.status=="INSUFFICIENT_DATA"

def test_stable_strong():
    x=BookDepthMultiSessionComparator().compare([report(),report(valid=.82),report(valid=.88)]); assert x.status=="STABLE_STRONG"

def test_stable_promising():
    x=BookDepthMultiSessionComparator().compare([report(valid=.68,degraded=.10,availability=.85),report(valid=.65,degraded=.08,availability=.86),report(valid=.70,degraded=.09,availability=.84)]); assert x.status=="STABLE_PROMISING"

def test_stable_weak():
    x=BookDepthMultiSessionComparator().compare([report(valid=.50,degraded=.10),report(valid=.48,degraded=.11),report(valid=.52,degraded=.09)]); assert x.status=="STABLE_WEAK"

def test_bad_session_requires_source_review():
    x=BookDepthMultiSessionComparator().compare([report(),report(status="DEGRADED_SESSION"),report()]); assert x.status=="SOURCE_REVIEW_REQUIRED" and x.recommendation=="REVIEW_SOURCE"

def test_degraded_weighted_metrics_require_review():
    x=BookDepthMultiSessionComparator().compare([report(valid=.50,degraded=.25,availability=.75)]*3); assert x.status=="DEGRADED_MULTI_SESSION"

def test_inconsistent_valid_rate_spread():
    x=BookDepthMultiSessionComparator().compare([report(valid=.90),report(valid=.60),report(valid=.85)]); assert x.status=="INCONSISTENT"

def test_weighted_by_session_samples():
    x=BookDepthMultiSessionComparator().compare([report(samples=200,valid=.90),report(samples=100,valid=.60),report(samples=100,valid=.60)]); assert x.weighted_valid_rate==.75

def test_report_is_passive_only():
    x=BookDepthMultiSessionComparator().compare([report(),report(),report()]); assert x.passive_only is True
