# Frozen analysis protocols

These files document the locked cross-validation, candidate-model, calibration,
decision-curve, TreeSHAP, clinical-baseline, and renal-marker-ablation specifications.

They are protocol/configuration artifacts, not fitted patient-level models. No
patient-level rows, predictions, hospital assignment rows, or credentials are included.

The primary model was selected by inner hospital-disjoint cross-validation and evaluated
on held-out hospitals. Targeted strengthening analyses were performed after the primary
analysis freeze without changing the selected primary model.
