# Subsequent Stage 2-3 AKI Prediction — Hospital-Disjoint Internal–External Validation

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

The A25 publication artwork is repository-rebuildable from disclosure-safe aggregate sources. `code/08_BUILD_PUBLICATION_FIGURES.py` regenerates Fig. 1–3 and Fig. S1–S12 as 600-dpi PNG and vector PDF. See `docs/FIGURE_REPRODUCIBILITY.md` and `docs/A25_FINAL_FIGURE_SOURCE_MAP.csv`.

## Version

This repository is aligned with the A25 submission-locked manuscript and publication figure set. Historical release tags remain unchanged.

## License

Original code and documentation are released under the MIT License. eICU data remain governed by the PhysioNet Data Use Agreement and are not covered by the MIT License.
