# Subsequent Stage 2-3 AKI Prediction — Hospital-Disjoint Internal–External Validation

> The 8 November 2026 submission figure scripts and reference outputs are under `code/` and `figures/submission_2026_11/`; see `docs/FIGURES_SUBMISSION_2026_11.md`. Earlier A25 materials remain available as historical snapshots.

Reproducibility materials for the manuscript:

**Machine learning for early prediction of subsequent stage 2-3 acute kidney injury in critically ill adults: hospital-disjoint internal-external validation**

Authors: Cagdas Yilmaz and Ali Akdagli

## Study summary

The primary cohort included 58,491 patients from 198 hospitals; 3,032 (5.18%) developed subsequent serum-creatinine-defined KDIGO stage 2-3 AKI after a fixed 12-hour landmark. The primary XGBoost strategy was evaluated using hospital-disjoint internal-external cross-validation.

## Repository contents

- `code/`: original source-only notebooks plus submission-stage robustness analysis scripts
- `sql/`: parameterized BigQuery SQL used to construct the analysis tables
- `protocols/`: analysis-specific model, calibration, decision-curve, TreeSHAP, comparator, and ablation specifications
- `aggregate_outputs/`: manuscript-level and fold-level aggregate results
- `checklists/`: data-privacy, reproducibility, and TRIPOD reporting checklists
- `docs/`: run order, data-access requirements, software environment, analysis scope, and reporting limits
- `figures/`: publication-oriented aggregate figures
- `manuscript/`: submission-ready manuscript snapshot and Online Resource PDF
- `release/`: file inventory, source validation, and SHA-256 manifest material

Submission-stage robustness analyses include cohort selection characterization, high-missingness ablation, explicit missingness-indicator dependence, renal-status/creatinine-trajectory comparators, exploratory subgroup performance, actionable lead-time/outcome-window sensitivity, and hospital-level discrimination/calibration heterogeneity.

## Data access

The eICU Collaborative Research Database is available through PhysioNet to credentialed users who complete the required human-subjects research training and accept the applicable Data Use Agreement. Source data and patient-level derivatives are not redistributed in this repository.

## Reproduction configuration

The project uses configurable values for the authorized execution environment, including `GOOGLE_CLOUD_PROJECT`, `AKI_DATASET_ID`, `EICU_SOURCE_DATASET`, `BIGQUERY_LOCATION`, and `AKI_OUTPUT_ROOT`. See `docs/RUN_ORDER.md`, the files under `sql/` and `protocols/`, and the source scripts under `code/` for execution details.

## Interpretation

The validation design is hospital-disjoint internal-external cross-validation and is not independent external validation. The primary outcome is serum-creatinine-defined. SHAP values are non-causal model attributions. Decision-curve analysis estimates net benefit but does not establish clinical effectiveness. Hospital-level discrimination was broadly maintained among adequately sized held-out hospitals, while calibration-in-the-large showed greater between-center heterogeneity. Independent contemporary external and prospective evaluation remain necessary before clinical implementation.

## Publication-figure reproducibility

The current submission figure scripts and reference outputs are described in `docs/FIGURES_SUBMISSION_2026_11.md`. The earlier A25 artwork can still be regenerated with `code/08_BUILD_PUBLICATION_FIGURES.py` from disclosure-safe aggregate sources.

## Version

Version `v1.2.2-submission` derives from the `v1.2.1-submission` tag.

## License

Original code and documentation are released under the MIT License. eICU data remain governed by the PhysioNet Data Use Agreement and are not covered by the MIT License.


## Submission files

The current submission manuscript and supplementary information are under `manuscript/submission_2026_11/`. The manuscript refers to DOI `10.5281/zenodo.24058816` and tag `v1.2.2-submission`. The legacy `manuscript/`, `figures/`, and A25 inventories are retained as historical snapshots. The scoped `release/SHA256SUMS_2026_11.txt` covers the 37 figure and manuscript files listed there, not the entire repository.
