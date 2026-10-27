# Paper 1 reference SQL preflight

Task 3B adds a local-only preflight, not an execution command. Run it with an untracked configuration file:

```powershell
python -m aki_rebuild.preflight --config config/rebuild.toml --repository . --frozen-sql sql --reference-sql sql/rebuild/reference
```

It validates identifiers, requires a dedicated destination dataset beginning `aki_paper1_rebuild_`, and rejects `aki_jcmc_v2` case-insensitively. It renders the five statements and prints a JSON report with configuration, rendered SQL SHA-256 values, dependency/destination checks, source table and column contract, and semantic-equivalence outcomes. It does not instantiate a BigQuery client, submit a dry run, or execute the `CREATE OR REPLACE TABLE` statements present in rendered SQL.

Equivalence is checked against frozen `sql/01_base_stays.sql` through `sql/05_cohort_outcome.sql` after only identifier parameterization and comment removal. The sole declared technical exception is `03_renal_flags.sql`: the frozen file contains literal ASCII backspace bytes (`0x08`), which the reference file represents as `CHR(8)` inside the same regular-expression strings. It is not converted to a regex word boundary.

The local preflight reviews fixed BigQuery Standard SQL constructs and records expected eICU source tables/columns, but it cannot validate remote table schemas, permissions, Standard SQL parsing, or bytes processed. Those remain remote preflight steps.

For a future explicitly authorized remote dry run, construct the existing `BigQueryExecutionGuard` with a real client and call `optional_guarded_reference_dry_run(..., explicit_remote_approval=True)`. That function calls `guard.estimate` only; it does not call `guard.run`, so it cannot submit an execution job. Each estimate retains the fixed 5,000,000,000-byte cap.
