# Paper 1 D-005 P3-C paired outcome-composition audit: static review

**Status:** READY FOR GUARDED DRY-RUN, pending separate authorization. This is a static, read-only preparation artifact; no BigQuery request or execution occurred. D-001–D-006 remain OPEN.

## Artifact identity

| Item | Value |
|---|---|
| SQL artifact | `sql/audits/paper1_d005_p3c_paired_outcome_composition.sql` |
| Source SHA-256 | `F1FD3CB4BD99CEEFB15A11AF0072486534F577A848C2F14DD7721500F2709702` |
| Render parameters used only for hash verification | `mimic-ai-project` / `aki_paper1_rebuild_reference_2026` |
| Rendered SHA-256 | `14251992E2C50C3A6765E35D8AE1C416EEDD17BB887B2AA7269A10D2094FC602` |
| Final output | Aggregate `section`, `unit`, `category`, `value`, `release_status` rows only |

## Scientific specification

The audit is restricted to the same frozen-restricted landmark population and `E_frozen_reconstruction` definition used by the executed P3-C membership comparison. It uses the frozen selected stay (`eligible_main_cohort = 1` and `deterministic_eligible_patient_stay_rank = 1`) and the same `identifier_order_technical_sensitivity` ordering: `patientHealthSystemStayID`, `COALESCE(unitVisitNumber, 999999)`, then `patientUnitStayID`.

Only patients for whom both selections exist and identify different stays enter the paired composition analysis. Each such `uniquePID` contributes one internal pair; the final output contains aggregate patient counts only. The identifier order is explicitly nonchronological. `E_frozen_reconstruction` is a retrospective frozen-reconstruction comparator, not proof that its creatinine-derived fields were clinically available at 720 minutes.

## Paired endpoints

| Endpoint | Frozen source field | Categories |
|---|---|---|
| Primary creatinine outcome ascertainment | `outcome_creatinine_stage23` | positive (`1`), negative (`0`), indeterminate (`NULL`), unexpected value |
| Observation process | `observation_class` | All six frozen CASE strings, NULL/unknown, unexpected string |
| Observed stage-2/3 event status | `incident_stage23_offset` | observed / no observed event |

The primary-outcome transition describes label/ascertainment composition; the observed-event transition is reported separately. They must not be conflated. The audit neither recalculates KDIGO nor changes outcome, discharge-censoring, observation-class, or selection rules.

## Reconciliation and integrity QC

The SQL derives its `different_stay_pairs` directly from the replicated P3-C pair classification rather than hardcoding the previously observed count. It reports the pair count, paired-detail count, their difference, both patient-set differences, selected/pair duplicate-`uniquePID` groups, singleton-key failures, and explicit frozen/technical selected-stay key matches. Missing clinical outcome or observation fields are retained as analytic categories and are not used as JOIN-failure proxies.

Primary-label/event QC is NULL-safe. A positive label requires an observed event; a negative label and an indeterminate NULL label are each valid only when no observed event is present. Thus an observed event paired with a NULL or negative label is reported as a contradiction, while a valid indeterminate outcome without an observed event is not. Any nonzero integrity violation, including a suppressed small technical QC value, requires review and is not a pass.

## Privacy design

All transitions are defined with complete zero-cell scaffolds. A single shared gate covers primary-outcome, observation-class, and observed-event transition partitions: if any nonzero cell in any of these related detailed partitions is 1–10, all three detailed partitions are suppressed. This prevents reconstruction through totals or cross-tabulation of related released partitions. Technical QC values release only when zero or at least 11; values 1–10 are suppressed. No identifiers, hospital labels, raw laboratories, or row-level selected stays appear in the final SELECT.

## Static validation

| Check | Result |
|---|---|
| Frozen sources only | PASS — `base_stays_v1` and `cohort_outcome_v1` |
| Frozen selection predicate and ordering | PASS — copied from the existing approved P3-C aggregate audit |
| `E_frozen_reconstruction` predicate | PASS — reference, baseline-stage, chronic dialysis/ESRD, and early strict-RRT predicates preserved |
| Primary outcome / observation fields | PASS — read directly from frozen `cohort_outcome_v1`; no recomputation |
| Different-stay pairing grain | PASS — one internal pair per `uniquePID`, with duplicate and set-equivalence QC |
| Selected-stay JOIN integrity | PASS — frozen and technical selected-stay keys are checked independently; clinical-field NULLs are not JOIN proxies |
| NULL and unknown categories | PASS — explicit for primary outcome and observation class |
| Primary-label/event contradiction QC | PASS — explicit NULL-safe valid and contradictory combinations |
| Small-cell and complementary-disclosure protection | PASS — common detailed-partition gate plus technical-QC suppression |
| DDL/DML/export/call statements | PASS — none |
| BigQuery parser, schema, and cost validation | NOT PERFORMED |

## Execution boundary and limitations

Any dry-run or execution requires separate authorization and must use the existing `BigQueryExecutionGuard`, `use_query_cache=False`, location `US`, and the 5,000,000,000-byte cap. This proposed audit cannot establish clinical laboratory availability, prospective index-stay chronology, causal effects of selection, or a preferred D-005 policy.
