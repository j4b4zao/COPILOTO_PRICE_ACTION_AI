"""Reconhecimento observacional de padrões da Psicologia do Trader (RC2)."""

from __future__ import annotations

from dataclasses import dataclass

from psychology.trader_psychology_state import TraderPsychologyState


@dataclass(frozen=True, slots=True)
class TraderPsychologyPolicy:
    maximum_trades_per_session: int = 6
    rushed_reentry_seconds: float = 60.0
    revenge_window_seconds: float = 180.0
    stop_sequence_threshold: int = 3
    extreme_daily_loss_r: float = 3.0
    overconfidence_size_multiplier: float = 1.5
    overconfidence_profit_r: float = 2.0

    def __post_init__(self):
        if self.maximum_trades_per_session < 1:
            raise ValueError("maximum_trades_per_session deve ser positivo.")
        if self.stop_sequence_threshold < 2:
            raise ValueError("stop_sequence_threshold deve ser pelo menos 2.")
        for name in (
            "rushed_reentry_seconds",
            "revenge_window_seconds",
            "extreme_daily_loss_r",
            "overconfidence_size_multiplier",
            "overconfidence_profit_r",
        ):
            if float(getattr(self, name)) <= 0:
                raise ValueError(f"{name} deve ser positivo.")
        if self.rushed_reentry_seconds > self.revenge_window_seconds:
            raise ValueError("Janela de pressa não pode exceder revenge window.")


@dataclass(frozen=True, slots=True)
class TraderPsychologySignal:
    code: str
    severity: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TraderPsychologyResult:
    status: str
    severity: str
    signals: tuple[TraderPsychologySignal, ...]
    pause_recommended: bool
    pause_reason_codes: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologyEngine:
    """Reconhece comportamento; não diagnostica, pontua ou bloqueia trades."""

    NAME = "TraderPsychologyEngine"
    VERSION = "RC2"
    SEVERITY_ORDER = {
        "NONE": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "EXTREME": 4,
    }

    def __init__(self, *, policy=None):
        self.policy = policy or TraderPsychologyPolicy()

    def analyze(self, state):
        if not isinstance(state, TraderPsychologyState):
            raise TypeError("state deve ser TraderPsychologyState.")

        signals = []
        recent = state.seconds_since_last_exit

        if state.trades_today >= self.policy.maximum_trades_per_session:
            signals.append(self._signal(
                "OVERTRADING",
                "HIGH",
                f"trades_today={state.trades_today}",
            ))

        revenge_evidence = []
        if (
            state.last_trade_was_loss
            and recent is not None
            and recent <= self.policy.revenge_window_seconds
        ):
            if state.increased_size_after_loss:
                revenge_evidence.append("increased_size_after_loss")
            if state.skipped_confirmation:
                revenge_evidence.append("skipped_confirmation")
            if not state.plan_checklist_passed:
                revenge_evidence.append("plan_checklist_failed")
        if revenge_evidence:
            signals.append(TraderPsychologySignal(
                code="REVENGE_TRADING",
                severity=(
                    "EXTREME"
                    if state.increased_size_after_loss
                    else "HIGH"
                ),
                evidence=tuple(revenge_evidence),
            ))

        if state.consecutive_losses >= self.policy.stop_sequence_threshold:
            signals.append(self._signal(
                "STOP_SEQUENCE",
                "EXTREME",
                f"consecutive_losses={state.consecutive_losses}",
            ))

        if state.chased_price or state.skipped_confirmation:
            evidence = []
            if state.chased_price:
                evidence.append("chased_price")
            if state.skipped_confirmation:
                evidence.append("skipped_confirmation")
            signals.append(TraderPsychologySignal(
                code="FOMO",
                severity="MEDIUM",
                evidence=tuple(evidence),
            ))

        if (
            recent is not None
            and recent <= self.policy.rushed_reentry_seconds
            and state.last_trade_was_loss
        ):
            signals.append(self._signal(
                "RUSHED_REENTRY",
                "HIGH",
                f"seconds_since_last_exit={float(recent)}",
            ))

        if (
            state.trade_size_multiplier
            >= self.policy.overconfidence_size_multiplier
            and state.session_pnl_r >= self.policy.overconfidence_profit_r
        ):
            signals.append(TraderPsychologySignal(
                code="OVERCONFIDENCE",
                severity="HIGH",
                evidence=(
                    f"trade_size_multiplier={float(state.trade_size_multiplier)}",
                    f"session_pnl_r={float(state.session_pnl_r)}",
                ),
            ))

        if not state.plan_checklist_passed:
            signals.append(self._signal(
                "OUTSIDE_PLAN",
                "HIGH",
                "plan_checklist_passed=False",
            ))

        pause_reasons = []
        if state.manual_pause_requested:
            pause_reasons.append("MANUAL_PAUSE")
        if state.daily_loss_r >= self.policy.extreme_daily_loss_r:
            pause_reasons.append("EXTREME_DAILY_LOSS")
        if state.consecutive_losses >= self.policy.stop_sequence_threshold:
            pause_reasons.append("STOP_SEQUENCE")
        if any(
            signal.code == "REVENGE_TRADING"
            and signal.severity == "EXTREME"
            for signal in signals
        ):
            pause_reasons.append("EXTREME_REVENGE_PATTERN")

        severity = self._maximum_severity(signals)
        if pause_reasons:
            severity = "EXTREME"

        return TraderPsychologyResult(
            status="NEUTRAL" if not signals else "ATTENTION",
            severity=severity,
            signals=tuple(signals),
            pause_recommended=bool(pause_reasons),
            pause_reason_codes=tuple(dict.fromkeys(pause_reasons)),
        )

    @classmethod
    def _maximum_severity(cls, signals):
        if not signals:
            return "NONE"
        return max(
            (signal.severity for signal in signals),
            key=cls.SEVERITY_ORDER.__getitem__,
        )

    @staticmethod
    def _signal(code, severity, *evidence):
        return TraderPsychologySignal(
            code=code,
            severity=severity,
            evidence=tuple(evidence),
        )
