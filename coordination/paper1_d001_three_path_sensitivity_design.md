# Paper 1 D-001 three-path mechanical sensitivity design

**Status:** Static design for researcher review only. It does not change frozen SQL, cohort definitions, contracts, or decision-register status. No BigQuery operation, patient-level retrieval, model work, or manuscript change occurred. D-001–D-006 remain OPEN.

## Purpose and shared interpretation limits

This design separates three mechanical questions that are often conflated: predictor summarisation, reference-creatinine selection, and pre-landmark creatinine trajectory/staging. Each alternative uses a **sample-plus-revision-restricted proxy**, not a timestamp proven to represent first clinical availability. A late final revision neither proves that the first result was late nor proves that the selected final value was available at the 720-minute landmark.

The source does not establish `labID` as chronological, and same-stay/same-offset rows are not assumed to be successive versions of one clinical measurement. All comparisons must therefore report selection mechanics and observed data differences, not clinical visibility or confirmed temporal leakage. Future outcome measurements remain outside this D-001 design.

| Shared convention | Mechanical definition | Guardrail |
|---|---|---|
| Landmark | 720 minutes after ICU admission. | Source-specific negative-offset rules remain distinct from the predictor window. |
| Revision proxy | `COALESCE(labResultRevisedOffset, labResultOffset)`. | It is a reproducible proxy only; missing revision values fall back to sample offset and must be counted separately. |
| Numeric comparison | Treat two non-NULL `FLOAT64` values as different when `ABS(x-y) > 1e-9 * GREATEST(1, ABS(x), ABS(y))`. | NULL transitions are reported separately, never as numeric differences. |
| Privacy | Release only pre-specified aggregate outputs. Suppress a complete related partition when any non-zero cell has 1–10 stays or 1–10 distinct patients, and assess complements against published totals. | Do not expose identifiers, raw text, or small-cell complements. |

Frozen sources and the audit boundary are: `sql/07_feature_labs.sql:9-95`, `sql/02_creatinine_long.sql:11-30`, `sql/04_creatinine_staged.sql:3-41`, and `sql/05_cohort_outcome.sql:16-75`. The timing contract retains sample, revision, and unknown availability separately (`contracts/feature_timing_policy.v1.json:20-28`).

## A. Predictor-only sensitivity

### Scientific question and target population

This pathway asks how a mechanical revision-proxy restriction would change frozen laboratory **feature summaries**, without changing reference creatinine, KDIGO staging, outcome ascertainment, eligibility, or patient-stay selection. The primary reporting population is the frozen reconstructed final analytic cohort: stays satisfying `eligible_main_cohort = 1` and `deterministic_eligible_patient_stay_rank = 1` in `cohort_outcome_v1`. Report its stay and patient denominator before feature-level results; do not describe this as a corrected cohort.

### Comparison policies

| Policy | Exact operational rule | Held fixed |
|---|---|---|
| A0 — frozen predictor summaries | Use `sql/07_feature_labs.sql` unchanged: non-NULL results, `labResultOffset BETWEEN 0 AND 720`, frozen feature mapping/plausibility filters, then all valid rows aggregate by stay and feature. | No pre-aggregation deduplication; frozen first/last order by sample offset and `labID`. |
| A1 — revision-restricted predictor sensitivity | Apply every A0 mapping, plausibility, and sample-time condition; additionally retain a row only if `COALESCE(labResultRevisedOffset, labResultOffset) <= 720`; then use the same frozen feature aggregations. | No deduplication is introduced. The rule does not claim clinical availability. |

The A0→A1 contrast estimates the joint mechanical consequence of retaining versus excluding rows by this proxy within the frozen feature aggregation. It does **not** estimate a value-version policy because frozen `07_feature_labs.sql` aggregates all qualifying rows.

### Required aggregate metrics

For each frozen feature and overall, report separately:

- valid input rows, distinct stay-feature pairs, and distinct affected stays;
- A0 rows excluded by A1, classified as late proxy, missing revision value using the sample-offset fallback, negative revision offset, and revision proxy earlier than sample offset;
- A0/A1 feature availability: numeric in both, numeric→NULL, NULL→numeric, and NULL in both;
- changes in `first_value`, `last_value`, `min_value`, `max_value`, `mean_value`, `n_values`, and frozen-only `delta`, including tolerant numeric-change count, median absolute difference, and maximum absolute difference among comparable numeric pairs;
- changes in distinct affected stays and in stay-feature pairs. These are different units and must not be summed.

### Repeats, ties, and missingness

Repeated-row effects must be measured as a separate descriptive stratum: groups defined by stay + frozen feature + `labResultOffset` with one row, multiple rows with identical numeric values, and multiple rows with different numeric values. Report how many A0 rows excluded by A1 occur in each stratum, but do not attribute a difference to “revision” when a repeated group itself changes an aggregate.

Do not collapse duplicate records before A0 or A1. First/last retain the frozen offset/`labID` ordering; a tie remains an operational tie-break, not clinical chronology. Missing values retain the frozen non-NULL result filter; missing revision values are classified explicitly before the `COALESCE` proxy is applied.

### What A can and cannot establish

A can establish differences in mechanically generated frozen feature summaries and missingness under the stated proxy. It cannot establish first clinician visibility, whether an excluded row was unavailable at 12 hours, whether repeated rows are versions, or model-performance impact. It does not evaluate reference creatinine, staging, or future outcomes.

## B. Reference-only sensitivity

### Scientific question and target population

This pathway isolates the effect of revision-proxy restriction on the **reference creatinine** while retaining the frozen creatinine trajectory for all non-reference use. The target population is all frozen `base_stays_v1` candidate stays that enter the frozen reference-candidate evaluation. Report structural candidate stays, stays with a frozen reference, stays with an alternative reference, and their distinct-patient counts separately. Do not use only reference-available stays as the denominator for reference-loss metrics.

### Comparison policies

| Policy | Exact operational rule | Held fixed |
|---|---|---|
| B0 — frozen reference | Reproduce `02_creatinine_long.sql` candidate window and selection: creatinine name/validity filters; `GREATEST(hospitalAdmitOffset,-1440)` through `LEAST(unitDischargeOffset,4320)`; one row per stay + sample offset, ordered by descending revision proxy then descending `labID`. Select the earliest resulting offset in the frozen reference window `GREATEST(hospitalAdmitOffset,-1440)` through 360 minutes (`sql/04_creatinine_staged.sql:3-11`). | Frozen selected trajectory and all non-reference values. |
| B1 — revision-restricted reference sensitivity | Keep the same broad creatinine and reference candidate windows. For reference candidates only, restrict same-offset selection candidates to `COALESCE(labResultRevisedOffset, labResultOffset) <= 720`, retain the frozen descending revision-proxy/`labID` tie-break, then select the earliest resulting reference offset. | All non-reference trajectory rows remain B0; no future record is filtered. |

B1 intentionally does not narrow either sample-offset candidate window. It is a reference-only sensitivity, not a rewrite of `creatinine_long_v1` and not a claim that a record passing the proxy was clinically available.

### Required aggregate metrics

- structural candidate stays/patients; frozen-reference available, alternative-reference available, both, frozen-only (lost), alternative-only (gained), and neither;
- among stays with both references: changed reference offset; tolerant changed reference value; median and maximum absolute value difference; and missing-revision/proxy-fallback categories;
- same-offset candidate groups, including multi-row, value-discordant, proxy-discordant, and no alternative eligible-candidate groups;
- downstream calculations **using the frozen trajectory**: changed creatinine ratio at every frozen trajectory row, changed maximum ratio by 12 hours, and any resulting pre-landmark stage/eligibility difference, each with explicit stay-level denominator;
- reference loss, numerical change, stage change, and eligibility change as separate non-additive metrics.

### Missingness, duplicates, and ties

If no B1 candidate remains, reference availability becomes NULL/absent for the sensitivity and is never coded as a normal reference, negative outcome, or zero stage. `COALESCE` fallback cases must be counted. Same-offset multi-row groups retain the frozen tie-break after applying the candidate restriction; no chronological inference follows. An alternative-only reference should be unexpected when B1 is a subset of B0 and must be reported as a data/integrity finding rather than silently accepted.

### What B can and cannot establish

B can quantify reference availability/value and mechanically propagated ratio/stage differences under a fixed proxy. It cannot establish whether either frozen or B1 reference value was visible at 720 minutes, clinical correctness of the proxy, or effects caused by changing the pre-landmark trajectory itself.

## C. Pre-landmark trajectory sensitivity

### Scientific question and target population

This pathway isolates revisions in the selected **pre-landmark creatinine trajectory** and their mechanical consequences for 48-hour prior minimum, ratio-based staging, and pre-landmark eligibility. The target population is all frozen `base_stays_v1` candidate stays with at least one selected creatinine observation in the source-specific pre-landmark trajectory interval; report all structural candidates before this restricted analytic population.

### Comparison policies

| Policy | Exact operational rule | Held fixed |
|---|---|---|
| C0 — frozen pre-landmark trajectory | Use the frozen selected creatinine series and frozen reference. Pre-landmark assessment includes selected rows with `labResultOffset <= 720` while retaining the frozen source-specific lower bound. Stage by the frozen ratio and 48-hour prior-minimum logic. | Frozen reference, future trajectory, outcome, and patient selection. |
| C1 — revision-restricted pre-landmark trajectory sensitivity | Keep the C0 reference exactly unchanged. For selected creatinine groups whose `labResultOffset <= 720`, retain only candidates with `COALESCE(labResultRevisedOffset, labResultOffset) <= 720` before the frozen same-offset ranking. Preserve the frozen source-specific lower bound, selection tie-break, ratio, and 48-hour minimum. Rows with `labResultOffset >720` remain frozen and are not evaluated as outcome records in this pathway. | Reference is frozen expressly to separate C1 from pathway B. |

C1 can remove a selected negative-offset or zero-to-720 observation if its proxy is after 720; the lower bound is not changed. It is not a future-outcome censoring rule and must not be combined with pathway B unless a separately specified combined scenario is approved.

### Required aggregate metrics

- structural candidate stays/patients, C0/C1 trajectory-covered stays, selected creatinine rows, and selected stay-offset groups;
- frozen groups removed from C1, groups with changed selected `labID`, tolerant changed creatinine values, and no alternative candidate; report counts of missing revision/proxy fallback and negative offsets separately;
- for common staged stays: change matrix for `max_stage_by_12h` (0/1/2/3/NULL), stage-1-at-prediction transitions, and pre-landmark stage-2/3 status transitions; show NULL transitions explicitly;
- changes in per-stay 48-hour prior minimum and maximum creatinine ratio, using numeric-change count plus median and maximum absolute difference among comparable non-NULL values;
- changes in frozen pre-landmark eligibility components and `eligible_main_cohort`, but not a redefined final cohort. Report stay-level eligibility transitions separately from any later patient-level selection sensitivity.

### Missingness, duplicates, and ties

One selected record per stay + sample offset is required for both C0 and C1; duplicate selected keys are integrity failures and should be aggregate-reported. Candidate duplicates remain in the source, with the frozen revision-proxy then `labID` ordering used only as a deterministic rule. A removed trajectory row is not a negative measurement, and a lost reference is not part of C1 because reference is deliberately fixed in this isolated comparison.

### What C can and cannot establish

C can establish how proxy-restricted pre-landmark row selection mechanically changes the frozen staging inputs and eligibility components. It cannot establish first availability, whether the proxy is scientifically preferable, corrected outcome labels, or any future outcome effect. Because reference remains frozen, C does not measure the combined reference-plus-trajectory policy.

## Cross-path reporting and decision gates

### Required reporting discipline

1. Keep A, B, and C outputs in separate sections and do not add their counts. Their populations, units, and selection operations differ.
2. Label all proxy-defined effects as mechanical sensitivity findings. Report rows, stay-offset groups, stays, patients, and stay-feature pairs in separate fields.
3. Suppress complete related partitions with a small non-zero cell; do not reveal derived complements from published totals. Zero-valued technical integrity checks may be released only if consistent with the governing disclosure policy.
4. Treat NULL as a distinct state in every transition table. Do not interpret missing revision time, missing reference, missing trajectory, or missing feature as evidence of no AKI or adequate availability.
5. Freeze all future outcome records in A/B/C. Any future-series revision sensitivity is a separate O0/O1 question, not D-001 predictor availability.

### Researcher decision checklist

Before any implementation or query authorization, the researcher should explicitly approve or decline:

- the use of the sample-plus-revision-restricted proxy `COALESCE(revision, sample) <= 720` as a **mechanical sensitivity convention**, including fallback treatment of missing revisions;
- the target population for A and whether feature-summary impacts should be described only in the frozen final analytic cohort or additionally in a broader candidate population;
- B1 reference-only isolation, including the unchanged broad reference candidate window and how reference loss will be presented;
- C1 frozen-reference isolation, the retained negative-offset lower bound, and whether any later combined B+C scenario is scientifically justified;
- pre-specified aggregate outputs, small-cell suppression/reconstruction review, and handling of unexpected alternative-only references or selected-key duplicates;
- whether any subsequent analysis is intended solely as a frozen-reconstruction sensitivity or as evidence toward a clinically deployable 12-hour rule.

No choice in this document approves a D-001 policy. The 191, 8,074, and 8,375 historical findings retain their recorded but non-interchangeable units and provenance limitations (`coordination/paper1_d001_static_timing_field_semantics_audit.md:41-49`).
