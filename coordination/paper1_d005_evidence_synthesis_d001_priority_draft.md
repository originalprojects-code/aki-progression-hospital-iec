# Paper 1 D-005 evidence synthesis and D-001 priority plan

**Status:** Draft for independent scientific review. It changes no frozen definition, cohort, SQL policy, manuscript, or decision record. D-001–D-006 remain OPEN.

## Scope and terminology

The prediction landmark is 720 minutes after ICU admission. The frozen primary outcome is creatinine-defined KDIGO stage 2–3 in `(720, min(unitDischargeOffset, 4320)]`; strict-RRT composite remains separate. `E_frozen_reconstruction` is a retrospective reconstruction comparator, not confirmation that its creatinine-derived fields were clinically available at the landmark. The P3-C identifier-order comparison is nonchronological and is not a deployable index-stay policy.

This draft distinguishes three concepts that cannot be substituted for one another:

1. **Outcome-dependent patient selection:** frozen deterministic ranking orders `eligible_main_cohort` before identifier tie-breaks. Because eligibility requires a determinate post-landmark outcome, it can select stays using future information.
2. **Surveillance sufficiency:** the frozen negative-label branches require a stated measurement/follow-up pathway. This is an outcome-ascertainment convention, not evidence that measurement is clinically complete or missing at random.
3. **Observed-event ascertainment:** a future frozen-staged stage 2–3 event establishes a positive creatinine outcome. It is distinct from the rule used to call an apparent no-event stay negative or indeterminate.

## Verified numerical evidence

### D-005 observability context

The prior structural-observability audit recorded 144,926 candidate stays and 126,324 distinct patients. It found 70,324 stays with no future creatinine, 40,153 valid >=72-hour ICU stays, and 36,231 of those with a frozen selected creatinine in the 48–72-hour interval. There were 100,938 early alive ICU exits, of which 62,636 had a recent frozen selected creatinine; the frozen early-alive negative class had 39,140 stays and the frozen early-death indeterminate class had 3,317 stays. These are descriptive observation counts, not final model-cohort patient counts and not evidence that unmeasured AKI was absent.

### P3-A frozen-reconstruction comparison

The executed P3-A aggregate comparison reported 438 observed stage-2/3 positive **stays** excluded by the event-status-independent surveillance rule. In the same frozen-reconstruction stay universe, 64,242 stays were members under both the frozen and P3-A rules, 438 were frozen-only, none were P3-A-only, and 25,283 were neither. The 438 figure means that the proposed symmetric surveillance rule can exclude observed positives that do not meet its negative-surveillance proxy; it does not show that the events were false, that the P3-A rule is clinically superior, or that surveillance is adequate.

### P3-C selection and paired outcome-composition comparison

The P3-C membership comparison identified 1,109 patients for whom frozen eligibility-first selection and nonchronological identifier-order selection chose different stays. The paired audit for precisely this internally derived patient set reported 1,109 paired-detail rows. Pair/detail row differences, both pair/detail set differences, duplicate-key checks, selected-stay key-match checks, and genuine primary-label/event contradiction checks were all zero.

All three detailed paired transition partitions—primary outcome labels, observation classes, and observed stage-2/3 event status—were suppressed by the shared small-cell disclosure gate. Therefore, the released aggregate evidence does **not** identify how outcomes, observation classes, or observed-event status differ between the two selected stays. No suppressed cell may be reconstructed, inferred from totals, or requested through a follow-up query designed to evade the gate.

## Interpretive synthesis

The P3-A and P3-C results establish that the frozen analytic population is sensitive to two distinct design features. P3-A demonstrates that an event-status-independent surveillance eligibility proxy can remove observed-positive stays; P3-C demonstrates that the frozen eligibility-first rank and a nonchronological technical ordering select different stays for 1,109 patients. Neither result identifies a preferred policy.

The P3-C integrity results validate the paired construction, not the magnitude or direction of selected-stay outcome changes. Because detailed transitions were correctly suppressed, the evidence cannot support a claim that different selection changes outcome-label composition, observed AKI frequency, or the scientific target population in a known direction. The 1,109 count is a selection-disagreement count, not a known outcome-effect count.

The O0/O1 future-revision sensitivity is also separate: it quantified a mechanical outcome-series revision-censor scenario, not pre-landmark predictor availability. It cannot resolve whether a laboratory result was available to clinicians by minute 720.

## D-005 status and remaining questions

The current evidence supports describing a conditional, observed/sufficiently observed retrospective estimand only if researchers approve its exact observation rule and wording. It does not support an all-12-hour-ICU-patient deployment claim. Final D-005 approval remains blocked by:

- the clinical acceptability of the asymmetric positive/negative ascertainment rule;
- treatment of early alive exits, early expired exits, and no-future-creatinine stays;
- the target-population consequence of outcome-dependent frozen ranking;
- the role, if any, of the nonchronological P3-C sensitivity in the final protocol; and
- the unresolved laboratory availability decision D-001.

## D-001 next priority: focused static-only audit plan

### Decision question

D-001 asks which documented availability convention, if any, can govern laboratory predictors when eICU provides `labResultOffset` and `labResultRevisedOffset` but no verified first-clinical-result-availability timestamp. A late final revision must not be treated as the time at which the first result became available.

### Static work package

1. **Freeze a field-semantics inventory.** Read local contracts, source-schema documentation available in the repository, frozen SQL, and audit notes. For each lab field, record the evidence category: documented sample/measurement-related time, documented revision-related time, unknown first availability, or unsupported inference. Do not treat the labels sample time and result time as interchangeable unless documentation establishes that fact.
2. **Map the frozen predictor behavior.** Trace `sql/07_feature_labs.sql`: valid predictor rows are mapped and plausibility-filtered with `labResultOffset BETWEEN 0 AND 720`; it does not use `labResultRevisedOffset` and aggregates all valid rows by stay and feature. Separately trace `sql/02_creatinine_long.sql`: it permits a broader source-specific offset interval and chooses one row per stay/offset by descending `COALESCE(labResultRevisedOffset, labResultOffset)`, then descending `labID`.
3. **Separate the three scientific uses.** Inventory predictor-laboratory summaries, reference-creatinine selection, and future KDIGO outcome records separately. A restriction proposed for predictors must not be silently imposed on future outcome measurements; a revision proxy for reference selection is not proof of first availability.
4. **Register value-version ambiguity explicitly.** For repeated rows sharing stay, analyte, and offset, specify that the schema does not itself prove successive clinically visible versions. Preserve the grouping key requirement and distinguish ties, differing values, differing revision offsets, missing revision offsets, and negative offsets.
5. **Reconcile existing evidence without recomputation.** Keep the recorded findings separate by unit: 191 rebuilt-cohort records lacked reference creatinine confirmed by the audited revision proxy; excluding late revisions removed at least one physiologically valid laboratory record in 8,074 patients. These findings are sensitivity evidence, are non-additive, and do not establish model-performance or prediction changes.
6. **Prepare researcher-facing decision alternatives without selecting one.** Use the terms **sample-time proxy** and **sample-plus-revision-restricted proxy** only; do not reuse inconsistent L1/L2 labels. For each use case, specify whether the policy is frozen reference behavior, a proposed corrected primary policy, or a sensitivity analysis.

### Required static deliverables and acceptance checks

The static package should contain a traceability table linking each assertion to `contracts/feature_timing_policy.v1.json`, `contracts/decision_register.v1.json`, `sql/07_feature_labs.sql`, `sql/02_creatinine_long.sql`, and any locally available source documentation. It should explicitly list facts not established by the source, including first clinical availability and the clinical sequence of duplicate records. It must retain source-specific negative-offset semantics; no universal negative-offset decision is permitted.

No BigQuery SQL, dry-run, feature regeneration, cohort update, or model experiment is part of this work package. Any later aggregate audit requires a separately approved question, a disclosure design, a fixed denominator, and a predeclared distinction among laboratory rows, stay-offset/analyte groups, stays, and patients.

### Researcher decisions still required

1. Whether the sample-time proxy is the provisional primary predictor policy, with a revision-proxy sensitivity analysis; or whether another policy is required.
2. How the reference-creatinine and pre-landmark staging uses should relate to the predictor policy, without treating future outcome records as pre-landmark predictors.
3. How missing, negative, or inconsistent revision offsets should be represented in a corrected analysis.
4. Whether any future restriction is scientifically justified as an availability proxy rather than only a mechanical sensitivity.

Until these questions are resolved, D-001 remains `requires_researcher_approval`; no D-005 result should be interpreted as resolving it.
