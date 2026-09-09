# RC54.8 OOS Checkpoint — 2026-09-09

## Scope

This checkpoint records the state of RC54.8 after four fresh, sealed OOS sessions for the two RC54.7 frozen candidates.

Selection manifest:
- schema: `RC54_7_SELECTION_MANIFEST_V1`
- selection cutoff: `2026-09-01T00:00:00`
- SHA-256: `5990be21ec5bb3a9c33b75b6111f9e49c47f9725a358564b05deda6392148047`

Frozen candidates:
1. `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY`
2. `CONTEXT_SELL_MICRO_NEUTRAL`

Production RC54.8 gates remain unchanged:
- minimum candidate occurrences: 30
- minimum independent candidate-bearing sessions: 2
- minimum observations per horizon: 10
- minimum sessions per horizon: 2
- persisted session integrity required
- at least 2 supported horizons required for directional behavior to advance

Safety restrictions remain active:
- `observational_only=True`
- `predictive_claim_allowed=False`
- `score_influence_allowed=False`
- `risk_influence_allowed=False`
- `decision_influence_allowed=False`
- `order_execution_allowed=False`

## Fresh OOS sessions included

1. `profit_rtd_rc54_3_2_WINV26_20260908_130030.json`
   - samples: 58
   - session_id: `3c87671c52a342e3b057bb81a02f28ea`
   - evidence_sha256: `04561c35fdae4d7d949a0a786381e3d6c8162aae1452d5f46c1f40452f56b10b`

2. `profit_rtd_rc54_3_2_WINV26_20260908_170045.json`
   - samples: 67
   - session_id: `7e8eb45e0df14a0c87aaeb57798c7783`
   - evidence_sha256: `0b56bd26b5a2d4df8a53db1a5b885f85d85f024984015b6d96085bf508f1466b`

3. `profit_rtd_rc54_3_2_WINV26_20260909_114536.json`
   - samples: 61
   - session_id: `d9ac715360044b9292cdeafc07929198`
   - evidence_sha256: `493cb37d7f028245564802f263f6d073e692d5c512f41b4774b00e35e493e7de`

4. `profit_rtd_rc54_3_2_WINV26_20260909_125729.json`
   - samples: 56
   - session_id: `1591153b111a4004bdf3a5d5e2b7f445`
   - evidence_sha256: `8d0b897821122319a57e8620ff3b9287fa1a0b3f3794ac2e93794bbc3d450f5f`

## Candidate result — CONTEXT_SELL_MICRO_NEUTRAL

RC54.8 production validator result:
- holdout_session_count: 4
- sessions_with_candidate: 2
- candidate_occurrences: 98
- sessions_with_usable_candidate: 2
- usable_candidate_occurrences: 96
- coverage_met: `True`
- supported_horizons: 0
- verdict: `OOS_DIRECTIONAL_BEHAVIOR_NOT_CONFIRMED`

Per-horizon aggregate results:

| Horizon | Observations | Sessions | Mean delta | Favorable SELL rate | Direction supported |
| --- | ---: | ---: | ---: | ---: | --- |
| +1 | 96 | 2 | +1.0416666667 | 0.3020833333 | False |
| +3 | 92 | 2 | +3.4239130435 | 0.4239130435 | False |
| +5 | 88 | 2 | +6.0795454545 | 0.4431818182 | False |
| +10 | 78 | 2 | +10.1923076923 | 0.4102564103 | False |

Interpretation:
- global OOS coverage gate is satisfied;
- every horizon also satisfies the minimum observation/session coverage gate;
- zero horizons satisfy the frozen directional-support rule;
- the tested SELL directional behavior is therefore **not confirmed OOS**;
- no threshold or gate is relaxed to preserve this candidate.

RC54.8 state for this candidate: **closed as not directionally confirmed under the frozen RC54.8 rules**.

## Candidate result — CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY

RC54.8 production validator result:
- holdout_session_count: 4
- sessions_with_candidate: 0
- candidate_occurrences: 0
- sessions_with_usable_candidate: 0
- usable_candidate_occurrences: 0
- coverage_met: `False`
- supported_horizons: 0
- verdict: `MORE_OOS_CANDIDATE_COVERAGE_REQUIRED`

Interpretation:
- the candidate has not appeared in any of the four sealed OOS sessions;
- no directional conclusion is permitted;
- the candidate remains observational only and requires additional fresh independent OOS coverage.

RC54.8 state for this candidate: **open — additional OOS coverage required**.

## Decision at this checkpoint

- `CONTEXT_SELL_MICRO_NEUTRAL`: do not promote; OOS directional behavior not confirmed.
- `CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY`: keep under observation; additional OOS candidate coverage required.
- Do not alter RC54.7 selection thresholds or RC54.8 validation gates.
- Do not allow either candidate to influence Score, Risk, Decision, alerts with trading authority, or order execution.
- Additional collection, if performed, is for the remaining DIVERGENT coverage question, not to re-open or rescue MICRO_NEUTRAL under the same frozen test.
