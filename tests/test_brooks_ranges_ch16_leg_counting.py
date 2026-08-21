from dataclasses import dataclass
from analysis.price_action.leg_count_dynamics import LegCountDynamics

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float

def c(o,h,l,cl):
    return Candle(o,h,l,cl)

def test_multiple_up_legs_mark_exhaustion():
    candles=[
        c(100,101,99,100.5),c(100.5,103,100,102.5),c(102.5,105,102,104.5),
        c(104.5,104.8,101.5,102),c(102,106,101.8,105.5),c(105.5,108,105,107.5),
        c(107.5,107.8,104.5,105),c(105,109,104.8,108.5),c(108.5,111,108,110.5),
        c(110.5,110.8,107.5,108),c(108,112,107.8,111.5),c(111.5,113,111,112.5),
        c(112.5,112.8,109.8,110.2),c(110.2,113.2,110,112.8),c(112.8,114,112.5,113.5),
        c(113.5,114.2,113,114),
    ]
    r=LegCountDynamics().analyze(candles)
    assert r.valid
    assert r.direction=="UP"
    assert r.leg_count>=3
    assert r.exhaustion_risk

def test_two_leg_complete():
    candles=[
        c(100,101,99,100),c(100,103,99.8,102.5),c(102.5,105,102,104),
        c(104,104.5,101.5,102),c(102,106,101.8,105.5),c(105.5,108,105,107),
        c(107,107.5,104.5,105),c(105,109,104.8,108.5),c(108.5,110,108,109.5),
        c(109.5,109.8,107,107.5),c(107.5,110.5,107.2,110),c(110,111,109.5,110.5),
        c(110.5,111.2,110,110.8),
    ]
    r=LegCountDynamics().analyze(candles)
    assert r.valid
    assert r.leg_count>=2
    assert r.two_leg_complete

def test_current_candle_is_excluded():
    base=[
        c(100,101,99,100),c(100,103,99.8,102.5),c(102.5,105,102,104),
        c(104,104.5,101.5,102),c(102,106,101.8,105.5),c(105.5,108,105,107),
        c(107,107.5,104.5,105),c(105,109,104.8,108.5),c(108.5,110,108,109.5),
        c(109.5,109.8,107,107.5),c(107.5,110.5,107.2,110),c(110,111,109.5,110.5),
    ]
    a=LegCountDynamics().analyze(base+[c(110.5,111,110,110.6)])
    b=LegCountDynamics().analyze(base+[c(110.5,120,90,119)])
    assert a.leg_count==b.leg_count
    assert a.pivot_count==b.pivot_count

def test_insufficient_history():
    r=LegCountDynamics().analyze([c(100,101,99,100)]*8)
    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons
