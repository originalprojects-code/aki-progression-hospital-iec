# Paper 1 D-005 Audits B/C controlled execution evidence

**2026-11-03 — one read-only aggregate execution each for B and C.**

Both audits were checked against their expected source/rendered SHA-256 values, had no matching accessible prior job, passed a fresh `BigQueryExecutionGuard.estimate()`, and were submitted once with `use_query_cache=False`, `maximum_bytes_billed=5,000,000,000`, project `mimic-ai-project`, and location `US`. `guard.run()` also performed its mandatory estimate. No retry occurred. The BigQuery destinations below are temporary anonymous result tables; no persistent table was requested or created.

## Audit B — hospital surveillance heterogeneity

| Field | Value |
|---|---|
| Source / rendered SHA-256 | `15A1DC122CD143A40600BF4D36B9C95CD798A87E5423F1E55EF8B3CDE20776A1` / `4AE548DCB2BC7EAFE06D6C6CFAB266ED2CC1171D1F6A9896A3073576CCA22989` |
| Job ID / state | `7d8c9a2c-4a8a-4319-afdd-9aae16d98cc8` / `DONE`, no server error |
| Fresh estimate | 12,402,783 bytes (0.0116 GiB) |
| Processed / billed | 12,402,783 / 20,971,520 bytes |

The unit of every distribution row is hospitals with at least 11 structural-candidate stays. There were 199 included hospitals and 9 hospitals excluded by the low-count threshold; hospital IDs were not returned. Base and outcome duplicate key-group counts were both zero.

| Frozen observation/surveillance metric | Included hospitals | Minimum rate | Median rate | Maximum rate |
|---|---:|---:|---:|---:|
| No future creatinine | 199 | 18.18% | 54.23% | 100.00% |
| Inadequate follow-up | 199 | 0.00% | 1.95% | 11.32% |
| Early death | 199 | 0.00% | 2.09% | 9.09% |
| Late negative | 199 | 0.00% | 13.39% | 44.90% |
| Early alive-discharge negative | 199 | 0.00% | 24.56% | 63.64% |
| Future creatinine available | 199 | 0.00% | 44.57% | 81.82% |

These are distributional properties of the frozen observation classes, not evidence that missing creatinine means no AKI, or that hospital-level differences are causal surveillance bias.

## Audit C — creatinine timing/frequency

| Field | Value |
|---|---|
| Source / rendered SHA-256 | `3F052AF4966C9FD0780EC401FEA85951F366AFDEA791F2E9455172330229E200` / `292F4AF587ED8CBF241D3D3C8A4B22FAE66820E3D0B336E428FC2D882B90C602` |
| Job ID / state | `e0b12f1e-82d0-471d-b78d-5be4115701c7` / `DONE`, no server error |
| Fresh estimate | 23,255,771 bytes (0.0217 GiB) |
| Processed / billed | 23,255,771 / 31,457,280 bytes |

| QC metric | Value |
|---|---:|
| Base duplicate key groups | 0 |
| Outcome duplicate key groups | 0 |
| Duplicate frozen-selected creatinine stay-offset groups | 0 |

No timing/detail rows were returned. The all-or-none Audit C disclosure gate therefore withheld detailed strata because at least one full stratum had fewer than 11 stays or fewer than 11 patients. Consequently, this execution does not quantify zero-future-measurement stays, 48–72-hour coverage, or recent-before-discharge measurement values in a disclosure-safe released form. Its QC establishes only that those metrics were not inflated by duplicate base, outcome, or frozen-selected stay-offset keys.

## Boundaries

No result rows containing patient, stay, or hospital identifiers were retrieved. Neither execution changes outcome definitions, establishes measurement sufficiency, validates clinical availability, or resolves D-001 through D-006. Audit D was not submitted.

**D-005 AUDITS B/C EXECUTED — SCIENTIFIC REVIEW PENDING.**
