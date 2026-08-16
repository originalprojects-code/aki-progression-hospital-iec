# Subsequent stage 2-3 AKI prediction with hospital-disjoint internal-external validation

Reproducibility materials aligned with the A23 scientifically and linguistically locked manuscript:

**Machine learning for early prediction of subsequent stage 2-3 acute kidney injury in critically ill adults: hospital-disjoint internal-external validation**

Authors: Cagdas Yilmaz and Ali Akdagli

## Study purpose and design

The study estimates risk of a subsequent serum-creatinine-defined KDIGO stage 2-3 acute kidney injury outcome after a fixed 12-hour ICU landmark. Evaluation uses hospital-disjoint internal-external cross-validation. This is not independent external validation and does not demonstrate clinical benefit or implementation readiness.

## Public release scope

This repository contains source code, parameterized SQL, analysis specifications, disclosure-safe aggregate outputs, tables, figures, reporting checklists, and software-environment information. It includes the primary pipeline plus seven sensitivity/robustness analyses: cohort selection, high-missingness ablation, missingness-indicator dependence, renal comparators, exploratory subgroup analyses, lead-time/outcome-window sensitivity, and hospital heterogeneity.

## Data access and DUA boundaries

No patient-level eICU data, patient-level predictions, patient-level SHAP values, raw extracts, hospital identity mappings, or DUA-restricted derivatives are distributed. The eICU Collaborative Research Database must be accessed separately through PhysioNet by credentialed users who complete the required training and accept the applicable Data Use Agreement.

## Repository structure

- `code/`, `sql/`, `protocols/`: primary source pipeline and locked/specification files.
- `analyses/`: Step 1–7 public-safe source code, READMEs, environments, and aggregate outputs.
- `aggregate_outputs/` and `tables/`: public aggregate results and final supplementary-table sources.
- `figures/`: final supplementary-figure source images.
- `docs/`: run order, scope, DUA notes, software environment, and final source mapping.
- `checklists/`: privacy, reproducibility, and reporting checks.
- `release/`: inventory, hashes, and release validation.

## Reproducibility entry points

Start with `docs/RUN_ORDER.md`, `docs/DATA_ACCESS_AND_DUA.md`, `code/README.md`, `protocols/README.md`, and `docs/A23_SUPPLEMENT_SOURCE_MAP.csv`. Each Step 1–7 analysis has a public README/source directory under `analyses/`.

## Environment

See `requirements.txt` and `docs/SOFTWARE_ENVIRONMENT.md`. Runtime project, dataset, location, dependency, input, and output paths are configured through environment variables; no private local paths are required.

## Citation and version

See `CITATION.cff`. Version: `1.1.1-submission`. This patch release preserves historical `v1.0.0-manuscript` and `v1.1.0-submission` provenance while aligning current metadata and supplementary figure presentation with the final A23 manuscript framing. Scientific results are unchanged.

Original code and documentation are MIT licensed. eICU data remain under the PhysioNet DUA and are not covered by the MIT license.
