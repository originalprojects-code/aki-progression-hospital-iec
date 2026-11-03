# Paper 1 O0/O1 future-revision sensitivity evidence freeze

**TECHNICAL EVIDENCE CONSOLIDATED — SCIENTIFIC POLICY NOT APPROVED**

## Scope

This records a frozen-rule, aggregate-only sensitivity analysis of future creatinine selection. O0 uses the frozen series. O1 changes only future sample-offset groups: it retains candidates whose revision-time proxy is at or before `LEAST(unitDischargeOffset, 4320)`. Reference creatinine and pre-landmark observations remain frozen.

The analysis does not establish first clinical availability, does not select a preferred primary policy, and does not approve any of `D-001` through `D-006`. It does not assess model fitting, model performance, or historical model-performance reproduction. All results are aggregate-only; this document contains no patient, stay, or hospital identifiers.

## Repository and artifact identity

- Branch: `develop/paper1-rebuild`
- Commit: `a83d872f92ef75e49d3693871b9d1369f2b53db8`
- Frozen outcome source: `sql/05_cohort_outcome.sql`

| Artifact | SHA-256 | Role |
|---|---|---|
| `sql/audits/paper1_o0_o1_creatinine_staging.sql` | `C5564A967060BB8257BB6E5F644BCD43D0A2F86A614918A7EC97023F06FB26EF` | O0/O1 selection and staging source |
| `sql/audits/paper1_o0_o1_future_revision_outcome_qc.sql` | `18AA99CCF7AA375737DAAD51DF16CD77135B36BA3EF36DDFE72652EC38E45516` | Outcome-propagation QC artifact |
| Rendered outcome QC | `A8C1C79CFD0B448632E34297130A433C098517DB810B1D7CE7D138FC0EF87343` | Submitted outcome QC SQL |
| `sql/audits/paper1_o0_o1_paired_cohort_stability_qc.sql` | `F4EB3F68F4243088E3616D3FD5004BC89BE5D4C8D3220E226F731A0535A6119B` | Paired stability QC artifact |
| Rendered paired QC | `541EA997334D0BA7148F94F8784BA581CFA450D83012408CB069A83764E745CE` | Submitted paired QC SQL |
| `sql/05_cohort_outcome.sql` | `4EBBB96F4EB906E5E5657AF7DD377E13965C66D5E5FEFFF39E1091D3FD8D9E63` | Frozen outcome, observation, eligibility, and ranking logic |

Scenario isolation adds `scenario` to the frozen `uniquePID` ranking partition. The frozen order remains `eligible_main_cohort DESC, patientHealthSystemStayID, patientUnitStayID`.

## Verified BigQuery evidence

All jobs were read-only aggregate queries in `mimic-ai-project`, location `US`, with no server error.

| QC | Job ID | Rendered SQL SHA-256 | Processed bytes | Billed bytes | State |
|---|---|---|---:|---:|---|
| O0/O1 staging | `f2f69d5d-2e52-4969-bced-29a4cde1f4bb` | `681CA346A9621367C01217A991F483F720362DC96583D98427E60326AA827801` | 1,952,778,007 | 1,953,497,088 | DONE |
| Outcome propagation | `68b9acd8-5a3c-48a2-a499-86e0299bedc5` | `A8C1C79CFD0B448632E34297130A433C098517DB810B1D7CE7D138FC0EF87343` | 1,959,092,562 | 1,959,788,544 | DONE |
| Paired stability | `11227ffc-ff23-4f03-bbdc-d71000c3786a` | `541EA997334D0BA7148F94F8784BA581CFA450D83012408CB069A83764E745CE` | 1,959,092,562 | 1,959,788,544 | DONE |

Each execution had a guarded dry run, a 5,000,000,000-byte cap, and disabled query cache. The paired-QC result schema was only `metric_group`, `scenario`, `unit`, `metric_name`, and `metric_value`.

## Verified aggregate results

### Structural population and staging

The common structural-candidate universe was 144,926 stays, 126,324 patients, and 208 hospitals. Both scenarios staged 94,093 stays (64.93%); 50,833 stays had no staging rows (35.07%).

### Future creatinine selection

O0 retained 174,352 future creatinine rows and O1 retained 173,031: a reduction of 1,321 rows (0.76% of O0 future rows). This is a row-selection finding, not a measure of clinical result availability.

### Primary outcome and eligibility

Primary creatinine outcome results are separate from the strict-RRT composite.

| Metric | O0 | O1 | Difference |
|---|---:|---:|---:|
| Primary positive stays | 5,233 | 5,207 | -26 |
| Primary negative stays | 62,717 | 62,209 | -508 |
| Primary NULL/indeterminate stays | 76,976 | 77,510 | +534 |
| Eligible main-cohort stays | 64,680 | 64,167 | -513 |
| Final selected stays/patients | 59,613 | 59,169 | -444 |
| Final selected primary positives | 3,060 | 3,046 | -14 |
| Final selected primary negatives | 56,553 | 56,123 | -430 |

Among all 144,926 structural-candidate stays, primary outcome transitions were 517 `0 -> NULL` (0.36%), 9 `1 -> 0` (0.006%), and 17 `1 -> NULL` (0.012%): 543 total (0.37%). The separate strict-RRT composite had 542 transitions; this need not equal 543 because its outcome definition and NULL transitions differ.

### Paired patient and selected-stay stability

Patient-level final membership in the 126,324-patient structural universe was: 444 O0-only, 0 O1-only, 59,169 both, and 66,711 neither. Among patients selected in both scenarios, 59,134 retained the same selected stay and 35 switched selected stays. All 35 switches were within the same hospital; none switched hospitals.

Stay-level membership over 144,926 structural candidates was 479 O0-only, 35 O1-only, 59,134 both, and 85,278 neither. Thus, the 35 O1-only stays are selected-stay substitutions for the same 35 patients, not new patient entries.

### Precursor/outcome overlap

There were 26 O0-present/O1-absent first future stage-2/3 events and 26 primary outcome transitions `1 -> 0` or `1 -> NULL`. Paired stay-key QC directly verified intersection 26, precursor-only 0, and outcome-transition-only 0. This establishes overlap for these frozen-rule scenarios, not clinical availability of a value.

### Hospital stability

Among 208 structural-candidate hospitals, 104 had reduced final membership, 104 were unchanged, and none increased. One hospital left the final cohort; none entered. Final-membership deltas had approximate quartiles -3, -1, and 0, with range -29 to 0. Eleven hospitals had reduced final-positive counts; none increased; the positive-count delta ranged from -2 to 0.

## Arithmetic and identity QC

The following checks passed:

- NULL `uniquePID` stays: 0; NULL hospitalID stays: 0.
- Candidate stays equalled distinct candidate stays: 144,926.
- Each scenario had zero patients with more than one selected stay.
- Patient membership cells sum to 126,324; stay membership cells sum to 144,926.
- Outcome-by-membership cells reproduce 517 `0 -> NULL`, 9 `1 -> 0`, and 17 `1 -> NULL` transitions, plus membership margins 479, 35, 59,134, and 85,278.
- Precursor/outcome margins are both 26 and their direct intersection is 26.
- Hospital delta categories sum to 208.

## Interpretation and limitations

O1 is a mechanical future-series revision-censor sensitivity scenario within the frozen outcome chain. It quantifies dependence of frozen-rule labels, eligibility, and final selection on that proxy. It does not show that O1 is clinically superior, leakage-free, or appropriate as a primary analysis.

`labResultRevisedOffset` is not established as first clinical availability; `D-001` remains open. The analysis preserves, rather than resolves, frozen discharge censoring, early death, follow-up adequacy, and indeterminate-outcome rules; `D-005` remains open. Excluding indeterminate outcomes can affect the selected population and may cause selection bias. No statistical significance, model-performance effect, or original-performance reproduction is asserted. There is no verified evidence that this sensitivity analysis was specified before results were observed.

## Reproducibility instructions

1. Use the stated branch and commit, preserving user-owned uncommitted work.
2. Hash the named source and QC artifacts against this record.
3. Render by replacing `{{PROJECT_ID}}` with `mimic-ai-project` and `{{DATASET_ID}}` with `aki_paper1_rebuild_reference_2026`, then hash the result.
4. Verify an existing job by project, location, job ID, and query-text SHA-256 before reading aggregate results.
5. Do not resubmit after local result-retrieval failure; recover only the identified job's metadata/results after hash verification.
6. Any new execution needs separate approval and `BigQueryExecutionGuard`, with the fixed 5,000,000,000-byte cap and cache disabled.

## D-005 scientific handoff

Researcher review must define the target AKI outcome estimand and decide:

1. Whether death before sufficient surveillance is indeterminate, a competing event, or part of another estimand.
2. What evidence is sufficient to classify a negative AKI outcome after early alive discharge, including the frozen 1,440-minute recent-creatinine condition.
3. Whether `(720, LEAST(unitDischargeOffset, 4320)]` and the 48--72-hour observation condition match the intended clinical question.
4. How indeterminate outcomes affect eligibility, descriptive reporting, and selection-bias assessment.
5. Whether strict-RRT composite outcomes remain secondary and separate from the primary creatinine-defined outcome.

## Handoff recommendation

Technical evidence collection for O0/O1 is complete. Proceed to researcher-led D-005 review before corrected-cohort implementation, revised outcome policy, feature generation, or model experiments. Keep `D-001` through `D-006` open pending explicit researcher approval.
