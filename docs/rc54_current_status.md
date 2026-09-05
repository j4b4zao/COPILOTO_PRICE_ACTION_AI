# RC54 Current Status

Checkpoint: 2026-09-05 (America/Sao_Paulo)

## Exact-candle clean selection checkpoint (2026-09-05)

- The exact-candle selection evidence was recomposed from three independent
  sessions: `154917`, `163915`, and `172520`. Together they provide 27 edge
  occurrences, 73 horizon evidence rows, 49 context buckets, and 16
  multi-horizon groups.
- The clean inventory is
  `data/profit_rtd_price_action_exact_selection/price_action_exact_inventory_clean_20260905.json`.
  Its verdict is `MORE_EVIDENCE_REQUIRED`: all 49 buckets remain below at least
  one gate and there are zero hypothesis-freeze candidates. The reported gaps
  are insufficient context sample, insufficient cross-session recurrence, and
  unconfirmed directional stability.
- Session `164118` is preserved but quarantined because its interval overlaps
  session `163915`; it is excluded from the clean inventory and from the clean
  Brooks audit. Paths, timestamps, sample counts, SHA-256 hashes, and the
  exclusion reason are recorded in
  `data/profit_rtd_price_action_exact_selection/exact_selection_integrity_manifest_20260905.json`.
- The clean Brooks breakout/pullback audit accepted the same three independent
  sessions, observed zero complete explicit sequences, and returned
  `MORE_EVIDENCE_REQUIRED`. No predictive claim or hypothesis freeze is
  permitted from this result.
- The checkpoint is committed and published on branch `projetocopiloto` at
  commit `1349d9c`. Focused verification passed: 25 tests.
- All artifacts remain `observational_only=True`; influence on ScoreEngine,
  RiskManager, DecisionEngine, alerts, and order execution remains disabled.

## Post-RC54 round 2 candidate freeze (2026-09-04 09:34)

- The sixth eligible selection session is
  `data/profit_rtd_post_rc54_round2_selection/profit_rtd_rc54_3_2_WINV26_20260904_093458.json`
  (SHA-256 `0d6da45e97e44c38b211ded28a66132c7bea78bfa44864b67b34530df7482825`).
  It spans `2026-09-04T09:26:02.327` through `2026-09-04T09:34:58.256` and
  completed with `data_ready=True`, 354 analyzable SELL-ready samples, 246
  source skips, and zero collection, Delta, or context-readiness failures.
- RC54.4 found three SELL microbuckets: 24
  `CONTEXT_SELL_DIVERGENT_TT_BUY_BOOK_SELL`, 5 `CONTEXT_SELL_MICRO_BUY`, and
  325 `CONTEXT_SELL_MICRO_NEUTRAL`; SELL is incrementally identifiable.
- The explicit six-session inventory is
  `data/profit_rtd_post_rc54_round2_selection/post_rc54_round2_inventory_20260904_093458.json`
  (SHA-256 `405002f7bfbfe23c1e88d5b84ef27f067b013284e850e9f0f58baf346363c8cd`).
  It accepts all six sessions, rejects none, and contains no OOS paths.
- RC54.7 now reports `CONTEXT_SELL_MICRO_NEUTRAL` as a robustness candidate:
  five supported sessions, three nonzero incremental sessions, four consistent
  horizons with a two-thirds negative majority, and evidence-gap lower bound 0.
- The candidate and all six selection paths/hashes are frozen in
  `data/profit_rtd_post_rc54_round2_selection/post_rc54_round2_candidate_freeze_20260904_093458.json`
  with selection cutoff `2026-09-04T09:34:58.256`. Future evidence must be
  written to a separate OOS directory and start strictly after this cutoff.
- RC54.8 must wait for at least two eligible OOS sessions jointly containing at
  least 30 candidate occurrences. The result remains observational only and has
  no influence on ScoreEngine, RiskManager, DecisionEngine, alerts, or execution.

## Post-RC54 round 2 fifth eligible selection session (2026-09-04 08:56)

- The fifth eligible round 2 selection session is
  `data/profit_rtd_post_rc54_round2_selection/profit_rtd_rc54_3_2_WINV26_20260904_085625.json`.
  It starts at `2026-09-04T08:47:02.010`, strictly after the round 2 temporal
  boundary, and ends at `2026-09-04T08:56:24.553`.
- Preflight reported real market activity. Warm-up reached `DOWN + SELL` after
  1428 cycles, then the 600-cycle session completed with `data_ready=True` and
  `trade_context_ready=True`: 351 analyzable samples, 249 unchanged/invalid
  source skips, zero collection errors, zero Delta failures/not-ready samples,
  and zero trade-context-not-ready samples.
- RC54.4 accepted all 351 samples in `CONTEXT_SELL_MICRO_NEUTRAL`. Because this
  was the only SELL microbucket in the session, its within-session incremental
  effect is not identifiable. Session SHA-256:
  `b7f109a13c7674507a4691e72a1a7b89cf6d445477b2eacb190be1fef46e2700`.
- The explicit five-session inventory is
  `data/profit_rtd_post_rc54_round2_selection/post_rc54_round2_inventory_20260904_085625.json`
  (SHA-256 `f72018885206b0a58306eda3d9be5a674626dec1e358d2f0c7fb8bf83bbea711`).
  It accepts all five selection sessions, rejects none, contains no OOS paths,
  and still reports `MORE_CROSS_SESSION_EVIDENCE_REQUIRED` with no robustness
  candidate.
- `CONTEXT_SELL_MICRO_NEUTRAL` now has 987 occurrences across four sessions,
  but only two sessions provide a nonzero within-SELL comparison. It has zero
  consistent horizons and a lower-bound gap of one additional suitable SELL
  session containing multiple microbuckets. A candidate is not frozen and
  RC54.8 remains blocked.
- This evidence remains `observational_only=True`; ScoreEngine, RiskManager,
  DecisionEngine, alerts, and execution are unchanged and uninfluenced.

## Post-RC54 round 2 fourth eligible selection session (2026-09-03 17:02)

- The fourth eligible round 2 selection session is
  `data/profit_rtd_post_rc54_round2_selection/profit_rtd_rc54_3_2_WINV26_20260903_170243.json`
  (SHA-256 `84d0c10796087c9aacfd4f637aed47fc35f8ee66009ca80ddc76c20128c96565`).
  It starts at `2026-09-03T16:52:01.809`, strictly after the round 2 temporal
  boundary, and ends at `2026-09-03T17:02:43.082`.
- Technical result: `COMPLETED`, `data_ready=True`, 421 analyzable and
  trade-context-ready SELL samples, 179 skipped cycles, zero collection
  errors, zero delta failures, and zero context-not-ready samples.
- RC54.4 found 19 `CONTEXT_SELL_DIVERGENT_TT_BUY_BOOK_SELL`, 327
  `CONTEXT_SELL_MICRO_NEUTRAL`, and 75 `CONTEXT_SELL_MICRO_SELL` samples.
  SELL is incrementally identifiable across three distinct microbuckets.
- The explicit four-session inventory is
  `data/profit_rtd_post_rc54_round2_selection/post_rc54_round2_inventory_20260903_170243.json`
  (SHA-256 `43f5cc1172c5bb8e9d17bf2985f38a690bab8ed49ca7235d536ba95c1107e2bd`).
  It accepts exactly four selection sessions, rejects none, contains no OOS
  paths, and returns `MORE_CROSS_SESSION_EVIDENCE_REQUIRED` with no robustness
  candidate.
- `CONTEXT_SELL_MICRO_NEUTRAL` now has 636 occurrences across three sessions,
  but still has an evidence-gap lower bound of one additional session. The
  other observed SELL microbuckets require at least two additional supporting
  sessions; `CONTEXT_BUY_MICRO_NEUTRAL` requires at least three.
- No candidate freeze, OOS collection, or RC54.8 is authorized. All outputs
  remain observational only with zero influence on ScoreEngine, RiskManager,
  DecisionEngine, alerts, and execution.

## Post-RC54 round 2 third eligible selection session (2026-09-03 16:21)

- The third eligible round 2 selection session is
  `data/profit_rtd_post_rc54_round2_selection/profit_rtd_rc54_3_2_WINV26_20260903_162139.json`
  (SHA-256 `4e01c493dbabe9e0550ccf481dfff32a1cc72d5eb24c2bbf483c1aaa65e152b7`).
  It starts at `2026-09-03T16:13:02.062`, strictly after the round 2 temporal
  boundary, and ends at `2026-09-03T16:21:39.765`.
- Technical result: `COMPLETED`, `data_ready=True`, 341 analyzable samples,
  259 skipped cycles, zero collection errors, zero delta failures, and
  `trade_context_ready_at_start=True`. The context later returned to
  `SIDEWAYS + PriceAction NONE`; 221 clean not-ready samples were excluded
  without converting the session to `COMPLETED_WITH_WARNINGS`.
- RC54.4 accepted 120 `CONTEXT_SELL_MICRO_NEUTRAL` samples and excluded the
  221 lateral samples. SELL has only one distinct microbucket in this session
  and is not incrementally identifiable by itself.
- The explicit three-session inventory is
  `data/profit_rtd_post_rc54_round2_selection/post_rc54_round2_inventory_20260903_162139.json`
  (SHA-256 `f8bc699e8259911af782c663e43ae126d1edb4ca586bddff08c952388b77372c`).
  It accepts exactly three selection sessions, rejects none, contains no OOS
  paths, and returns `MORE_CROSS_SESSION_EVIDENCE_REQUIRED` with no robustness
  candidate.
- `CONTEXT_SELL_MICRO_NEUTRAL` now has 309 occurrences across two sessions,
  but its incremental evidence-gap lower bound remains two additional
  sessions. `CONTEXT_BUY_MICRO_NEUTRAL` requires at least three additional
  sessions; the other observed SELL microbuckets require at least two.
- No candidate freeze, OOS collection, or RC54.8 is authorized. All outputs
  remain observational only with zero influence on ScoreEngine, RiskManager,
  DecisionEngine, alerts, and execution.

## Post-RC54 round 2 second eligible selection session (2026-09-03 15:37)

- The next eligible round 2 selection session is
  `data/profit_rtd_post_rc54_round2_selection/profit_rtd_rc54_3_2_WINV26_20260903_153737.json`
  (SHA-256 `677545ffaf818d99b63fde25f273317b14175797c98b209bd87168f174517ab8`).
  It starts at `2026-09-03T15:28:02.216`, strictly after the round 2 temporal
  boundary, and ends at `2026-09-03T15:37:37.172`.
- Technical result: `COMPLETED`, `data_ready=True`, 382 analyzable and
  trade-context-ready samples, 218 skipped cycles, zero collection errors,
  zero delta failures, and zero context-not-ready samples.
- RC54.4 found 382 `CONTEXT_BUY_MICRO_NEUTRAL` samples. BUY has only one
  distinct microbucket in this session and is not incrementally identifiable.
- The explicit two-session inventory is
  `data/profit_rtd_post_rc54_round2_selection/post_rc54_round2_inventory_20260903_153737.json`
  (SHA-256 `63adeb1c8f8d4a49cb08ed32d1cc978564d924fbb81c2b10c6cbf957abbca100`).
  It accepts exactly two selection sessions, rejects none, contains no OOS
  paths, and returns `MORE_CROSS_SESSION_EVIDENCE_REQUIRED` with no robustness
  candidate.
- Across the two sessions, `CONTEXT_BUY_MICRO_NEUTRAL` has 417 occurrences in
  two sessions, but no within-context microbucket variation. Its evidence-gap
  lower bound is three additional sessions. The three observed SELL
  microbuckets remain supported by only one session each and require at least
  two additional supporting sessions.
- No candidate freeze, OOS collection, or RC54.8 is authorized. All outputs
  remain observational only with zero influence on ScoreEngine, RiskManager,
  DecisionEngine, alerts, and execution.

## Post-RC54 round 2 first eligible selection session (2026-09-03 10:52)

- The second attempt produced the first eligible round 2 selection session:
  `data/profit_rtd_post_rc54_round2_selection/profit_rtd_rc54_3_2_WINV26_20260903_105250.json`
  (SHA-256 `b1367a9c4967dc9cf853bb751fceda480e4775bc35a29ee2626f600b3acebff3`).
  It starts at `2026-09-03T10:44:02.874`, strictly after the round 2 temporal
  boundary, and ends at `2026-09-03T10:52:50.808`.
- Technical result: `COMPLETED`, `data_ready=True`, 336 analyzable samples,
  264 skipped cycles, zero collection errors, zero delta failures, 261
  trade-context-ready samples, and 75 lateral samples excluded from RC54.4.
- RC54.4 found 35 `CONTEXT_BUY_MICRO_NEUTRAL`, 6
  `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY`, 31 `CONTEXT_SELL_MICRO_BUY`, and
  189 `CONTEXT_SELL_MICRO_NEUTRAL` samples. SELL is incrementally identifiable
  across three microbuckets; BUY has only one microbucket.
- The explicit one-session inventory is
  `data/profit_rtd_post_rc54_round2_selection/post_rc54_round2_inventory_20260903_105250.json`
  (SHA-256 `7396a1697efc272c768257e9198c89ea65757ff1676c41db31fcb68c99dde052`).
  It accepts one selection session, rejects none, contains no OOS paths, and
  returns `MORE_CROSS_SESSION_EVIDENCE_REQUIRED` with no robustness candidate.
- At least two additional supporting sessions are required for the observed
  SELL microbuckets; no candidate freeze or OOS collection is authorized.
  All outputs remain observational only with zero influence on ScoreEngine,
  RiskManager, DecisionEngine, alerts, and execution.

## Post-RC54 round 2 selection attempt (2026-09-03)

- A new, isolated selection cycle was opened in
  `data/profit_rtd_post_rc54_round2_selection`, with every previously observed
  session excluded and temporal boundary `2026-09-03T09:50:10.594`.
- The first attempt passed the 90-cycle real-market-activity preflight, built
  25 candles and 876 analyzable warm-up samples, but remained
  `SIDEWAYS + PriceAction NONE` through all 1800 warm-up cycles. The 600-cycle
  session did not start and no evidence file was created.
- The abort diagnostic now distinguishes `WARM_TRADE_CONTEXT_NOT_READY` from
  genuinely insufficient history (`WARM_HISTORY_NOT_READY`). This changes only
  reporting; readiness gates, observational isolation, ScoreEngine,
  RiskManager, DecisionEngine, alerts, and execution are unchanged.

## Post-RC54 OOS closure (2026-09-03 09:50)

- Fourth eligible OOS session:
  `data/profit_rtd_post_rc54_oos/profit_rtd_rc54_3_2_WINV26_20260903_095011.json`
  (SHA-256 `b0a6e74a3bd42f82771e0dd31ba80d8c7df6b573799844cf2c75e0b74b1b694a`).
  It is `COMPLETED`, `data_ready=True`, starts at
  `2026-09-03T09:42:02.214`, has 313 analyzable and trade-context-ready
  samples, 287 skipped cycles, and zero collection errors.
- RC54.4 identified SELL across four distinct microbuckets: 65
  `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY`, 6 `CONTEXT_SELL_MICRO_BUY`,
  239 `CONTEXT_SELL_MICRO_NEUTRAL`, and 3 `CONTEXT_SELL_MICRO_SELL`.
- The frozen candidate now has 302 occurrences across two independent OOS
  sessions. RC54.8 accepted exactly 5 frozen selection sessions and 4 separate
  OOS holdouts, with zero rejected sessions and no path/hash overlap.
- None of the four OOS horizons passed directional support. The final verdict
  is `OOS_DIRECTIONAL_BEHAVIOR_NOT_CONFIRMED`; this candidate is not eligible
  for promotion. The result remains observational only, with no influence on
  ScoreEngine, RiskManager, DecisionEngine, alerts, or execution.

## Post-RC54 OOS checkpoint (2026-09-02)

- Third eligible OOS session:
  `data/profit_rtd_post_rc54_oos/profit_rtd_rc54_3_2_WINV26_20260903_090850.json`
  (SHA-256 `135ffc39fbe9f4603bc22110e9507279f2d66a8976d4424d75b64a45c0c3ad04`).
  It is `COMPLETED`, `data_ready=True`, starts at
  `2026-09-03T09:00:01.644`, has 335 analyzable samples, 265 skipped cycles,
  zero collection errors, and 335 trade-context-ready samples.
- RC54.4 identified three BUY microbuckets: 41
  `CONTEXT_BUY_DIVERGENT_TT_SELL_BOOK_BUY`, 17 `CONTEXT_BUY_MICRO_BUY`, and
  277 `CONTEXT_BUY_MICRO_NEUTRAL`. The frozen SELL candidate occurred zero
  times.
- RC54.8 recomposition now accepts 5 frozen selection sessions and 3 separate
  OOS holdouts, with zero rejected sessions. Candidate coverage remains 63
  occurrences in only one holdout; verdict remains
  `MORE_OOS_CANDIDATE_COVERAGE_REQUIRED`.

- Selection remains frozen over exactly five sessions with candidate
  `CONTEXT_SELL_MICRO_NEUTRAL` and cutoff `2026-09-02T11:01:20.258`.
- Two independent post-cutoff OOS sessions are now technically eligible. The
  second is `data/profit_rtd_post_rc54_oos/profit_rtd_rc54_3_2_WINV26_20260902_151351.json`
  (SHA-256 `c1610f83355add22922b70ba161c012846be4dcdb2f9a4086676889ddcc78549`):
  `COMPLETED`, `data_ready=True`, 378 analyzable samples, 222 skipped cycles,
  zero collection errors, and all 378 samples trade-context-ready.
- RC54.4 identified BUY across three microbuckets: 6
  `CONTEXT_BUY_DIVERGENT_TT_SELL_BOOK_BUY`, 17 `CONTEXT_BUY_MICRO_BUY`, and
  355 `CONTEXT_BUY_MICRO_NEUTRAL`. This session contains zero occurrences of
  the frozen SELL candidate.
- RC54.8 ran with the five frozen selection paths and exactly the two separate
  OOS holdouts. Manifest valid: 5 selection accepted, 2 OOS accepted, zero
  rejected. Aggregate candidate coverage remains 63 occurrences in only one
  OOS session, so the verdict is `MORE_OOS_CANDIDATE_COVERAGE_REQUIRED`.
- Continue collecting independent OOS sessions until at least two sessions
  contain the frozen candidate. This is observational evidence only and does
  not authorize ScoreEngine, RiskManager, DecisionEngine, alerts, or execution.

## Current verdict

- Research state: `OOS_DIRECTIONAL_BEHAVIOR_NOT_CONFIRMED`.
- Robustness candidates: `CONTEXT_SELL_MICRO_NEUTRAL`.
- Candidate freeze: completed in
  `data/profit_rtd_rc54_3_2/rc54_candidate_freeze_20260831_1010.json`.
- Frozen selection cutoff: `2026-08-31T10:09:58.526000`.
- RC54.8/OOS: completed over eight eligible holdouts. Two independent sessions
  contain 393 total candidate occurrences, satisfying the frozen coverage gate.
  Zero of four horizons passed directional support; verdict:
  `OOS_DIRECTIONAL_BEHAVIOR_NOT_CONFIRMED`.
- Operational influence: prohibited for ScoreEngine, RiskManager,
  DecisionEngine, alerts, and order execution.

## Post-RC54 transition guardrail

- RC54 is closed with a negative OOS verdict for
  `CONTEXT_SELL_MICRO_NEUTRAL`; additional evaluation of the same frozen
  candidate is not required for this phase.
- Every selection and holdout sample through `2026-09-01T11:41:43.435` is now
  exposed historical evidence. None of the eight RC54 OOS files may be used to
  choose a replacement candidate.
- A subsequent research cycle must collect a fresh selection set whose first
  timestamp is strictly later than that boundary, store it outside both the
  frozen RC54 selection directory and the RC54 `oos` directory, and build a new
  manifest.
- Only that fresh selection set may pass through context audit, incremental
  analysis, cross-session robustness, candidate freeze, and then a new unseen
  OOS phase.
- The existing `RC55` test name in the repository belongs to the separate book
  diagnostics voice integration and must not be reused as the identifier for
  this research transition.
- The transition is frozen in
  `data/profit_rtd_post_rc54_selection/post_rc54_selection_freeze_20260901_114143.json`;
  fresh selection sessions must be written only to
  `data/profit_rtd_post_rc54_selection`.
- The first fresh-selection attempt on 2026-09-01 passed market-activity
  preflight but remained `SIDEWAYS + PriceAction NONE` through all 1800 warm-up
  cycles. It ended `ABORTED_CONTEXT_NOT_READY`; no session file was created and
  the fresh selection set remains empty.
- The second attempt produced the first eligible fresh-selection session:
  `profit_rtd_rc54_3_2_WINV26_20260901_151014.json`. It is `COMPLETED` with
  `data_ready=True`, 330 analyzable BUY-ready samples, 270 skipped cycles, zero
  collection errors, and timestamps `2026-09-01T15:02:03.490` through
  `2026-09-01T15:10:13.189`.
- BUY is incrementally identifiable across 321 `CONTEXT_BUY_MICRO_NEUTRAL` and
  9 `CONTEXT_BUY_MICRO_SELL` samples. No candidate is frozen: the new selection
  has only 2/3 minimum independent sessions. Its manifest is
  `data/profit_rtd_post_rc54_selection/post_rc54_selection_manifest_20260901.json`.
- The third attempt produced the second eligible fresh-selection session:
  `profit_rtd_rc54_3_2_WINV26_20260901_153903.json`. It is `COMPLETED` with
  `data_ready=True`, 341 analyzable SELL-ready samples, 259 skipped cycles,
  zero collection errors, and timestamps `2026-09-01T15:30:03.605` through
  `2026-09-01T15:39:03.205`.
- SELL is incrementally identifiable across 325 `CONTEXT_SELL_MICRO_NEUTRAL`,
  10 `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY`, and 6
  `CONTEXT_SELL_MICRO_BUY` samples. SHA-256:
  `65b0d3fe20d2dcf644e9d34746187dfe6d1f56f74fb130b860643bbc873666c1`.
- The two fresh sessions deliberately cover opposite directions and remain
  selection evidence only. The minimum gate is still unmet, robustness has not
  been evaluated, and no post-RC54 candidate or OOS cutoff is frozen.
- The fourth fresh-selection attempt passed the real-market-activity preflight
  and reached `history_ready=True`, with at least 24 M1 candles and 859
  analyzable updates observed during warm-up, but remained
  `SIDEWAYS + PriceAction NONE`. The runner ended without starting the 600-cycle
  session and created no evidence file. This is a clean non-ready trade context,
  not a technical warning; the manifest remains unchanged at 2/3 sessions.
- The fifth attempt produced the third eligible fresh-selection session:
  `profit_rtd_rc54_3_2_WINV26_20260901_165549.json`. It is `COMPLETED` with
  `data_ready=True`, 422 analyzable samples, 178 skipped cycles, zero collection
  errors, and timestamps `2026-09-01T16:44:02.509` through
  `2026-09-01T16:55:47.768`. SHA-256:
  `83fe8a4725f58f9552a8aade73ed70ba38893f698f29c9dc223ce39ea6405253`.
- RC54.4 accepted 317 context-ready samples (172
  `CONTEXT_BUY_MICRO_NEUTRAL` and 145 `CONTEXT_SELL_MICRO_NEUTRAL`) and cleanly
  excluded 105 lateral samples. Neither direction is incrementally identifiable
  within this session because each has only one distinct microbucket.
- The fresh-selection minimum is now met at 3/3 independent sessions. This is
  only permission to evaluate cross-session robustness; `candidate_frozen`
  remains false and no new OOS phase is authorized yet.
- RC54.5 accumulated exactly the three fresh manifest paths: 1093 technical
  samples, 988 context-ready samples, and 105 clean lateral exclusions. No
  bucket met the combined 30-occurrence/3-session threshold. The two dominant
  buckets have ample occurrences but only two supporting sessions: 493
  `CONTEXT_BUY_MICRO_NEUTRAL` and 470 `CONTEXT_SELL_MICRO_NEUTRAL`.
- RC54.7 returned `MORE_CROSS_SESSION_EVIDENCE_REQUIRED`, zero robustness
  candidates, and zero consistent horizons for every bucket. Its evidence-gap
  lower bound is two additional independent sessions for each observed bucket.
- Therefore the selection cycle remains open for additional fresh sessions.
  No candidate is frozen, no cutoff is established, and OOS validation remains
  prohibited until a genuinely robust candidate exists.
- The next attempt produced the fourth eligible fresh-selection session:
  `profit_rtd_rc54_3_2_WINV26_20260901_171919.json`. It is `COMPLETED` with
  `data_ready=True`, 272 analyzable samples, 328 skipped cycles, zero collection
  errors, and timestamps `2026-09-01T17:12:02.057` through
  `2026-09-01T17:19:19.828`. SHA-256:
  `8302e1dd6e84934ffb89f31a32456de1eed76aaa480f355bc50d2c80c5b5bd99`.
- RC54.4 accepted 186 SELL-ready samples across three microbuckets (123
  `CONTEXT_SELL_MICRO_NEUTRAL`, 62 `CONTEXT_SELL_MICRO_BUY`, and 1
  `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY`) and excluded 86 clean lateral
  samples. The fresh manifest now contains four eligible sessions.
- With four fresh sessions, RC54.5 reports 1365 technical samples, 1174
  context-ready samples, and 191 clean lateral exclusions.
  `CONTEXT_SELL_MICRO_NEUTRAL` now passes the accumulation threshold with 593
  occurrences across three sessions.
- RC54.7 still returns `MORE_CROSS_SESSION_EVIDENCE_REQUIRED` and zero robust
  candidates. `CONTEXT_SELL_MICRO_NEUTRAL` has three supporting sessions but
  only two sessions with nonzero horizon means; its lower-bound evidence gap is
  one additional independent session. `CONTEXT_SELL_MICRO_BUY` also has a
  one-session lower-bound gap. No freeze or OOS transition is authorized.
- The following fifth-session attempt was stopped by preflight as
  `MARKET_ACTIVITY_NOT_READY`, with insufficient analyzable updates,
  insufficient price movement, and no new M1 candle progress. No warm-up or
  600-cycle session started, no evidence file was created, and the fresh
  manifest remains unchanged at four eligible sessions. Resume only after a
  future preflight observes real RTD market activity.
- A subsequent confirmation preflight returned the same three
  `MARKET_ACTIVITY_NOT_READY` reasons and again stopped before warm-up. No file
  was created and the manifest remained unchanged. Further live attempts are
  closed for this inactive window.
- On 2026-09-02, market activity preflight passed and the fifth eligible fresh
  selection session completed as
  `profit_rtd_rc54_3_2_WINV26_20260902_110120.json`. It has
  `data_ready=True`, 316 analyzable samples, 284 skipped cycles, zero collection
  errors, and timestamps `2026-09-02T10:53:02.112` through
  `2026-09-02T11:01:20.258`. RC54.4 accepted 184 SELL-ready samples and cleanly
  excluded 132 later lateral samples.
- SELL is incrementally identifiable across three microbuckets: 169
  `CONTEXT_SELL_MICRO_NEUTRAL`, 9
  `CONTEXT_SELL_DIVERGENT_TT_BUY_BOOK_SELL`, and 6
  `CONTEXT_SELL_MICRO_SELL`. Session SHA-256:
  `20a52b04990d8eb5073a652d4e4ae521e36bab8113c71bff785c8b07fdde58b8`.
- The explicit five-session recomposition accepted 5/5 paths and RC54.7 now
  reports `CONTEXT_SELL_MICRO_NEUTRAL` as a genuine robustness candidate: four
  supporting sessions, three nonzero sessions at every horizon, four consistent
  horizons, and evidence-gap lower bound zero.
- The post-RC54 selection is now frozen in
  `data/profit_rtd_post_rc54_selection/post_rc54_candidate_freeze_20260902_110120.json`
  with cutoff `2026-09-02T11:01:20.258`. The five frozen selection paths and
  their hashes must never be mixed with the new unseen OOS phase.
- Two post-freeze OOS attempts passed the real-market-activity preflight but
  remained `SIDEWAYS + PriceAction NONE` for all 1800 warm-up cycles. The first
  observed 1042 analyzable updates and 28 M1 candles; the second observed 1086
  analyzable updates and 30 M1 candles. Both ended
  `ABORTED_CONTEXT_NOT_READY` before the 600-cycle session started.
- Neither attempt created an OOS file. The OOS directory remains empty, zero
  eligible holdouts are registered, and RC54.8 remains prohibited until at
  least two eligible unseen sessions jointly contain at least 30 occurrences of
  the frozen candidate.
- Two later attempts also spent the full 1800-cycle warm-up in a clean lateral
  context and created no file. A following attempt finally opened the gate at
  `DOWN + SELL` and completed the first eligible unseen OOS session:
  `data/profit_rtd_post_rc54_oos/profit_rtd_rc54_3_2_WINV26_20260902_143834.json`.
- The first eligible OOS session is `COMPLETED`, `data_ready=True`, with 367
  analyzable samples, 233 skipped cycles, zero collection errors, and timestamps
  `2026-09-02T14:29:01.945` through `2026-09-02T14:38:34.769`. Its SHA-256 is
  `9fc07b7502b2f2b33ce8d15ed56bb4e87d8196027a35f2319b34365468b9c023`.
- RC54.4 accepted 247 context-ready samples and excluded 120 clean lateral
  samples. The frozen candidate occurred 63 times. SELL is incrementally
  identifiable across three SELL microbuckets; BUY has only one microbucket and
  is not incrementally identifiable.
- The occurrence gate is met, but the independent-session gate remains 1/2.
  RC54.8 is still prohibited. Registry:
  `data/profit_rtd_post_rc54_oos/post_rc54_oos_registry_20260902.json`.

## Next live action

- Current clean checkpoint: five frozen fresh-selection sessions, zero active
  RC54 runners, no partial file, and `candidate_frozen=True` for
  `CONTEXT_SELL_MICRO_NEUTRAL`.
- Start a new unseen OOS phase only with sessions whose first timestamp is
  strictly later than `2026-09-02T11:01:20.258`, stored outside the frozen
  selection directory. Require at least two eligible OOS sessions and 30 total
  candidate occurrences before RC54.8.
- Never add new paths to the frozen selection manifest, never use the five
  frozen paths to select another candidate, and never mix selection with OOS.

## Implemented readiness semantics

- `data_ready` represents technical RTD, collection, continuity, synchronized
  price, and Delta integrity.
- `trade_context_ready` represents directional MarketStructure plus PriceAction
  readiness.
- `trade_context_ready_at_start` is the canonical session-start field;
  `context_ready_at_start` remains a legacy alias.
- `SIDEWAYS + PriceAction NONE` is a non-ready trade context, not a technical
  warning by itself.
- Technical failures remain warnings and exclude a session when
  `data_ready` is not explicitly true.
- Missing `data_ready` is never inferred as true, including in direct calls to
  RC54.4, RC54.5, RC54.5.5, RC54.7, RC54.8, or the recomposer.
- RC54.5.5 keeps `trade_context_ready_at_start=False` under diagnostic
  `trade_context_reasons`; it does not convert clean lateral data into a technical
  rejection.

## Evidence inventory

- Discovered sessions: 14.
- Accepted selection sessions: 8.
- Rejected sessions: 6 (`DATA_READY_NOT_TRUE` in all six), with overlapping
  technical evidence: 2 `COLLECTION_ERRORS_PRESENT`, 1
  `DELTA_FAILURES_PRESENT`, and 1 `SYNCHRONIZED_PRICE_NOT_VERIFIED`.
- Accepted OOS sessions inside the frozen selection inventory: 0. The separate
  holdout registry currently contains eight eligible OOS sessions.
- Three accepted sessions contain zero directional-ready samples. They remain
  technically valid lateral evidence and contribute no RC54.7 bucket vote.
- Full report:
  `data/profit_rtd_rc54_3_2/rc54_full_inventory_20260831_1010.json`.

The accepted sessions end at:

- `20260828_103407`
- `20260828_115900`
- `20260828_130401`
- `20260828_154015`
- `20260828_155916`
- `20260828_164858`
- `20260831_085053`
- `20260831_100958`

## Evidence gap

- BUY is incrementally identifiable only in the session ending at 11:59.
- SELL is incrementally identifiable in the sessions ending at 10:34 on
  2026-08-28 and 08:50 on 2026-08-31.
- The other four accepted sessions do not contain enough within-context
  microbucket diversity to identify an incremental effect.
- `CONTEXT_SELL_MICRO_NEUTRAL` now has three supporting sessions with non-zero
  votes, zero evidence deficit, and consistent negative incremental signs at
  horizons 1, 3, 5, and 10. It is the first RC54.7 robustness candidate.
- `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY`, `CONTEXT_SELL_MICRO_BUY`, and
  `CONTEXT_SELL_MICRO_SELL` each have a lower bound of one additional session;
  the remaining observed buckets need at least two.

## Latest frozen-selection live session

- Selection session: `profit_rtd_rc54_3_2_WINV26_20260831_100958.json`. This is
  not an OOS holdout; the latest eligible OOS session is documented separately
  below.
- Preflight confirmed market activity; the directional-at-start gate waited
  through `SIDEWAYS + PriceAction NONE` and started only at `DOWN + SELL`.
- Result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 351 analyzable
  samples, 249 skipped cycles, and zero collection errors.
- All 351 analyzable samples were trade-context-ready. SELL was incrementally
  identifiable across four distinct microbuckets.
- The session remains `observational_only=True`; every Score, Risk, Decision,
  alert, and execution influence flag remains false.

## Next live collection

Run only when market activity is confirmed and no other RC54 runner is active:

```powershell
python tools/profit_rtd_rc54_5_4_orchestrated_session_runner.py WINV26 `
  --preflight-cycles 90 `
  --preflight-interval 0.25 `
  --cycles 600 `
  --interval 0.25 `
  --max-warmup-cycles 1800 `
  --require-trade-context-at-start `
  --concise-output `
  --progress-every 50 `
  --output-dir data/profit_rtd_rc54_3_2/oos
```

Accept the resulting session as evidence only with `data_ready=True`. Record
`incrementally_identifiable_contexts` and the distinct microbuckets for BUY and
SELL. Lack of identifiability is diagnostic only and does not invalidate clean
technical data.

Do not run selection discovery over `oos`. Refresh the frozen selection
inventory only when explicitly performing a new selection phase; ordinary OOS
collection updates only the separate holdout registry. The selection-only
recomposition command remains:

```powershell
python tools/profit_rtd_rc54_offline_recomposer.py `
  --discover-dir data/profit_rtd_rc54_3_2 `
  --output data/profit_rtd_rc54_3_2/rc54_full_inventory_latest.json
```

## Candidate and OOS guardrail

The frozen candidate is `CONTEXT_SELL_MICRO_NEUTRAL` and the selection cutoff is
`2026-08-31T10:09:58.526000`. Accept only newly collected holdout sessions whose
first sample is strictly later than this cutoff. Never mix a selection path or
SHA-256-identical file into OOS. Run RC54.8 only after at least two eligible OOS
sessions jointly contain at least 30 candidate occurrences.

## OOS collection

- Registry: `oos/rc54_oos_registry_20260831.json`.
- Eighth eligible holdout:
  `oos/profit_rtd_rc54_3_2_WINV26_20260901_114143.json`.
- First/last timestamps: `2026-09-01T11:32:04.023` /
  `2026-09-01T11:41:43.435`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 348
  analyzable samples, 252 skipped cycles, zero collection errors, 107
  trade-context-ready SELL samples, and 241 clean lateral samples excluded from
  the context audit.
- SELL was incrementally identifiable across 3
  `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY` and 104
  `CONTEXT_SELL_MICRO_NEUTRAL` samples. SHA-256:
  `dbecfc080ca8b2b3ec49c3c17fa31f145f5b40dec8be2c386e212ca1b8974a2b`.
- RC54.8 then evaluated all eight registered holdouts: 393 candidate occurrences
  across two sessions, but zero supported horizons. Candidate mean deltas were
  -0.51, -1.61, -2.49, and -4.28 points at horizons 1, 3, 5, and 10; favorable
  rates were 36.6%, 50.8%, 52.2%, and 54.0%, respectively. The frozen candidate
  failed OOS directional confirmation and is not eligible for promotion.
- Seventh eligible holdout:
  `oos/profit_rtd_rc54_3_2_WINV26_20260901_110243.json`.
- First/last timestamps: `2026-09-01T10:55:00.963` /
  `2026-09-01T11:02:42.884`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 292
  analyzable and trade-context-ready SELL samples, 308 skipped cycles, and zero
  collection errors.
- SELL was incrementally identifiable across two microbuckets: 3
  `CONTEXT_SELL_MICRO_BUY` and 289 `CONTEXT_SELL_MICRO_NEUTRAL`. This is the
  first OOS session containing the frozen candidate. The 30-occurrence threshold
  is exceeded, but a second independent candidate-containing session is still
  required before RC54.8. SHA-256:
  `915d695dd304169c28ec411ab788cb4ffb8ab7cdda63a0ce78eb3653573ab0a6`.
- Sixth eligible holdout:
  `oos/profit_rtd_rc54_3_2_WINV26_20260901_103632.json`.
- First/last timestamps: `2026-09-01T10:29:00.983` /
  `2026-09-01T10:36:31.048`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 280
  analyzable samples, 320 skipped cycles, zero collection errors, 225
  trade-context-ready BUY samples, and 55 clean lateral samples excluded from
  the context audit.
- BUY was incrementally identifiable across four microbuckets: 3
  `CONTEXT_BUY_DIVERGENT_TT_BUY_BOOK_SELL`, 7 `CONTEXT_BUY_MICRO_BUY`, 181
  `CONTEXT_BUY_MICRO_NEUTRAL`, and 34 `CONTEXT_BUY_MICRO_SELL`. The frozen SELL
  candidate occurred zero times. SHA-256:
  `6ba0d8367794678659d31e77cd56f0439fe214f233117d401eb1c3444f85eb3d`.
- Fifth eligible holdout:
  `oos/profit_rtd_rc54_3_2_WINV26_20260901_100355.json`.
- First/last timestamps: `2026-09-01T09:56:00.662` /
  `2026-09-01T10:03:54.599`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 309
  analyzable and trade-context-ready samples, 291 skipped cycles, and zero
  collection errors.
- BUY was incrementally identifiable across five microbuckets: 73
  `CONTEXT_BUY_DIVERGENT_TT_BUY_BOOK_SELL`, 3
  `CONTEXT_BUY_DIVERGENT_TT_SELL_BOOK_BUY`, 9 `CONTEXT_BUY_MICRO_BUY`, 190
  `CONTEXT_BUY_MICRO_NEUTRAL`, and 34 `CONTEXT_BUY_MICRO_SELL`. The frozen SELL
  candidate occurred zero times. SHA-256:
  `224c18db1a84e41b4ad748fe9d9a56e9a0e1a7dd6f075b2e7025a852c4e840c1`.
- The 2026-09-01 opening attempt passed market-activity preflight and observed
  981 analyzable updates forming 26 candles, with `history_ready=True`, but
  remained `SIDEWAYS + PriceAction NONE` through all 1800 warm-up cycles. It
  ended as `ABORTED_CONTEXT_NOT_READY`; no session file was created and the OOS
  registry was unchanged.
- The sixth OOS attempt after 17:20 was rejected by preflight as
  `MARKET_ACTIVITY_NOT_READY` due to insufficient analyzable updates,
  insufficient price movement, and no new M1 candle progress. No warm-up or
  session started, no evidence file was created, and the registry was unchanged.
- A confirmation preflight at 17:30 returned the same three activity failures.
  It also stopped before warm-up and left the OOS evidence set unchanged.
- The final preflight at 17:44 again returned `MARKET_ACTIVITY_NOT_READY` with
  the same reasons and stopped before warm-up. Live collection was closed for
  this window; resume only after a future preflight observes real RTD activity.
- Fourth eligible holdout:
  `oos/profit_rtd_rc54_3_2_WINV26_20260831_172044.json`.
- First/last timestamps: `2026-08-31T17:13:01.102` /
  `2026-08-31T17:20:44.961`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 292
  analyzable and trade-context-ready samples, 308 skipped cycles, and zero
  collection errors.
- BUY was incrementally identifiable across two buckets: 216
  `CONTEXT_BUY_MICRO_NEUTRAL` and 76
  `CONTEXT_BUY_DIVERGENT_TT_SELL_BOOK_BUY`. The frozen SELL candidate occurred
  zero times. SHA-256:
  `468568d0b06aac01b5c304baef83033c896cf508b6033c2f32d3d787a3242faa`.
- The fourth OOS attempt at 16:17 passed market-activity preflight and observed
  1010 analyzable updates forming 27 candles, with `history_ready=True`, but
  remained `SIDEWAYS + PriceAction NONE` through all 1800 warm-up cycles. It
  ended as `ABORTED_CONTEXT_NOT_READY`; `session_started=False`, no session file
  was created, and the OOS registry was not changed.
- The second OOS attempt at 13:00 passed market-activity preflight but exhausted
  all 1800 warm-up cycles in `SIDEWAYS + PriceAction NONE`. It ended as
  `ABORTED_CONTEXT_NOT_READY`; no session file was created and the OOS registry
  was not changed.
- Second eligible holdout:
  `oos/profit_rtd_rc54_3_2_WINV26_20260831_144615.json`.
- First/last timestamps: `2026-08-31T14:37:01.681` /
  `2026-08-31T14:46:15.921`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 377
  analyzable and trade-context-ready samples, 223 skipped cycles, and zero
  collection errors.
- The second holdout contained 323 `CONTEXT_BUY_MICRO_NEUTRAL` and 54
  `CONTEXT_BUY_MICRO_SELL` samples, with zero occurrences of the frozen
  `CONTEXT_SELL_MICRO_NEUTRAL` candidate.
- SHA-256:
  `c374486a4f1e21602ca39d1a337f14c5be67efd95619ea4e075cb34db13a8dc4`.
- Third eligible holdout:
  `oos/profit_rtd_rc54_3_2_WINV26_20260831_161119.json`.
- First/last timestamps: `2026-08-31T16:02:02.177` /
  `2026-08-31T16:11:18.812`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 372 analyzable samples, 228
  skipped cycles, zero collection errors, 276 trade-context-ready samples, and
  96 clean lateral samples excluded from the context audit.
- The third holdout was BUY-only and contained zero occurrences of the frozen
  SELL candidate. SHA-256:
  `80a74ea9b057b183c339907808519eff59414676ea424acd7c1cc5090d1313ed`.
- First holdout: `oos/profit_rtd_rc54_3_2_WINV26_20260831_112656.json`.
- First/last timestamps: `2026-08-31T11:19:00.588` /
  `2026-08-31T11:26:56.293`, strictly after the frozen cutoff.
- Technical result: `COMPLETED`, `data_ready=True`, 600 requested cycles, 293
  analyzable samples, 307 skipped cycles, and zero collection errors.
- RC54.4 accepted 259 BUY-ready samples and excluded 34 later lateral
  `SIDEWAYS + PriceAction NONE` samples without a technical warning.
- Frozen candidate occurrences: 0. This is valid OOS market coverage but adds
  no candidate coverage; RC54.8 was not executed.
- SHA-256:
  `eba8002e09e9c3276eabbd227a3bf2c4f20218a39d2e43c0d2d57d7d2f55e97b`.

## Verification checkpoint

- 18 RC54 test files pass.
- After the four-session post-RC54 robustness update, all four fresh-selection
  paths and SHA-256 hashes were revalidated. Each session is `COMPLETED`, has
  `data_ready=True`, starts strictly after `2026-09-01T11:41:43.435`, is unique,
  and is outside the RC54 OOS directory. The fresh manifest is valid and still
  declares `candidate_frozen=False`.
- All 18 RC54 standalone test programs were run again after this validation and
  passed, including the offline recomposer and global operational-isolation
  test.
- After the 17:30 inactive-market preflight, all 18 RC54 test programs were run
  again and passed. The frozen inventory hash, all eight selection hashes, and
  all four OOS hashes were revalidated; selection and OOS remain disjoint, and
  every holdout starts strictly after the frozen cutoff.
- After the 2026-08-31 live session, all 18 RC54 test files pass as standalone
  test programs, including the offline recomposer and global operational
  isolation checks. The bundled runtime does not include the optional `pytest`
  package.
- The global AST isolation test passes.
- Every RC54 utility declares `risk_influence_allowed=False`.
- All reports retain observational-only and no-influence flags.
- Changes are saved locally and remain uncommitted.

## Version-control safety

The repository is a mixed dirty worktree. It contains unrelated staged and
unstaged changes in operational modules, spreadsheets, generated bytecode, older
RC phases, and research utilities. Several RC54 files are partially staged
(`AM`), so the index does not necessarily contain the same version that passed
the tests described above.

Do not use bulk `git add`, `git commit -a`, checkout/reset, or cleanup commands.
Before any commit, review both the staged and unstaged diff for each explicit
RC54 path, isolate only the intended files, and rerun the RC54 suite against the
exact content to be committed. In particular, do not include existing changes
to ScoreEngine, RiskManager, DecisionEngine, alerts, strategies, spreadsheets,
or generated `__pycache__` files as part of RC54.3.3.

The normative procedure is in `docs/rc54_readiness_evidence_protocol.md`.
