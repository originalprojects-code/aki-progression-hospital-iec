# Paper 1 D-005 scientific method decision draft

**Status:** Conditional scientific direction approved for P0-modified + P3 planning; D-005 is not finally approved, and no protocol, SQL, or execution authorization follows from this document. D-001–D-006 remain OPEN.

## Recommended provisional direction

### Primary estimand: P0-modified

The proposed primary estimand is the conditional risk of an **observed creatinine-defined KDIGO stage 2–3 event**, under the frozen surveillance and outcome-ascertainment policy, among analytically eligible candidate stays. The landmark is exactly 720 minutes after ICU admission. The outcome window is `(720, min(unitDischargeOffset, 4320)]` minutes. The outcome remains creatinine-defined; strict-RRT composite outcomes remain separate.

This is a conditional ascertainment estimand, not an estimate of unobserved biological AKI incidence in every patient present in ICU at 12 hours. The target population must therefore be described as an analytically eligible, observed/sufficiently observed ICU population, not all 12-hour ICU patients.

### Candidate sufficient-observability rule for approval

The candidate rule retains frozen observation branches without changing them:

1. An observed incident stage 2–3 creatinine event is a positive frozen-window outcome.
2. A no-event negative label requires either a valid ≥72-hour ICU stay plus a frozen-selected creatinine in `(2880, 4320]`, or early alive ICU exit after 12 hours and before 72 hours plus a frozen-selected post-landmark creatinine in the final 1,440 minutes before ICU exit.
3. Early ICU exits with `expired` status and no observed event, no future creatinine, and other inadequate-follow-up paths remain indeterminate, not negative.

The ascertainment is asymmetric: an observed event establishes positivity, while an apparent negative requires additional observation evidence. This can select on measurement processes associated with discharge practice, death, severity, hospital workflow, and clinician testing. It preserves frozen outcome ascertainment but does not establish clinical completeness of surveillance or an exact death timestamp.

## Verified observability evidence

All figures below are structural-candidate **stays**, not final model-cohort patients, unless a distinct-patient count is explicitly shown.

| Evidence item | Verified result | Interpretation boundary |
|---|---:|---|
| Structural candidates | 144,926 stays; 126,324 patients | Pre-final-selection observational universe. |
| No future creatinine | 70,324 stays | Not evidence of no AKI. |
| Valid ≥72-hour ICU observation | 40,153 stays | Discharge-duration condition, not clinically validated surveillance. |
| 48–72-h creatinine among valid ≥72-h stays | 36,231 stays (90.23%) | Frozen selected creatinine records only. |
| Early alive ICU exit | 100,938 stays | Exit after 12 h and before 72 h with frozen `alive` status. |
| Recent creatinine among early alive exits | 62,636 stays (62.05%) | Event-status independent. |
| Frozen early-alive negative class | 39,140 stays | Exact frozen-count reconciliation. |
| Frozen early-death indeterminate class | 3,317 stays | No observed stage 2–3 under frozen branch ordering; not exact death timing. |

Audit B found substantial hospital-level heterogeneity among 199 hospitals with at least 11 structural-candidate stays (9 lower-volume hospitals withheld): no-future-creatinine rates ranged from 18.18% to 100.00% (median 54.23%). This is descriptive surveillance evidence, not causal evidence of care quality or outcome effect.

## Consequences of conditioning on surveillance

Post-landmark laboratory surveillance may reflect discharge practice, death, severity, hospital workflow, and clinician testing. Conditioning on it changes the estimand and can induce selection bias. The frozen rule is asymmetric: an observed event can establish positivity, whereas apparent negatives require stated surveillance evidence. This is outcome ascertainment logic, not proof that selection is outcome-independent.

The frozen deterministic patient-level rank orders stays by `eligible_main_cohort DESC` before chronological tie-breaking. Main eligibility requires a non-NULL post-landmark outcome. Thus the frozen selection can select a stay using information unavailable at the 12-hour landmark. It is appropriate only for an explicitly conditional retrospective analytic cohort; it must not be described as an operational 12-hour index-stay rule.

Therefore, a 12-hour score can be evaluated within P0-modified, but current evidence does **not** demonstrate deployability to all patients present in ICU at 12 hours. An all-patient deployment claim needs a pre-landmark index-stay policy and an outcome-observation strategy that does not use future surveillance for eligibility.

## Proposed prespecified P3 sensitivity set

| Sensitivity estimand | Comparison | What it assesses | Feasibility limit |
|---|---|---|---|
| P3-A: surveillance restriction | P0-modified versus an event-status-independent surveillance-eligibility rule | Sensitivity of cohort composition and labels to surveillance definition | Exact alternative rule requires researcher approval and may exclude observed positives; no results are implied. It cannot validate clinical adequacy. |
| P3-B: hospital surveillance context | Hospital-disjoint evaluation by prespecified surveillance strata | Whether observed performance/generalizability varies with surveillance context | Requires leakage-safe model evaluation; Audit B cannot estimate performance. |
| P3-C: patient-stay selection (**required robustness check**) | Frozen eligibility-first ranking versus a prespecified pre-landmark, outcome-independent index-stay rule | Whether post-outcome eligibility changes selected stays | Requires separately approved index-stay definition. A material difference requires reconsideration of the primary cohort definition. |
| P3-D: outcome-series timing | Existing O0/O1 future-revision sensitivity, separate from D-001 | Mechanical outcome-series sensitivity to revision censoring | Does not establish first clinical availability. |

P2 remains exploratory only. A terminal ICU-exit formulation could use documented exit offset/status if approved, but it cannot be called a death-time competing-risk analysis without evidence for exact death timing.

## Hospital-disjoint validation and reporting

Hospital-disjoint splitting remains necessary, but it does not remove hospital-specific measurement selection. For P0-modified, preprocessing, feature selection, imputation, calibration, thresholding, and tuning must be fit only in outer-training hospitals. Reports should name the conditional observed population and must not generalize performance to inadequately observed stays.

## Remaining blockers before D-005 approval

1. Approve, reject, or revise the candidate sufficient-observability rule, including the asymmetric treatment of observed positives and apparent negatives.
2. Decide whether the primary claim is conditional retrospective risk or an operational all-patient prediction claim; current evidence supports only the former.
3. Approve the P3 estimands and reporting denominators, including P3-C as a required robustness check, before any required future executions.
4. Approve a pre-landmark index-stay policy if deployability is intended.
5. Decide whether P2 remains exploratory or is removed; ICU exit status is not an exact death timestamp.
6. Resolve D-001 and remaining timing/feature decisions, which are distinct from D-005.

## Go/no-go checklist for final D-005 approval

### Scientific decisions still required

- [ ] Approve, reject, or revise P0-modified as the primary estimand.
- [ ] Approve the exact sufficient-observability branches and treatment of event-positive stays, early alive exit, early death, and no-future records.
- [ ] Approve conditional-population wording and the prohibition on an all-patient deployment claim.
- [ ] Approve the P3 sensitivity set and prespecified reporting plan, including the event-status-independent P3-A alternative and required P3-C index-stay policy.
- [ ] Decide whether P2 remains exploratory or is removed pending new evidence.

### Separate future-execution authorization required

- [ ] Authorize the P3-C cohort-membership robustness comparison only after approving its pre-landmark, outcome-independent index-stay policy.
- [ ] Authorize any P3-A alternative-observability cohort/outcome comparison only after approving its exact rule.
- [ ] Authorize any subsequent feature-matrix generation, model fitting, or hospital-disjoint validation separately.
- [ ] Confirm that a material P3-C selection difference is a no-go for retaining the frozen primary cohort definition without further scientific review.

No frozen SQL, cohort table, model, manuscript result, or decision register was changed by this draft.
