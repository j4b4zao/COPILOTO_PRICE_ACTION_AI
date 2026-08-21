# Brooks Trading Ranges — Chapter 11

## First Pullback Sequence

Diagnostic mapping implemented in `analysis/price_action/first_pullback_sequence_dynamics.py`.

Sequence tracked:

1. First bar pullback.
2. Minor trendline break.
3. Moving-average touch.
4. Close crossing the moving average.
5. Moving-average gap bar.
6. Major trendline break.
7. Longer two-leg pullback.
8. Transition to two-sided trading / trading range.

The module is intentionally diagnostic-only. It does not authorize trades and does not mutate Score, Risk, or Decision.

The current/forming candle is excluded from confirmation.
