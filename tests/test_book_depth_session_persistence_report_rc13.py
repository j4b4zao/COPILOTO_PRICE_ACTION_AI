import json
from types import SimpleNamespace
from market_data.book_depth_session_recorder import BookDepthSessionRecorder
from market_data.book_depth_session_report import BookDepthSessionReporter


def add(r, quality="VALID", source="READY", availability=1.0, duplicate=0.0, anomaly=0):
    src = SimpleNamespace(status=source, duplicate_rate=duplicate, availability_rate=availability, symbol="WINV26")
    q = SimpleNamespace(status=quality, levels_bid=5, levels_ask=5, spread=5, spread_ratio=.00003, imbalance=.2,
        top_bid_concentration=.6, top_ask_concentration=.5, concentration_edge=.1, anomaly_count=anomaly)
    r.record(src, q)


def test_jsonl_round_trip(tmp_path):
    r=BookDepthSessionRecorder(); add(r); p=r.save_jsonl(tmp_path/'s.jsonl'); x=BookDepthSessionRecorder(); assert x.load_jsonl(p)==1; assert x.samples[0].symbol=='WINV26'

def test_csv_export(tmp_path):
    r=BookDepthSessionRecorder(); add(r); p=r.export_csv(tmp_path/'s.csv'); assert 'quality_status' in p.read_text(encoding='utf-8-sig')

def test_summary_json(tmp_path):
    r=BookDepthSessionRecorder(); add(r); p=r.export_summary_json(tmp_path/'s.json'); assert json.loads(p.read_text())['samples']==1

def test_missing_jsonl_safe(tmp_path):
    assert BookDepthSessionRecorder().load_jsonl(tmp_path/'none.jsonl')==0

def test_no_data_report():
    assert BookDepthSessionReporter().build(BookDepthSessionRecorder()).status=='NO_DATA'

def test_insufficient_session():
    r=BookDepthSessionRecorder(); [add(r) for _ in range(99)]; assert BookDepthSessionReporter().build(r).status=='INSUFFICIENT_DATA'

def test_strong_session():
    r=BookDepthSessionRecorder(); [add(r) for _ in range(100)]; x=BookDepthSessionReporter().build(r); assert x.status=='STRONG_VALID_SESSION' and x.mature

def test_promising_session():
    r=BookDepthSessionRecorder(); [add(r) for _ in range(70)]; [add(r,'SHALLOW') for _ in range(30)]; assert BookDepthSessionReporter().build(r).status=='PROMISING_VALID_SESSION'

def test_degraded_session_requires_review():
    r=BookDepthSessionRecorder(); [add(r,'DEGRADED',source='DEGRADED',availability=.7,anomaly=1) for _ in range(100)]; x=BookDepthSessionReporter().build(r); assert x.status=='DEGRADED_SESSION' and x.action=='REVIEW_SOURCE'

def test_unstable_duplicate_source_requires_review():
    r=BookDepthSessionRecorder(); [add(r,duplicate=.9) for _ in range(100)]; x=BookDepthSessionReporter().build(r); assert x.status=='UNSTABLE_SOURCE' and x.action=='REVIEW_SOURCE'
