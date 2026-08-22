# Publication figure aggregate sources (A25)

This directory contains disclosure-safe aggregate numerical sources required to
regenerate the final A25 publication figures from repository contents.

## Privacy rule
No patient-level rows are included. No hospital identifiers or hashed hospital
identifiers are included. Hospital-level artwork retains only anonymous numerical
coordinates required for the figure. Row-level predictions and row-level SHAP values
are not included.

## Figure-specific additions
- Fig. 2(a,b): five model AUROC/AUPRC point estimates and hospital-bootstrap 95% CIs.
- Fig. 2(c): pooled XGBoost Platt-calibrated risk deciles.
- Fig. 3(a): 19 prespecified decision-curve thresholds from 1% to 10%.
- Fig. 3(b): top 15 pooled grouped TreeSHAP source-predictor attributions.
- Fig. S2: 51 anonymous Tier-B calibration points.
- Fig. S3: all six prespecified operating points (1%, 2%, 3%, 5%, 7.5%, 10%).
- Fig. S4: four reference-creatinine sensitivity phenotypes.
- Fig. S11(a): 15 four-hour event-time bins, 12–72 h; counts sum to 3,032.
- Fig. S12(a): 51 anonymous Tier-B AUROC values.
- Fig. S12(b): 51 anonymous Tier-B calibration intercept/slope pairs.
- Fig. S12(c): 198 anonymous all-hospital calibration-context points.

`PUBLICATION_FIGURE_SOURCE_MANIFEST.csv` records provenance, retained fields, privacy
transformation, row counts, and SHA-256 hashes.

These files support publication-artifact reproduction; they do not replace the
restricted clinical source data or the full credentialed analysis pipeline.
