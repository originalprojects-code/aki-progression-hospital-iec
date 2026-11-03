# Paper 1 D-005 Audit A controlled execution evidence

**2026-11-03 — one read-only aggregate query executed after guarded dry-run.**

## Identity and safeguards

| Field | Value |
|---|---|
| Source SQL | `sql/audits/paper1_d005_a_cohort_observability_feasibility_v4.sql` |
| Source SHA-256 | `305F1DC6B264F0512CAE660A950958F498F97F122422AFC82B0F63CFD04810D9` |
| Rendered SHA-256 | `1528DF40C78F536D541F26F19ECDC0D7BE29E161D46D61EB712446E7CC55AE09` |
| Project / location | `mimic-ai-project` / `US` |
| Guard | `BigQueryExecutionGuard`; cache disabled; maximum billed bytes `5,000,000,000` |
| Fresh pre-execution estimate | 18,026,235 bytes (0.0168 GiB) |
| History check | No accessible prior job had the exact rendered SHA-256 |
| Execution job ID | `cff583cb-8b1a-46e0-9f4d-4bdbd8ced420` |
| Final state | `DONE`; no server error |
| Processed / billed bytes | 18,026,235 / 20,971,520 |
| Destination | BigQuery temporary anonymous query-result table only; no persistent destination table was requested or created |

`guard.run()` performed its own mandatory estimate after the explicit fresh estimate, then submitted the identical in-memory rendered string once. There was no retry, no query-result export, and no patient/stay/hospital identifier in the returned aggregate rows.

## Aggregate results

| Metric | Unit | Value |
|---|---:|---:|
| Base duplicate key groups | stay-key groups | 0 |
| Outcome duplicate key groups | stay-key groups | 0 |
| Base singleton keys missing any outcome key | stay keys | 27,466 |
| Outcome singleton keys missing any base key | stay keys | 0 |
| Base singleton keys excluded by structural filter | stay keys | 27,466 |

## Reconciliation and disclosure outcome

The two 27,466 counts are numerically identical: the audited base stays absent from `cohort_outcome_v1` correspond, in this query, to singleton base stays excluded by the frozen structural eligibility restriction. This is a reconciliation of the Audit A key-QC definitions, not proof that every excluded stay has the same scientific reason.

The query returned no `detail` rows. Under the SQL’s all-or-none gate, this means at least one full detailed stratum had fewer than 11 stays or fewer than 11 patients. Detailed categories were therefore withheld; no small cell can be inferred from a released detailed margin because no detailed margin was returned. The executed output does not contain the structural-candidate denominator itself, so the previously recorded 144,926-stay denominator cannot be independently re-established from this query result alone.

## Boundaries and next questions

This execution confirms source-table key cardinality at the audit’s QC grain and the operation of its suppression gate. It does not validate the clinical adequacy of frozen observation rules, establish an alternative D-005 estimand, resolve D-001 availability, or support a death-time competing-risk interpretation. Any future audit must separately authorize its exact SQL and review output privacy before execution. D-001 through D-006 remain open.

**D-005 AUDIT A EXECUTED — SCIENTIFIC REVIEW PENDING.**
