# AKI Progression — Hospital-Disjoint Internal–External Validation

Reproducibility materials for the manuscript:

**Machine learning for early prediction of acute kidney injury progression in critically ill adults: hospital-disjoint internal–external validation**

Authors: Cagdas Yilmaz and Ali Akdagli

## Study summary

The primary cohort included 58,491 patients from 198 hospitals, with 3,032 serum-creatinine-defined KDIGO stage 2–3 progression events after a fixed 12-hour landmark. The primary XGBoost model was evaluated using hospital-disjoint internal–external cross-validation.

## Repository contents

- `code/`: seven source-only notebooks covering feasibility, cohort and outcome construction, feature preparation, model development, strengthening analyses, and Table 1
- `sql/`: parameterized BigQuery SQL used to construct the analysis tables
- `protocols/`: predefined model, calibration, decision-curve, TreeSHAP, clinical-comparator, and renal-marker-ablation specifications
- `aggregate_outputs/`: manuscript-level and fold-level aggregate results
- `checklists/`: data-privacy, reproducibility, and TRIPOD reporting checklists
- `docs/`: run order, data-access requirements, software environment, analysis scope, and reporting limits
- `figures/`: publication-oriented aggregate figures
- `release/`: file inventory, notebook source validation, and SHA-256 manifest

## Data access

The eICU Collaborative Research Database is available through PhysioNet to credentialed users who complete the required human-subjects research training and accept the applicable Data Use Agreement. Source data and patient-level derivatives are not redistributed in this repository.

## Reproduction configuration

The notebooks use configurable values for the authorized execution environment:

- `GOOGLE_CLOUD_PROJECT`
- `AKI_DATASET_ID` (default `aki_jcmc_v2`)
- `EICU_SOURCE_DATASET` (default `physionet-data.eicu_crd`)
- `BIGQUERY_LOCATION` (default `US`)
- `AKI_OUTPUT_ROOT`

See `docs/RUN_ORDER.md` and the files under `sql/` and `protocols/` for execution details.

## Interpretation

The validation design is hospital-disjoint internal–external cross-validation and should not be interpreted as independent external validation. The outcome is serum-creatinine-defined. SHAP values are non-causal model attributions. Decision-curve analysis estimates net benefit but does not establish clinical effectiveness. The renal-marker ablation is exploratory. Independent external and prospective evaluation remain necessary before clinical implementation.

## Version

Current source-package version: `v1.0.0-manuscript`.

## License

Original code and documentation are released under the MIT License. eICU data remain governed by the PhysioNet Data Use Agreement and are not covered by the MIT License.
