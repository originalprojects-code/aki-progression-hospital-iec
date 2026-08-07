# Reproduction run order

1. Complete PhysioNet credentialing and accept the eICU Data Use Agreement.
2. Configure an authorized Google Cloud project and working BigQuery dataset.
3. Run feasibility/source audit.
4. Construct the cohort and serum-creatinine-defined outcome.
5. Run predictor inventory and temporal audit.
6. Construct the extended and core feature matrices.
7. Run hospital-disjoint model development and evaluation.
8. Verify the frozen result registry.
9. Run targeted strengthening analyses without model reselection or retuning.
10. Generate the aggregate baseline-characteristics table.

The primary prediction landmark is 12 hours after ICU admission. Predictors use only
information available by the landmark. The serum-creatinine-defined stage 2–3 outcome
window is strictly after 12 hours through 72 hours. Validation is hospital-disjoint
internal–external cross-validation, not independent external validation.
