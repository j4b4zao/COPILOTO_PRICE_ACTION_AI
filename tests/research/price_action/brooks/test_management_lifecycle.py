from types import SimpleNamespace

import tools.profit_rtd_brooks_management_lifecycle as mod


def _sample(cid, o, h, l, c, *, entry=False):
    pa = {}

    if entry:
        pa.update(
            {
                "brooks_stop_target_entry_triggered": True,
                "brooks_stop_target_direction": "BUY",
                "brooks_stop_target_entry_price": 100.0,
                "brooks_stop_target_initial_stop": 95.0,
                "brooks_stop_target_stop_geometry_valid": True,
            }
        )

    return {
        "candle_evidence": {
            "candle_id": cid,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
        },
        "price_action": pa,
    }


def test_exact_candle_last_revision_creates_single_entry():
    payload = {
        "samples": [
            _sample("C1", 99, 101, 95, 100, entry=True),
            _sample("C1", 99, 102, 95, 101, entry=True),
            _sample("C2", 101, 103, 99, 102),
        ]
    }

    report = mod.build_lifecycles(payload)

    assert report["raw_samples"] == 3
    assert report["exact_candles"] == 2
    assert report["eligible_entry_episodes"] == 1
    assert (
        report["episodes"][0]["entry_event_candle_id"]
        == "C1"
    )


def test_lifecycle_persists_advanced_stop(monkeypatch):
    calls = []

    class FakeEngine:
        def analyze(
            self,
            candles,
            direction,
            entry_price,
            initial_stop,
            current_stop=None,
            tick_size=1.0,
        ):
            calls.append(current_stop)

            if len(calls) == 1:
                return SimpleNamespace(
                    state="TRAILING_STOP_ADVANCE",
                    reason="TEST_ADVANCE",
                    proposed_stop=97.0,
                    trailing_active=True,
                    stop_improved=True,
                    stop_loosened=False,
                    structural_advance_confirmed=True,
                    latest_swing_index=1,
                    latest_swing_price=98.0,
                    protected_r=0.4,
                )

            return SimpleNamespace(
                state="TRAILING_STOP_HOLD",
                reason="TEST_HOLD",
                proposed_stop=current_stop,
                trailing_active=True,
                stop_improved=False,
                stop_loosened=False,
                structural_advance_confirmed=False,
                latest_swing_index=2,
                latest_swing_price=99.0,
                protected_r=0.4,
            )

    monkeypatch.setattr(mod, "_ENGINE", FakeEngine())

    payload = {
        "samples": [
            _sample("C1", 99, 101, 95, 100, entry=True),
            _sample("C2", 100, 103, 98, 102),
            _sample("C3", 102, 105, 100, 104),
        ]
    }

    report = mod.build_lifecycles(payload)
    episode = report["episodes"][0]

    assert calls == [95.0, 97.0]
    assert episode["stop_revision_count"] == 1
    assert episode["current_stop"] == 97.0
    assert report["episodes_with_stop_advance"] == 1
    assert report["stop_advance_observations"] == 1
    assert (
        episode["observations"][0]["revision_applied"]
        is True
    )
    assert (
        episode["observations"][1]["previous_stop"]
        == 97.0
    )


def test_lifecycle_never_applies_looser_stop(monkeypatch):
    class FakeEngine:
        def analyze(self, *args, **kwargs):
            return SimpleNamespace(
                state="STOP_LOOSENING_REJECTED",
                reason="TEST_REJECT",
                proposed_stop=94.0,
                trailing_active=False,
                stop_improved=False,
                stop_loosened=True,
                structural_advance_confirmed=False,
                latest_swing_index=None,
                latest_swing_price=0.0,
                protected_r=0.0,
            )

    monkeypatch.setattr(mod, "_ENGINE", FakeEngine())

    payload = {
        "samples": [
            _sample("C1", 99, 101, 95, 100, entry=True),
            _sample("C2", 100, 103, 98, 102),
        ]
    }

    report = mod.build_lifecycles(payload)
    episode = report["episodes"][0]

    assert episode["current_stop"] == 95.0
    assert episode["stop_revision_count"] == 0
    assert (
        episode["observations"][0]["revision_applied"]
        is False
    )


def test_safety_contract_remains_research_only():
    payload = {
        "samples": [
            _sample("C1", 99, 101, 95, 100, entry=True),
            _sample("C2", 100, 103, 98, 102),
        ]
    }

    report = mod.build_lifecycles(payload)

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["predictive_claim_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["dynamic_management_validated"] is False
    assert report["hypothesis_freeze_allowed"] is False
