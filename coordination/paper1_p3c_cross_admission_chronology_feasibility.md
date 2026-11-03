# Paper 1 P3-C cross-admission chronology feasibility

**Scope:** Local schema/documentation and frozen-SQL inspection only. No remote schema lookup, BigQuery operation, or data inspection occurred. D-001–D-006 remain OPEN.

## Local evidence reviewed

- `sql/01_base_stays.sql`
- `contracts/reference_preflight_spec.v1.json`
- `sql/05_cohort_outcome.sql`
- `coordination/paper1_d005_p3a_p3c_rule_specification.md`

## Candidate fields

| Field | Locally supported meaning | Time frame | Can order distinct hospital admissions for one `uniquePID`? | Available without post-landmark outcome information? |
|---|---|---|---|---|
| `uniquePID` | Patient identifier | None | No; identifier only | Yes, but not temporal |
| `patientHealthSystemStayID` | Hospital-stay grouping identifier | None documented locally | No; numerical/lexical order is not chronology | Yes, but not temporal |
| `patientUnitStayID` | ICU-unit-stay identifier | None documented locally | No; identifier only | Yes, but not temporal |
| `unitVisitNumber` | Used by frozen SQL to rank units within `patientHealthSystemStayID` | Within-hospital-stay ordering convention only | No; no cross-admission meaning and local documentation does not independently verify chronology | Not an outcome field; landmark-time availability is not established locally |
| `hospitalAdmitOffset` | Offset from ICU-unit admission to hospital admission | ICU-relative/admission-relative | No; each value has a different ICU-unit origin and no absolute common origin | Yes as an admission-history offset, but not a cross-admission timestamp |
| `unitDischargeOffset` | Offset from ICU-unit admission to unit discharge | ICU-relative exit time | No; different ICU-unit origins and post-landmark exit information | No for a strict 12-hour index rule |
| Unit/hospital discharge status | Exit condition labels retained by frozen base SQL | Exit-status, not a timestamp | No | No for a strict 12-hour index rule |

No locally versioned schema contract or frozen SQL reference contains an absolute admission datetime, a patient-relative timestamp spanning hospital admissions, or a documented admission sequence number across `patientHealthSystemStayID` values.

## Feasibility conclusion

The preferred P3-C rule—chronologically first pre-landmark-eligible ICU stay across all hospital admissions of one patient—is **not implementable from the locally documented frozen source fields**. In particular:

1. `hospitalAdmitOffset` cannot compare separate admissions because its zero point is each ICU unit admission.
2. `patientHealthSystemStayID` and `patientUnitStayID` are identifiers, not documented temporal values.
3. The frozen order `patientHealthSystemStayID, patientUnitStayID` is deterministic but cannot be represented as chronological.
4. `unitVisitNumber` can support the existing within-hospital-stay ordering convention only; its source semantics and availability at the landmark require independent confirmation before an operational claim.

This is a documentation/schema limitation, not evidence that chronological ordering is impossible in another eICU-derived source. A future chronology policy requires a documented source field and a separate scientific review before implementation.

## Explicit nonchronological technical sensitivity

If a robustness comparison is authorized before such a field is found, the only defensible local fallback is an **identifier-order technical sensitivity**, explicitly not a chronological or deployable index policy:

1. Form the approved P3-C pre-landmark candidate set without `eligible_main_cohort`, outcome label, observation class, future measurements, discharge status, or post-landmark RRT.
2. Within each `patientHealthSystemStayID`, order qualifying units by `COALESCE(unitVisitNumber, 999999)`, then `patientUnitStayID`.
3. Across distinct hospital admissions, order by `patientHealthSystemStayID`, then the selected `patientUnitStayID`.
4. Label all outputs `identifier_order_technical_sensitivity`; do not describe them as first chronological admission, first ICU stay, or prospective deployment selection.

It can quantify sensitivity to the frozen eligibility-first ranking, but cannot resolve outcome-independent chronological selection. Any disagreement with frozen selection remains a methodological warning requiring researcher review, with no invented numerical threshold.

## Remaining decisions

- Identify a documented cross-admission chronology field, if one exists in an approved source.
- Decide whether the technical fallback is useful enough to run and how it will be described.
- Decide whether the full-table `n_hospitals_for_patient = 1` restriction is retained in a nonoperational retrospective comparison; it is not a strict landmark-time variable.
- Confirm whether `unitVisitNumber` is acceptable for within-admission ordering after source-semantic verification.
