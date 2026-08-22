# Submission-stage robustness analyses

This submission snapshot adds source scripts corresponding to the manuscript-strengthening analyses performed after the initial v1.0.0-manuscript archive.

- `code/08_selection_bias_analysis.py` — cohort selection/representativeness characterization
- `code/09_high_missingness_ablation.py` — removal of highly sparse predictors
- `code/10_missingness_indicator_analysis.py` — explicit missingness-indicator attribution and no-indicator model
- `code/11_renal_trajectory_comparator.py` — renal-status and creatinine-trajectory comparators
- `code/12_subgroup_performance.py` — exploratory subgroup discrimination/calibration
- `code/13_lead_time_outcome_window.py` — actionable lead-time and outcome-window sensitivity
- `code/14_hospital_heterogeneity.py` — held-out hospital discrimination/calibration heterogeneity

The public copies preserve analysis logic while replacing machine-specific output-path literals with configurable environment paths. No scientific calculations, model specifications, cohort definitions, or reported results were changed by that portability cleanup.

The default environment variables follow the existing project configuration (`GOOGLE_CLOUD_PROJECT`, `AKI_DATASET_ID`, and `AKI_OUTPUT_ROOT`). Some scripts accept additional environment paths to inputs created by earlier strengthening analyses.

No patient-level data, patient-level prediction files, raw hospital identifier mappings, credentials, or Data Use Agreement-restricted derivatives are included in the submission snapshot.
