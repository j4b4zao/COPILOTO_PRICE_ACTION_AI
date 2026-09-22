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

## Second directional session — 2026-09-21 16:30

- Source file: `profit_rtd_rc54_3_2_WINV26_20260921_163046.json`.
- SHA-256:
  `a3b74ad03c9338d28e0d81cf261e0c6d70d49ff4d20ca14e623695562ab90aa4`.
- Preflight: market activity ready, 66 analyzable updates, 31 price changes,
  two new M1 candles, and one transient read error; the directional capture
  itself recorded zero collection errors.
- Technical result: `COMPLETED`, `data_ready=True`, `UP + BUY` ready at the
  start, 343 analyzable and prospectively captured samples, zero missing
  prices, and zero Delta failures.
- Aggregate quality: one `HIGH`, 63 `MEDIUM`, one three-source sample, 96
  conflicts, high-quality rate `0.0029`, conflict rate `0.2799`, and average
  confidence `0.1665`.
- Session verdict: `DEGRADED_BY_CONFLICT / REVIEW_CONFLICTS`.

The multi-session audit now accepts two independent directional sessions and
635 samples, with no rejection. Weighted conflict is `0.1937`; stability
remains `INSUFFICIENT_DATA / COLLECT_MORE_DATA` because the three-session
minimum is not met. The remaining lower-bound gap is one independent
directional session and zero samples.

Conflict degradation is an observational diagnostic, not a technical failure
or operational signal. All influence and promotion flags remain disabled.

### Conflict decomposition

The first directional session recorded 27 conflicts. Its most frequent axis
was `PA BUY` against `Flow SELL`, with neutral structure and no directional
Book evidence (11 occurrences).

The second directional session recorded 96 conflicts. Of these, 80 (`83.3%`)
shared the same dominant signature: `PA BUY`, no directional Flow evidence,
structural evidence unavailable, and `Book SELL`. Thus, the conflict increase
was driven primarily by isolated Book pressure opposing the BUY context, not
by balanced disagreement among several independent sources. This is a cohort
composition diagnostic only; it does not justify changing weights, thresholds,
Score, Risk, Decision, Alert, execution, or promotion.

## Canonical prospective runner

Prospective captures now use one orchestrated entry point that holds the same
exclusive symbol lock across market-activity preflight, directional warm-up,
and the 600-cycle capture:

```powershell
python -m tools.profit_rtd_microstructure_prospective_orchestrated_session WINV26 `
  --preflight-cycles 90 --preflight-interval 0.25 `
  --cycles 600 --interval 0.25 --max-warmup-cycles 1800 `
  --output-dir data/profit_rtd_rc54_3_2
```

Directional readiness is required by default. Market inactivity, runner
collision, lateral-only warm-up, or technical non-readiness aborts without
admitting a prospective session.
