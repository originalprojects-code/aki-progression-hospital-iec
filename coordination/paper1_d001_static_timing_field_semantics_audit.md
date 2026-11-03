# Paper 1 D-001 static timing and field-semantics audit

**Status:** Evidence and decision draft only. No BigQuery operation, patient-level retrieval, SQL execution, model work, or decision-register update occurred. D-001–D-006 remain OPEN.

## Scope and terminology

This audit uses the following terms without equating them:

- **Sample-time proxy:** eligibility based on `labResultOffset` under the source-specific frozen window.
- **Sample-plus-revision-restricted proxy:** eligibility based on the sample-time rule plus a specified revision-time proxy bound.
- **Unknown first clinical availability:** the dataset does not supply a field established here as the time the first result became visible to clinicians.

`labResultOffset` and `labResultRevisedOffset` are preserved as separate fields. A late revision is not evidence that the first result was late. The contract explicitly lists the result-availability field as `null` and requires researcher approval for D-001 (`contracts/feature_timing_policy.v1.json:20-28`).

## Field-semantics and timing traceability matrix

| Claim or operational behavior | Evidence and exact repository location | What it establishes | What it does not establish |
|---|---|---|---|
| Landmark is 720 minutes; timestamp eligibility is source-specific. | `contracts/feature_timing_policy.v1.json:3,13-17`; `contracts/policy_traceability.v1.csv:2` | The contract prohibits a universal negative-offset rule. | A clinically correct lab-availability policy. |
| The laboratory contract names a sample field and revision field, but no availability field. | `contracts/feature_timing_policy.v1.json:20-28` | The current contract distinguishes `labResultOffset`, `labResultRevisedOffset`, and unknown availability. | Whether either timestamp equals first clinical availability. |
| The local preflight schema contains laboratory IDs, offsets, result, and name. | `contracts/reference_preflight_spec.v1.json:9-16` | The rebuild expects `patientUnitStayID`, `labID`, `labResultOffset`, `labResultRevisedOffset`, `labResult`, and `labName`. | Semantic definitions of those fields or ordering semantics for `labID`. |
| Frozen general laboratory predictors use a sample-offset window. | `sql/07_feature_labs.sql:9-20` | Predictors include non-NULL lab results with `labResultOffset BETWEEN 0 AND 720`; revision time is not selected in this CTE. | First-result availability, revision chronology, or one-row-per-measurement behavior. |
| Frozen predictor mapping and plausibility rules are feature-specific. | `sql/07_feature_labs.sql:21-81` | Raw names map to listed features; values outside stated feature-specific bounds are excluded. | That all repeated rows are alternate versions of one clinical result. |
| Frozen feature summaries aggregate every valid row by stay and feature. | `sql/07_feature_labs.sql:83-95` | First/last use sample offset then `labID`; min, max, mean, and count use all valid rows. | That `labID` is chronological or that the summaries are immune to repeated records. |
| Frozen creatinine-long selects one row per stay and sample offset. | `sql/02_creatinine_long.sql:11-18,28-30` | Selection groups by `(patientUnitStayID, labResultOffset)` after restricting `labName` to creatinine. Ties favor larger `labID` after descending revision proxy. | That two same-offset records are confirmed serial clinical versions, or that a selected revision was available at minute 720. |
| Frozen creatinine candidate window is source-specific and broader than predictor window. | `sql/02_creatinine_long.sql:19-26` | Creatinine candidates use `[GREATEST(hospitalAdmitOffset,-1440), LEAST(unitDischargeOffset,4320)]`, not `[0,720]`. | That a predictor policy can be copied unchanged to reference or outcome records. |
| Frozen reference creatinine is the earliest selected creatinine in its reference window. | `sql/04_creatinine_staged.sql:3-11` | Reference candidates use the selected `creatinine_long_v1` series from `GREATEST(hospitalAdmitOffset,-1440)` through 360 minutes and choose lowest offset. | Availability of that result by 720 minutes under a clinically verified clock. |
| Frozen KDIGO staging uses the selected creatinine trajectory and a 48-hour minimum. | `sql/04_creatinine_staged.sql:13-41` | Ratio, prior 48-hour minimum, and 0/1/2/3 staging all depend on selected creatinine values. | That a revision-time restriction is scientifically appropriate for every trajectory value. |
| Frozen outcome measurements are post-landmark and discharge-censored. | `sql/05_cohort_outcome.sql:16-25,36-55` | Stage-2/3 event ascertainment uses `(720, LEAST(discharge,4320)]`; negative/indeterminate rules are separate. | Pre-landmark predictor availability or first clinical availability. |
| The contracts test late revision as unknown availability and test grouping discipline. | `tests/test_scientific_contracts.py:58-84` | A synthetic late revision is classified as revision-proxy-after-landmark with availability `unknown`; selection rejects missing/incorrect grouping. | Real-data frequency, direction, or clinical meaning of duplicated rows. |
| Reference reconstruction found selected pre-landmark records with late revision offsets. | `docs/PAPER1_REFERENCE_RECONSTRUCTION_AUDIT.md:45-55` | 8,375 **selected records** had sample offset `<=720` and revision offset `>720`; no missing selected revision offsets in that reference stage. | The number of affected patients, the number of predictor rows, or first-result availability. |

### Available eICU documentation limitation

The locally available source-schema artifact lists field names only (`contracts/reference_preflight_spec.v1.json:9-16`). No locally stored official eICU documentation was found that defines `labResultOffset` as specimen collection, assay completion, result release, or first clinician visibility; likewise none establishes the clinical ordering of `labID` or that repeated rows are successive versions. These are unresolved source-semantics gaps, not negative findings about the underlying source database.

## Existing sensitivity findings: provenance, unit, denominator, and limitation

| Finding | Provenance | Verified unit and denominator statement | Limitation / ambiguity |
|---|---|---|---|
| 191 | `contracts/decision_register.v1.json:5-9`; echoed in `contracts/policy_traceability.v1.csv:4` | The register says **191 rebuilt-cohort records** lacked reference creatinine “confirmed available by 12 hours” under an audited revision-time proxy. No denominator is supplied in those sources. | The user-facing audit narrative previously called these patients, whereas the controlling JSON says records. The static evidence cannot resolve whether the unit is patients, stays, records, or reference-candidate rows. It must not be converted to a rate or combined with other counts. |
| 8,074 | `contracts/decision_register.v1.json:5-9`; echoed in `contracts/policy_traceability.v1.csv:4` | The register says excluding late revisions removed at least one physiologically valid laboratory record in **8,074 patients**. No denominator, analyte breakdown, or row count is supplied. | It is an affected-patient sensitivity count, not the number of removed records, changed feature summaries, changed cohort members, or changed predictions. |
| 8,375 | `docs/PAPER1_REFERENCE_RECONSTRUCTION_AUDIT.md:51-55` | A separate reference-reconstruction QC reports 8,375 selected creatinine **records** with sample offset `<=720` and revision offset `>720`. | It is not interchangeable with 8,074 patients or 191 records. It must not be subtracted from, added to, or used as a denominator for either prior finding. |

The 191 and 8,074 findings are therefore retained exactly as historical sensitivity evidence. They are non-additive and do not establish corrected-cohort counts, model-performance effects, or confirmed temporal leakage.

## Separate scientific uses of laboratory data

| Use | Frozen behavior | D-001 relevance | Required separation |
|---|---|---|---|
| Predictor laboratory features | Sample-time proxy: valid rows with `[0,720]`, then feature-level aggregation across rows. | Directly relevant: a value may be aggregated even when its final revision proxy is after 720. | Evaluate feature summaries, missingness, and duplicate-row effects separately; do not call a revision time first availability. |
| Reference creatinine | Broad source-specific candidate interval; same-offset selection by descending revision proxy/lab ID; earliest selected offset through 360. | Directly relevant: reference availability and value can affect eligibility and all downstream ratios. | Do not equate the predictor `[0,720]` filter with the reference window; distinguish reference-only sensitivity from full trajectory sensitivity. |
| Pre-landmark AKI staging | Uses reference plus selected trajectory; stage summary examines reference-to-720 measurements. | Relevant through both reference and pre-landmark selected values. | A change in reference can alter ratios; a trajectory change can alter prior minima. Report them separately. |
| Post-landmark outcome measurements | Uses selected trajectory in `(720, min(discharge,4320)]`. | Not a predictor-availability question. | Do not apply a `revision <=720` rule to future measurements. The completed O0/O1 work is a separate mechanical outcome-series sensitivity (`coordination/paper1_o0_o1_future_revision_evidence_freeze.md:5-9,94-96`). |

## Duplicate records and value-version ambiguity

The frozen general feature SQL does not deduplicate stay/feature/sample-offset groups before aggregation: it uses all valid rows for count, mean, min, and max, and resolves first/last ties by `labID` (`sql/07_feature_labs.sql:83-95`). Thus an exact repeated row can change counts and means, while a differing-value repeated row can also change value summaries. The code alone does not establish whether repeats are duplicate exports, corrections, separate measurements sharing an offset, or historically successive clinician-visible results.

For creatinine, the frozen selection is narrower but still operational rather than historical: it filters to creatinine, groups by stay and sample offset, and chooses the highest revision proxy then highest `labID` (`sql/02_creatinine_long.sql:15-18`). The grouping is compatible with a single analyte only because the predicate fixes `labName` to creatinine (`sql/02_creatinine_long.sql:23-24`). The contract requires a stay/analyte/sample-offset grouping key and rejects incorrect grouping in synthetic tests (`contracts/policy_traceability.v1.csv:4`; `tests/test_scientific_contracts.py:73-84`). Neither source establishes that `labID` is temporal or that selected values were clinically visible in this order.

## Researcher decision matrix

| Candidate direction | Predictor laboratory features | Reference / pre-landmark staging | Future outcome records | Leakage / selection consequence | Status |
|---|---|---|---|---|---|
| Frozen reference behavior | Sample-time proxy `[0,720]`; aggregate valid rows with no revision filter. | Frozen broad candidate window and revision-proxy selection. | Frozen trajectory and outcome logic. | May include rows whose final revision proxy is after landmark; this is not confirmed leakage because first availability is unknown. | Historical reference only; not a corrected policy. |
| Sample-time proxy primary, sample-plus-revision-restricted sensitivity | Use source-specific sample-time window as provisional primary; separately quantify a fixed revision-proxy restriction. | Keep frozen reference and staging for the primary comparison; evaluate reference-only and pre-landmark-series sensitivities separately. | Keep future outcomes frozen; do not impose `revision <=720`. | Primary retains potentially late-final revisions; sensitivity may exclude genuinely available early results and alter missingness/eligibility. | **Provisional methodological direction recommended for researcher review; not approved.** |
| Sample-plus-revision-restricted proxy primary | Require sample-time eligibility and a revision-proxy bound for predictors. | Would require separately approved reference/staging rules. | Does not justify a landmark filter on future outcomes. | Lower proxy-defined post-landmark inclusion but potentially higher false exclusion; revision proxy is not first availability. | Scientifically possible sensitivity, but not supported as primary by current evidence alone. |
| No corrected timing policy yet | Preserve frozen reconstruction only. | Preserve frozen reconstruction only. | Preserve frozen outcome policy. | Avoids an unsupported availability claim but defers corrected analysis. | Valid until researcher approval; no final science conclusion. |

## Provisional recommendation and unresolved questions

The defensible provisional direction is to retain the **sample-time proxy** as the candidate primary predictor policy because it matches frozen source-specific predictor semantics, while prespecifying a **sample-plus-revision-restricted proxy** as a sensitivity analysis. This is a methodological proposal, not a claim that sample time proves result availability, and it does not approve a reference-creatinine, pre-landmark staging, or future-outcome rule.

Researcher approval is still required for:

1. Whether the sample-time proxy is acceptable as the primary predictor eligibility convention despite unknown first availability.
2. The precise revision-proxy bound, treatment of missing revision offsets, and source-specific negative-offset behavior for the sensitivity analysis.
3. Whether reference creatinine is governed by a reference-only sensitivity or a wider pre-landmark trajectory sensitivity, and how resulting cohort changes should be reported.
4. Whether repeated same-offset rows should be summarized only as a sensitivity issue or receive a separate mechanical deduplication analysis; no clinical version sequence may be assumed.
5. Whether a future aggregate audit is justified, with prespecified units/denominators and disclosure protection, to quantify policy effects without asserting clinical availability.

Until then, `D-001` remains `requires_researcher_approval` (`contracts/decision_register.v1.json:5-9`).
