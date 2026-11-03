# Paper 1 D-005 P3-A / P3-C rule specification

**Status:** Static, implementation-ready proposal for researcher approval. It authorizes no SQL execution, cohort change, model fitting, or decision-register update. D-001–D-006 remain OPEN.

## Shared definitions

- **Landmark:** 720 minutes after ICU admission.
- **Future outcome window:** `(720, min(unitDischargeOffset, 4320)]` minutes.
- **Measurement source:** frozen `creatinine_long_v1` and frozen staging/outcome fields only. No raw laboratory versions, new deduplication rule, or new clinical-availability assumption is introduced.
- **Pre-outcome clinical eligibility (`E_pre`):** frozen main-eligibility requirements excluding only the post-landmark outcome-determinacy requirement: reference creatinine present; no strict chronic dialysis/ESRD; `COALESCE(max_stage_by_12h, 0) < 2`; and no strict acute-RRT offset `<=720`. This definition is a proposal to isolate the surveillance component and remains subject to D-001 and researcher review.
- **Strict-RRT composite:** remains separate from the primary creatinine-defined outcome in both checks.

## P3-A — event-status-independent observability

### Preferred alternative surveillance rule

For every stay in `E_pre`, define `S_A = 1` if and only if one of the following is true, without using incident KDIGO stage, the frozen outcome label, or any other future event status:

1. `unitDischargeOffset >= 4320` **and** at least one frozen-selected creatinine has `2880 < labResultOffset <= 4320`; or
2. `720 < unitDischargeOffset < 4320`, `unit_discharge_status = 'alive'`, **and** at least one frozen-selected creatinine has `720 < labResultOffset <= unitDischargeOffset` and `labResultOffset >= unitDischargeOffset - 1440`.

`NULL`, negative, and `<=720` discharge offsets do not satisfy `S_A`. An `expired` early ICU exit does not satisfy `S_A`; this is not a claim that all such exits lack a usable outcome, but a conservative consequence of not having an exact death time or an approved terminal-event estimand.

### Labels under the alternative

Among `E_pre AND S_A = 1`:

- **Positive:** at least one frozen-staged creatinine has stage 2–3 in the frozen future outcome window.
- **Negative:** no such frozen-staged event is observed in that window.
- **Indeterminate:** not emitted within the P3-A analytic cohort. All `E_pre AND S_A != 1` stays are excluded from this alternative analytic cohort and counted separately as nonmembers, not relabeled negative.

This rule is event-status independent only at the eligibility stage. It can exclude an observed positive event when that stay lacks the same surveillance pathway required of apparent negatives—for example, an early positive event in a ≥72-hour stay without a 48–72-hour selected measurement. That exclusion is intentional for this sensitivity estimand, not an assertion that the observed event is false or that the alternative rule is clinically superior.

### Required comparison populations and outputs

All stay-level comparisons use the common `E_pre` universe before any patient-level selection. Report stays and distinct non-null patients separately.

| Metric family | Exact comparison |
|---|---|
| Eligibility membership | Frozen main analytic membership (`eligible_main_cohort = 1`) versus `E_pre AND S_A = 1`: both, frozen-only, P3-A-only, neither. |
| Observed-positive exclusions | `E_pre` stays with a frozen observed stage-2/3 event that fail `S_A`; report separately from no-event exclusions. |
| Label comparison | Among common members, frozen creatinine label versus P3-A positive/negative label; report 0→1, 1→0, stable 0, stable 1, and any frozen NULL separately. |
| Population composition | Candidate, included, excluded, positive, and negative stays/patients; do not infer clinical completeness from a measurement count. |
| Patient-level effect | Apply the approved P3-C index rule identically to frozen and P3-A stay-level membership before reporting selected-patient totals. Until P3-C is approved, patient-level P3-A membership is a dependency, not a result. |

No hospital-identifying output is needed for this check. Any later hospital-stratified summary must apply the established disclosure gate.

### P3-A remaining decisions and dependencies

1. Researcher approval of `E_pre`, including its relationship to D-001 reference-creatinine timing.
2. Researcher approval that early `expired` exits are excluded rather than handled by a terminal-event estimand.
3. Confirmation that the 48–72-hour and final-1,440-minute rules are retained exactly as surveillance proxies, not as clinically validated completeness criteria.
4. An approved P3-C index rule before patient-level P3-A results are interpreted.
5. A read-only/cohort comparison implementation using existing staged, renal-flag, and base-stay fields; model training is not required for the initial membership/label audit.

## P3-C — outcome-independent index-stay selection

### Preferred scientific policy

For each `uniquePID`, select the chronologically first ICU unit stay whose 12-hour landmark is reached, using only pre-landmark eligibility criteria and never `eligible_main_cohort`, future outcome label, observation class, future laboratory measurement, discharge status, or post-landmark RRT.

Within a single `patientHealthSystemStayID`, select the first qualifying unit using:

1. ascending `unitVisitNumber`, with `NULL` ordered last; then
2. ascending `patientUnitStayID` as the deterministic tie-breaker.

This directly handles transfers or multiple ICU units within one hospital stay. A later unit is considered only if an earlier unit in the same hospital stay did not reach its 12-hour landmark or failed the approved pre-landmark eligibility criteria.

### Cross-admission chronology limitation

Frozen `base_stays_v1` supplies `patientHealthSystemStayID`, `unitVisitNumber`, `patientUnitStayID`, and `hospitalAdmitOffset`, but it does not establish a verified chronological order across distinct hospital admissions for the same `uniquePID`. `hospitalAdmitOffset` is relative to that ICU unit and cannot order separate admissions; identifiers must not be assumed chronological.

Therefore, the preferred "chronologically first across admissions" P3-C policy is **scientifically specified but implementation-blocked** until a documented, pre-landmark cross-admission chronology field is identified and approved. The frozen fallback order (`patientHealthSystemStayID`, then `patientUnitStayID`) is deterministic but is not acceptable as a claim of chronology. It may be used only as an explicitly labelled technical sensitivity if separately approved.

The frozen `n_hospitals_for_patient = 1` restriction is also calculated from the full patient table and is not a 12-hour operational variable. The researcher must decide whether P3-C should retain it as a retrospective population restriction or remove it from the operational index-rule comparison; this choice must be fixed before execution.

### Frozen comparison

The comparator is the frozen patient-level selection:

```text
PARTITION BY uniquePID
ORDER BY eligible_main_cohort DESC, patientHealthSystemStayID, patientUnitStayID
```

Unlike P3-C, this ranking uses post-landmark outcome determinacy through `eligible_main_cohort`. The comparison must be performed on an explicitly declared common patient universe, with separate reporting for patients who have no stay selected by either policy.

### Prespecified disagreement metrics

Report aggregate counts only, separately for patients and selected stays:

1. Both policies select the same `patientUnitStayID`.
2. Both select a stay but select different `patientUnitStayID` values.
3. Frozen-only selection.
4. P3-C-only selection.
5. Neither policy selects a stay in the common patient universe.
6. Among patients with different selected stays: frozen versus P3-C selected-stay outcome class, primary creatinine label, hospital membership, and pre-landmark feature availability summaries. These are paired comparison metrics, not causal estimates.
7. Counts of patients with multiple qualifying units within a hospital stay and with multiple qualifying hospital admissions, reported separately so that unresolved cross-admission chronology is visible.

No numerical threshold is prespecified for a material difference. Researcher review is triggered by any substantive disagreement pattern that changes selected-stay outcome composition, hospital representation, pre-landmark feature availability, or the interpretation of the target population. The decision must use the full paired aggregate pattern rather than a single percentage.

### P3-C remaining decisions and dependencies

1. Identify and document an admissible cross-admission chronological field, or approve the explicitly nonchronological technical fallback and its limitation.
2. Approve the exact pre-landmark eligibility set, including whether the full-table cross-hospital restriction remains.
3. Approve the common patient universe and treatment of patients with no qualifying 12-hour stay.
4. Define the allowed pre-landmark feature-availability summary before any model comparison.
5. Implement and validate the paired membership audit before retaining the frozen primary cohort definition. A material discrepancy is a mandatory scientific-review trigger, not an automatic cohort rewrite.

## Execution boundary

This specification creates no final cohort and reports no new results. Any implementation requires separate authorization for aggregate membership/label QC, followed by a separate decision before feature generation or hospital-disjoint model fitting.
