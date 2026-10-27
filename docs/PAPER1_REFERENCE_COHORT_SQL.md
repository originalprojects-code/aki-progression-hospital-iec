# Paper 1 reference cohort SQL

`sql/rebuild/reference/` is a five-stage, parameterized reference reconstruction of frozen `sql/01_base_stays.sql` through `sql/05_cohort_outcome.sql`. It is not a corrected scientific cohort and has not been executed.

## Parameters and safe rendering

The renderer accepts `source_project_id`, `source_dataset`, `destination_project_id`, `destination_dataset`, and `run_id` from `RebuildConfig`. Each is validated against a strict identifier pattern before token replacement, so values cannot add SQL syntax. BigQuery identifiers cannot be query parameters; validation plus fixed templates is the applicable safeguard.

`run_id` appears only in a SQL comment and in the manifest. Output table names remain the frozen `*_v1` names, so an authorized execution must select a dedicated destination dataset. Task 3A did not create tables or submit a query.

## Fixed order and dependencies

1. `01_base_stays.sql` → `base_stays_v1`
2. `02_creatinine_long.sql` → `creatinine_long_v1` (depends on base stays)
3. `03_renal_flags.sql` → `renal_flags_v1` (depends on base stays)
4. `04_creatinine_staged.sql` → `creatinine_staged_v1` (depends on base stays and creatinine long)
5. `05_cohort_outcome.sql` → `cohort_outcome_v1` (depends on base stays, renal flags, and creatinine staged)

The equivalent machine-readable plan is `contracts/reference_cohort_execution_plan.v1.json`. Its 59,612 patients, 3,060 positives, and 199 hospitals are audited historical comparison values only, not targets or results from this code.

## Guarding and provenance

`guarded_reference_dry_run` sends every stage to `BigQueryExecutionGuard.estimate`. Any eventual submission must use `submit_reference_plan`, which calls `BigQueryExecutionGuard.run` for every stage and therefore performs the required dry run and enforces the fixed 5,000,000,000-byte cap. No code in Task 3A instantiated a BigQuery client or called either function with a real service.

`build_reference_run_manifest` produces a non-executed manifest containing the Git commit, configuration hash, and SHA-256 for all five templates. The local test creates it in memory only.

## Differences from frozen files

The only intended changes are fixed placeholder tokens for source/destination identifiers and a provenance comment. In `03_renal_flags.sql`, `CHR(8)` is used solely to represent literal backspace bytes present in frozen regular-expression strings; this retains their effective pattern without embedding control characters in the new file. The discharge censoring rule remains `LEAST(unitDischargeOffset,4320)`. The primary eligibility flag remains based on `outcome_creatinine_stage23`; the separately retained RRT composite is not substituted.

## Unresolved scientific decisions

The Task 2.1 decision register remains controlling: laboratory availability and revision interpretation, history documentation timing, respiratory event/documentation timing, infusion/treatment timestamp semantics, discharge/outcome-observation policy for corrected science, and source-specific negative offset treatment. This reference reconstruction does not resolve or approve any of them.
