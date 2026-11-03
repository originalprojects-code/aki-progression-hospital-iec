# Paper 1 D-005 minimal observability-gap QC: guarded dry-run evidence

**Date:** 2026-11-03
**Authorization scope:** Dry run only. No query execution was authorized or performed.
**Decision status:** D-001–D-006, including D-005, remain open.

## Verified artifact identity

| Item | SHA-256 |
|---|---|
| Source: `sql/audits/paper1_d005_minimal_observability_gap_qc.sql` | `E7FD77BDB734A96CF3516FBF18673C7BFBD817BDAC104CCBCEC43E6021EC7FD0` |
| Rendered with `mimic-ai-project` / `aki_paper1_rebuild_reference_2026` | `7DBC284AD836FFF53960AF6AE2AAC65055A9DE886B86A68876991E69F7A0888C` |

Both hashes matched the researcher-authorized values before the request.

## Guard configuration and outcome

| Field | Value |
|---|---|
| Interface used | `BigQueryExecutionGuard.estimate()` only |
| Project / location | `mimic-ai-project` / `US` |
| SQL dialect | BigQuery Standard SQL default (`use_legacy_sql` unset; no legacy-SQL directive) |
| `dry_run` | `true` |
| `use_query_cache` | `false` |
| `maximum_bytes_billed` | `5,000,000,000` bytes |
| Estimated bytes processed | `21,876,635` bytes (`0.0204` GiB) |
| Cap check | PASS — estimate is below the 5 GB cap |
| Parser/schema status | PASS — BigQuery accepted the dry run; no server error returned |
| Dry-run object location / state | `US` / `DONE` |
| Dry-run job ID | Not returned by the client dry-run object |
| Result retrieval | Not requested; no result rows read |
| Destination table | None requested or created |
| Actual execution | **0** |

The guard configuration was checked after submission and confirmed `dry_run=True`, `use_query_cache=False`, and `maximum_bytes_billed=5,000,000,000`. `BigQueryExecutionGuard.run()` was not called.

## Boundary

This dry run validates parse/schema resolution and an estimated scan cost for the exact rendered text above. It does not establish the scientific sufficiency of creatinine measurement, alter frozen cohort/outcome definitions, release aggregate values, or approve D-005.

**D-005 MINIMAL AUDIT DRY-RUN COMPLETE — NO QUERY EXECUTION AUTHORIZED.**
