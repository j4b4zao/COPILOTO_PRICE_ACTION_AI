# Prospective Microstructure RC1

## Contract

The prospective capture is research-only and observational. It runs after the
official analysis cycle, never feeds its output back into Score, Risk,
Decision, Alert, or order execution, and keeps promotion disabled.

The warm-up recorder is cleared before the main window. Therefore, every
persisted prospective sample belongs to the synchronized session window.

## First infrastructure session — 2026-09-21 09:47

- Source file:
  `profit_rtd_rc54_3_2_WINV26_20260921_094726.json`.
- SHA-256:
  `d91b7fd05de05e9d240362db725af211d005d1c25ed1b2db8577bc1aaf9cd71f`.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles,
  357 analyzable samples, 243 skips, zero collection errors, zero missing
  prices, and zero Delta failures.
- Prospective integrity: 357 captured microstructure samples, exactly matching
  the 357 analyzable source samples.
- Warm-up ended after 295 cycles with `SIDEWAYS + PriceAction NONE`.
  Directional trade context was not required and was not ready at session
  start. This session therefore validates capture infrastructure only.

### Observed distribution

- 309 `INSUFFICIENT_DATA`, 46 `CONFLICT`, and 2 `CONFIRMED`.
- Zero `HIGH`, 2 `MEDIUM`, and zero three-source samples.
- 281 samples with zero independent sources, 70 with one, and 6 with two.
- Conflict rate: `0.1289`; average confidence: `0.0393`.
- Book evidence was available in all 357 samples; Order Flow momentum remained
  `INSUFFICIENT_DATA` in 262 samples.
- Session verdict: `WEAK / KEEP_OBSERVING`.

## Verdict

The prospective persistence path is technically validated, including the
warm-up boundary and complete source-to-evidence accounting. The session does
not validate predictive value and does not authorize freeze, OOS, promotion,
score influence, alerts, risk changes, decisions, or execution.

The next independent session should require directional trade context at the
start, or explicitly remain classified as another infrastructure diagnostic.

## First directional session — 2026-09-21 13:09

- Source file: `profit_rtd_rc54_3_2_WINV26_20260921_130942.json`.
- SHA-256:
  `a85544271ff2ac693535ae6ed1e6effb033846f7f1ff63d24208d69159337427`.
- Technical result: `COMPLETED`, `data_ready=True`, directional trade context
  ready at the start, 292 analyzable and prospectively captured samples, zero
  collection errors, zero missing prices, and zero Delta failures.
- Aggregate quality: one `HIGH`, 51 `MEDIUM`, one three-source sample, 27
  conflicts, high-quality rate `0.0034`, conflict rate `0.0925`, and average
  confidence `0.1193`.
- Session verdict: `WEAK / KEEP_OBSERVING`.

The fail-closed multi-session audit accepts this directional session but
returns `INSUFFICIENT_DATA / COLLECT_MORE_DATA`. The lower-bound evidence gap
is two additional independent directional sessions and eight aggregate
samples. Both requirements apply: satisfying the sample count alone is not
enough. Duplicate paths or hashes, invalid technical readiness, sample-count
mismatches, or any enabled influence flag exclude a session from aggregation.

No predictive or stability claim is allowed at this checkpoint. Score, Risk,
Decision, Alert, execution, and promotion remain disabled.
