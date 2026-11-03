# Paper 1 D-005 P3-A / P3-C aggregate comparison: static review

**Status:** READY FOR GUARDED DRY-RUN, subject to the pre-execution gates below. This is static preparation only; no BigQuery request or execution occurred. D-001–D-006 remain OPEN.

## Artifact identity

| Item | Value |
|---|---|
| SQL artifact | `sql/audits/paper1_d005_p3a_p3c_aggregate_comparison.sql` |
| Source SHA-256 | `C2C1494C04DDC38585AD1992CD6BEF646DE7319F35F310D3B304CEE2AB588FA9` |
| Render parameters used only for hash verification | `mimic-ai-project` / `aki_paper1_rebuild_reference_2026` |
| Rendered SHA-256 | `4371C57CACBDFA01819839C82C9B9F202B02207ED7D10C31FB1F1D280289F43C` |
| Final output | Aggregate section/unit/category/count/status rows only |

## Scientific traceability and separation

### P3-A

`E_frozen_reconstruction` applies the approved Option A comparator definition: frozen reference creatinine, frozen baseline-stage logic, no strict chronic dialysis/ESRD, and no early strict RRT. It is explicitly a retrospective frozen-reconstruction variable, is not availability-confirmed information at 720 minutes, and does not resolve D-001.

P3-A surveillance eligibility is outcome-status independent: it requires either the frozen 48–72-hour selected-creatinine pathway for valid ≥72-hour ICU stays, or the frozen recent-selected-creatinine pathway for early alive ICU exits. The alternative label is positive when the frozen staged series contains an incident stage 2–3 event in the frozen outcome window and negative otherwise. Observed positive events that fail the surveillance rule are counted as P3-A exclusions, not relabelled or deleted from the comparison universe.

P3-A reports stay membership, **any-stay** patient membership, label agreement among common stay members, and observed-positive surveillance effects. The any-stay patient partition means that a patient has at least one frozen member and/or at least one P3-A member; it is neither same-stay membership nor P3-C index-selected patient membership. The common P3-A universe is all non-null patients with at least one `E_frozen_reconstruction` stay. This is a frozen-restricted comparator universe; it is not an all-patient operational universe.

Observed-positive effects are reported at two distinct grains. Stay rows are retained/excluded under P3-A. Patient rows are distinct `uniquePID` values classified as retained-only, excluded-only, or both-retained-and-excluded; no patient with positive stays in both statuses is counted twice. Common-stay label agreement includes explicit frozen `NULL` and unexpected-label categories. QC reports source-row count, partition-row count, their difference, and frozen-NULL/unexpected counts; a nonzero source-minus-partition difference is a reconciliation failure.

### P3-C, isolated matched ranking

The matched section holds the frozen `n_hospitals_for_patient = 1` restriction and `E_frozen_reconstruction` eligibility fixed. It compares the frozen selected stay (`eligible_main_cohort = 1` and frozen deterministic rank = 1) with `identifier_order_technical_sensitivity`, ordered by `patientHealthSystemStayID`, then `COALESCE(unitVisitNumber, 999999)`, then `patientUnitStayID`.

This is nonchronological identifier order, not first chronological admission, not prospective 12-hour indexing, and not deployment logic.

### P3-C, separate cross-hospital restriction effect

The broad section uses only `base_stays_v1` landmark candidates and compares the same identifier ordering with and without `n_hospitals_for_patient = 1`. It does **not** apply `E_frozen_reconstruction`, P3-A surveillance eligibility, or outcome labels outside the frozen-restricted population because frozen staged and outcome sources were created only for that restriction. Thus it isolates the administrative cross-hospital restriction effect and is not combined with the matched ranking effect into a single estimate.

Consequently, the requested broad common patient universe is represented in this artifact only for the P3-C administrative restriction comparison. A broad P3-A `E_frozen_reconstruction` universe cannot be formed from frozen derived sources without rebuilding creatinine/staging for cross-hospital patients, which this audit is not authorized to do. This is a scope limitation, not an unreported default or a claim that cross-hospital patients are ineligible.

## Privacy and integrity safeguards

- No patient, stay, hospital, raw laboratory, or row-level result is in the final SELECT.
- Each categorical partition has an explicit zero-cell scaffold.
- A complete partition is released only when every nonzero category is at least 11. Zero categories are retained only when the complete partition is released.
- If any category is 1–10, the entire partition returns one suppression status with no counts, avoiding reconstruction from the total and remaining cells.
- Technical QC reports zero or counts ≥11; values 1–10 are suppressed.
- Singleton base/outcome keys and missing outcome linkage are QC outputs; no duplicate row is selected arbitrarily.

## Local static checks

| Check | Result |
|---|---|
| Rendered placeholders | PASS — none remain |
| DDL/DML/export/call statement at line start | PASS — none |
| Invalid `STRUCT(*)` form | PASS — none |
| Frozen sources only | PASS — `base_stays_v1` and `cohort_outcome_v1` |
| Source-field traceability | PASS — fields are emitted by frozen `01_base_stays.sql` and `05_cohort_outcome.sql` |
| P3-A event-status-independent eligibility | PASS — incident event is not referenced in the surveillance predicate |
| P3-A patient grain | PASS — section is explicitly any-stay; P3-C index-selected membership is separate |
| P3-A observed-positive patient grain | PASS — grouped by distinct `uniquePID`, with a both-status category |
| P3-A NULL-label reconciliation | PASS — explicit categories and source/partition QC are present |
| P3-C effect separation | PASS — matched and cross-hospital sections use separate partitions |
| BigQuery parser/schema/cost validation | NOT PERFORMED |

## Pre-execution gates

Before any dry run, verify both hashes above, render only with the stated project/dataset identifiers, and confirm Standard SQL plus read-only final output. A separately authorized guarded dry run must use `use_query_cache=False` and `maximum_bytes_billed=5,000,000,000`. No actual execution may follow without another explicit authorization.

## Remaining limitations

The artifact cannot establish clinical availability of frozen creatinine, completeness of AKI surveillance, causal hospital effects, or chronological cross-admission ordering. `identifier_order_technical_sensitivity` remains a limited robustness comparison. A material disagreement requires researcher review, with no numerical materiality threshold embedded in this SQL.
