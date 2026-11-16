"""Testes adversariais RC9.3 — executar com unittest ou pytest."""
import unittest
from contextlib import redirect_stdout
from io import StringIO

from alerts.alert_manager import AlertManager
from core.analysis_context import AnalysisContext


class AlertManagerSecurityRC93(unittest.TestCase):
    def setUp(self):
        self.manager = AlertManager()

    def context(self, action="BUY"):
        c = AnalysisContext()
        d = c.decision
        d.action = d.direction = d.signal = action
        d.valid = True
        d.setup = "TESTE_CONTROLADO"
        d.score = 95.0
        d.confidence = 0.95
        d.entry = 170000.0
        d.stop = 169800.0 if action == "BUY" else 170200.0
        d.target = 170400.0 if action == "BUY" else 169600.0
        c.risk.valid = True
        c.risk.approved = True
        return c

    def run_alert(self, c):
        with redirect_stdout(StringIO()):
            result = self.manager.executar(c)
        self.assertIs(result, c)
        return c.alert

    def test_valid_buy_sell(self):
        for action in ("BUY", "SELL"):
            with self.subTest(action=action):
                a = self.run_alert(self.context(action))
                self.assertTrue(a.valid)
                self.assertEqual(a.action, action)

    def test_wait(self):
        c = self.context()
        c.decision.action = "WAIT"
        a = self.run_alert(c)
        self.assertFalse(a.valid)
        self.assertEqual(a.action, "NONE")

    def test_adversarial(self):
        cases = {
            "decision_invalid": ("decision", "valid", False),
            "risk_not_approved": ("risk", "approved", False),
            "risk_invalid": ("risk", "valid", False),
            "direction_mismatch": ("decision", "direction", "SELL"),
            "signal_mismatch": ("decision", "signal", "SELL"),
            "entry_zero": ("decision", "entry", 0.0),
            "stop_wrong_side": ("decision", "stop", 170100.0),
            "target_wrong_side": ("decision", "target", 169900.0),
            "score_zero": ("decision", "score", 0.0),
            "confidence_zero": ("decision", "confidence", 0.0),
            "confidence_over_one": ("decision", "confidence", 1.1),
            "setup_empty": ("decision", "setup", ""),
            "entry_nan": ("decision", "entry", float("nan")),
            "stop_infinity": ("decision", "stop", float("inf")),
            "target_nan": ("decision", "target", float("nan")),
            "score_infinity": ("decision", "score", float("inf")),
            "confidence_nan": ("decision", "confidence", float("nan")),
            "rr_insufficient": ("decision", "target", 170100.0),
        }
        for name, (object_name, field, value) in cases.items():
            with self.subTest(name=name):
                c = self.context()
                setattr(getattr(c, object_name), field, value)
                a = self.run_alert(c)
                self.assertFalse(a.valid)
                self.assertEqual(a.action, "NONE")

    def test_old_alert_cleared(self):
        c = self.context()
        self.assertTrue(self.run_alert(c).valid)
        c.decision.valid = False
        a = self.run_alert(c)
        self.assertFalse(a.valid)
        self.assertEqual(a.action, "NONE")


if __name__ == "__main__":
    unittest.main()
