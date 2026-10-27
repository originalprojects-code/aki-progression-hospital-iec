# Paper 1 reference reconstruction audit

## Scope and status

This report documents a five-stage, frozen-equivalent reference cohort reconstruction in `mimic-ai-project.aki_paper1_rebuild_reference_2026` and a read-only investigation of its one-stay difference from `mimic-ai-project.aki_p1_audit_2026`.

It is a provenance and reproducibility record, not a corrected scientific cohort, feature-matrix reconstruction, model reproduction, or manuscript-reproduction claim. No patient identifiers, stay identifiers, raw clinical text, or patient-level rows are included.

- Repository: `originalprojects-code/aki-progression-hospital-iec`
- Branch: `develop/paper1-rebuild`
- Code commit at documentation time: `8048d52541ecd734ba20d287d50bd50aef0276c3`
- Source: `physionet-data.eicu_crd`
- Reference destination: `mimic-ai-project.aki_paper1_rebuild_reference_2026` (`US`)
- Guard for every recorded BigQuery query: `maximum_bytes_billed=5,000,000,000`, `use_query_cache=False`
- Reference-table expiration policy: 60 days; recorded table expirations are 26 December 2026.

Related local specifications are [reference cohort SQL](PAPER1_REFERENCE_COHORT_SQL.md), [reference preflight](PAPER1_REFERENCE_PREFLIGHT.md), [scientific data contracts](PAPER1_SCIENTIFIC_DATA_CONTRACTS.md), [execution plan](../contracts/reference_cohort_execution_plan.v1.json), and [preflight specification](../contracts/reference_preflight_spec.v1.json).

## SQL provenance and hash scope

The hashes in the following table are SHA-256 values of the **rendered SQL submitted to BigQuery**, not hashes of the unrendered template files. Rendering substitutes validated source/destination identifiers and a stage-specific `run_id`; the latter appears in a SQL provenance comment. Template-file hashes are therefore intentionally different and must not be compared to execution hashes as though they had the same scope.

Local rendering verification reproduced all five recorded execution hashes exactly. No hash mismatch was found. Frozen/reference semantic equivalence was established by local SQL rendering and preflight checks; it does not establish that the historical audit used an identical upstream eICU source snapshot or extraction environment.

| Stage | Reference SQL path | Destination table | Rows | Rendered SQL SHA-256 |
|---|---|---|---:|---|
| 01 | `sql/rebuild/reference/01_base_stays.sql` | `base_stays_v1` | 172,392 | `8ac1dccc9c570cdc115a18c030fd563a1d3daaa110ae3228cbcba31ba3b4e2cd` |
| 02 | `sql/rebuild/reference/02_creatinine_long.sql` | `creatinine_long_v1` | 433,284 | `37d457062b6b59a2c08868b625d77399c64862455f3d0d274f00d1a8f0af760b` |
| 03 | `sql/rebuild/reference/03_renal_flags.sql` | `renal_flags_v1` | 144,926 | `43b84698aecca45284ec093e4f3a0739daae6e7e2faa36ad4340c34de5646f6a` |
| 04 | `sql/rebuild/reference/04_creatinine_staged.sql` | `creatinine_staged_v1` | 348,026 | `30662c809c8699faadef7549b92ae341e98dfebb95cd200ab635d2fd8f54ec0c` |
| 05 | `sql/rebuild/reference/05_cohort_outcome.sql` | `cohort_outcome_v1` | 144,926 | `dd478796b8ca1b38b69ae66ffbe9ba364f20d185f59249cf3aa51173cfd66a14` |

## Five-stage execution record

Every stage received a fresh dry run through `BigQueryExecutionGuard.estimate` before its guarded execution through `BigQueryExecutionGuard.run`.

| Stage | Execution job ID | Fresh dry-run estimate | Processed / billed bytes | Table expiration (UTC) |
|---|---|---:|---:|---|
| 01 | `8f6151c6-e6ca-4fb3-a6d3-7851c6d8897e` | 15,537,619 | 15,537,619 / 15,728,640 | 2026-12-26 13:50:40 |
| 02 | `4d7f8728-21b6-4db4-aa2d-baf52fb24fdf` | 1,954,157,143 | 1,954,157,143 / 1,954,545,664 | 2026-12-26 13:53:53 |
| 03 | `0cd3eee8-4ef5-4f5a-9b5c-1824a3c10c70` | 975,411,455 | 975,411,455 / 976,224,256 | 2026-12-26 13:56:11 |
| 04 | `271c7296-12ee-40aa-8f03-ed080c817383` | 38,728,722 | 38,728,722 / 38,797,312 | 2026-12-26 13:58:02 |
| 05 | `438209eb-4345-4940-b64e-cb34fc7b854e` | 30,259,852 | 30,259,852 / 31,457,280 | 2026-12-26 13:59:58 |

## Stage-level aggregate quality control

The following summary contains only previously recorded aggregate results.

| Stage | Aggregate quality-control summary |
|---|---|
| 01: base stays | 172,392 rows and distinct stays; 130,361 patients; 208 hospitals; no null or duplicate stay IDs. |
| 02: creatinine long | 433,284 rows; 137,843 stays; 205 hospitals; no duplicate `(patientUnitStayID, labResultOffset)` groups; 8,375 selected records had `labResultOffset <= 720` and `labResultRevisedOffset > 720`; no missing revision offsets. |
| 03: renal flags | 144,926 rows and distinct stays; 126,324 patients; 208 hospitals; no null or duplicate stay IDs; 3,365 strict chronic dialysis/ESRD flags; 716 strict acute-RRT offsets at or before 720 minutes. |
| 04: creatinine staged | 348,026 rows; 94,093 stays; 204 hospitals; no null or duplicate `(patientUnitStayID, labResultOffset)` groups; 94,093 usable reference-creatinine stays among 144,926 candidates; KDIGO 0/1/2/3 measurement counts were 309,265 / 25,067 / 3,441 / 10,253. |
| 05: cohort outcome | 144,926 rows and distinct stays; 64,680 `eligible_main_cohort` rows; 59,613 final selected stays; no null or unexpected outcomes in the final selected cohort. |

## Final reference cohort

The final selection predicate was:

```sql
eligible_main_cohort = 1
AND deterministic_eligible_patient_stay_rank = 1
```

| Measure | Historical audit | Reconstructed reference |
|---|---:|---:|
| Selected stays | 59,612 | 59,613 |
| Positive outcome | 3,060 | 3,060 |
| Hospitals | 199 | 199 |
| Negative outcome | Not recorded here | 56,553 |

The reconstructed reference outcome prevalence is 5.1331% (3,060 / 59,613). The 58,491-patient figure reported in the original manuscript is not the same object as this reference reconstruction result. This work does not claim that the manuscript cohort, its model performance, or its original patient-level analysis has been reproduced.

## Cohort set comparison

The final cohorts were independently filtered with the selection predicate above and compared through `EXCEPT DISTINCT` / `INTERSECT DISTINCT` operations.

| Final-cohort set metric | Count |
|---|---:|
| Reconstructed-only stays | 1 |
| Historical-only stays | 0 |
| Common stays | 59,612 |
| Symmetric difference | 1 |

The full `cohort_outcome_v1` tables each contained 144,926 distinct stay IDs, with zero full-table stay-ID symmetric difference. Thus, direct set operations establish that the net +1 final-cohort difference is exactly one discordant stay, not a net balance of multiple discordant stays.

Read-only aggregate set-audit jobs:

| Audit query | Job ID | Processed / billed bytes |
|---|---|---:|
| Full-table stay-ID set comparison | `5ac0aeb1-440e-44ec-afac-d28e6d15d0e2` | 2,318,816 / 20,971,520 |
| Final-cohort set comparison | `681c30e5-8763-4f53-bd3a-e1b3848073e9` | 10,362,464 / 20,971,520 |
| Discordant flag comparison | `1ad82681-8a26-4d84-b0df-4d0e527db172` | 13,401,608 / 20,971,520 |
| Narrow deterministic-rank/RRT comparison | `a99ec928-1624-49b4-a897-809341f79168` | 10,178,788 / 20,971,520 |

## Single-stay strict acute-RRT discordance

### Established findings

1. The discordant stay is present in both full cohort tables and both `renal_flags_v1` tables.
2. The earliest demonstrable difference is in `renal_flags_v1`.
3. The historical audit has early strict acute RRT; the reconstructed reference has no strict acute-RRT flag.
4. Broad acute RRT and nonzero dialysis intake/output are present in both flags records; strict/broad chronic renal-support fields, broad RRT offset, and dialysis-I/O offset do not differ in the aggregate comparison.
5. In the current eICU `treatment` source, the frozen-byte-equivalent strict matcher produces 0 matches for the discordant stay.
6. The same source produces 20 broad-RRT matches.
7. There are 13 nonzero dialysis intake/output records, with 0 at or before 12 hours and 13 after 12 hours.
8. Frozen `sql/03_renal_flags.sql` contains literal ASCII backspace bytes. The reference `sql/rebuild/reference/03_renal_flags.sql` represents those bytes with `CHR(8)`; semantic equivalence was verified, and no `\b` word-boundary substitution is present.
9. The historical early strict-RRT flag makes the stay ineligible, while the reconstructed absence of that flag permits eligibility and changes the deterministic final selection.

The strict acute-RRT rule is derived from `physionet-data.eicu_crd.treatment.treatmentOffset` and `treatmentString`. The separate dialysis intake/output measure is derived from `physionet-data.eicu_crd.intakeoutput.intakeOutputOffset` and `dialysisTotal`; it does not itself create the strict RRT flag.

### What this evidence does and does not establish

**The mechanism of the one-stay cohort discrepancy is established; its historical provenance root cause remains unresolved.**

The evidence rules out the `CHR(8)` representation as the supported explanation and shows that the current source snapshot does not yield a strict match at any offset for this stay. It also does not support a deterministic ranking tie: the relevant patient has multiple full-table stays in both datasets, no dataset has multiple eligible stays for that patient, and `ROW_NUMBER` assigns one rank-one row in each table.

The following remain plausible but unproven explanations:

- a historical audit extraction or pipeline variant; or
- a different historical upstream source snapshot or record content.

Neither explanation is a confirmed root cause because historical raw-source provenance sufficient to distinguish them was not available.

| Provenance audit query | Job ID | Processed / billed bytes |
|---|---|---:|
| Final-set plus renal-flags comparison | `0cd4313b-ba8c-4d13-a1af-69a5a7ea91f7` | 14,077,672 / 41,943,040 |
| Upstream treatment plus intake/output matcher audit | `04d0a892-ad49-4dd1-aa69-ff71762aa07f` | 596,585,068 / 596,639,744 |

## Limitations and unresolved scientific work

- This is a frozen-equivalent reference reconstruction.
- A scientifically corrected cohort has not yet been produced.
- Feature matrices and model performance have not been reproduced.
- The manuscript's 58,491-patient discrepancy remains unresolved.
- Revision-time semantics and information availability at the 12-hour prediction landmark remain separate scientific decisions.
- All recorded BigQuery jobs used a 5,000,000,000-byte cap. Billing and query-cache behavior were controlled by the execution guard, but query results remain specific to the recorded source and audit-table states.
- The reference tables are subject to the project-imposed 60-day expiration policy; the recorded expiration date is 26 December 2026.

## Verification record

Local verification performed for this report:

- Re-rendered each stage with the stage-specific execution configuration and confirmed all five recorded rendered-SQL SHA-256 values.
- Confirmed semantic equivalence of frozen and reference SQL according to the documented `CHR(8)` exception.
- Confirmed the report numbers against the recorded execution and aggregate-QC results above.
- No BigQuery query, dataset/table modification, scientific SQL modification, feature generation, or model training was performed while writing this report.
