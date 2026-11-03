# Paper 1 D-005 minimal observability-gap QC: controlled execution evidence

**Date:** 2026-11-03
**Authorization scope:** One read-only aggregate execution of the verified minimal D-005 QC.
**Decision status:** D-001–D-006, including D-005, remain open.

## Identity and guarded submission

| Field | Value |
|---|---|
| Source SHA-256 | `E7FD77BDB734A96CF3516FBF18673C7BFBD817BDAC104CCBCEC43E6021EC7FD0` |
| Rendered SHA-256 | `7DBC284AD836FFF53960AF6AE2AAC65055A9DE886B86A68876991E69F7A0888C` |
| Project / location | `mimic-ai-project` / `US` |
| Fresh guarded estimate | 21,876,635 bytes |
| Guard settings | `dry_run=True`, `use_query_cache=False`, `maximum_bytes_billed=5,000,000,000` |
| Actual job ID / state | `d8bfa90e-c018-4103-9d6c-cdbb798918a4` / `DONE`, no server error |
| Created / started / ended (UTC) | 09:55:29.616 / 09:55:29.708 / 09:55:34.077 |
| Processed / billed | 21,876,635 / 31,457,280 bytes |
| Destination | Temporary anonymous query result; no persistent table |

The guard performed the required fresh estimate, then `run()` performed its own mandatory estimate before the single actual submission. No retry occurred.

Initial `job.result()` retrieval raised a client-side `TypeError` after job submission. The existing job was then recovered by exact ID, project, and location. Its stored SQL text hashed to the expected rendered SHA-256, and its existing temporary result rows were retrieved through the rows API only; no additional SQL job was submitted.

## Disclosure-safe aggregate outputs

All six indicator rows met the stay/patient numerator-and-complement gate; no clinical metric was suppressed. Percentages below are descriptive and use the displayed denominator only. Patient percentages count distinct non-null `uniquePID` values within each indicator denominator; they are not complements of stay counts.

| Metric | Denominator population | Stays | Distinct patients | Numerator stays | Numerator patients |
|---|---|---:|---:|---:|---:|
| Structural candidates | Full structural singleton candidates | 144,926 | 126,324 | 144,926 | 126,324 |
| Selected creatinine in 48–72 h, all structural | Nonambiguous selected-creatinine analysis stays | 144,926 | 126,324 | 46,544 (32.12%) | 43,145 (34.15%) |
| Selected creatinine in 48–72 h, among valid ≥72-h ICU stays | Nonambiguous selected-creatinine analysis stays | 40,153 | 37,462 | 36,231 (90.23%) | 33,985 (90.72%) |
| Recent selected creatinine before early alive ICU exit | Nonambiguous selected-creatinine analysis stays | 100,938 | 91,025 | 62,636 (62.05%) | 57,999 (63.72%) |
| Frozen early-alive negative class plus recent selected creatinine | Nonambiguous selected-creatinine analysis stays | 100,938 | 91,025 | 39,140 (38.78%) | 36,908 (40.55%) |
| Frozen early-death-without-observed-stage-2/3 class | Full structural singleton candidates | 144,926 | 126,324 | 3,317 (2.29%) | 3,317 (2.63%) |

The 39,140 frozen early-alive-negative stays and 3,317 frozen early-death indeterminate stays exactly reconcile to the previously recorded frozen stay-level counts. The 62,636 early-alive recent-creatinine count is larger by design: it is event-status independent, whereas the frozen negative class has positive events in a higher-priority branch.

## Integrity and suppression QC

All reported technical QC values were zero and therefore releasable under the artifact’s technical-QC policy:

| QC metric | Value |
|---|---:|
| Duplicate base stay-key groups | 0 |
| Duplicate outcome stay-key groups | 0 |
| Duplicate frozen-selected creatinine stay-offset groups | 0 |
| Structural stays excluded for ambiguous selected creatinine | 0 |
| Structural stays missing singleton outcome record | 0 |
| Structural stays with NULL `uniquePID` | 0 |

No hospital, patient, or stay identifier and no cross-tabulation was returned. The result schema consisted only of `section`, `metric`, `denominator_population`, `unit`, denominator/numerator stay and patient counts, `value`, and `release_status`.

## Interpretation boundary

These are frozen-source surveillance and observability descriptors. They do not establish that a creatinine measurement was clinically sufficient, that a missing measurement implies no AKI, or that ICU-exit status supplies an exact death time. This execution neither changes a scientific decision nor approves D-005.

**D-005 MINIMAL AUDIT EXECUTED — SCIENTIFIC REVIEW PENDING.**
