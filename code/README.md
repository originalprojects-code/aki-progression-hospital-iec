# Source-only analysis notebooks

The notebooks are ordered by the frozen analysis workflow:

1. `01_AKI_V2_FEASIBILITY_SOURCE.ipynb`
2. `02_AKI_V2_COHORT_OUTCOME_SOURCE.ipynb`
3. `03_AKI_V2_FEATURE_INVENTORY_SOURCE.ipynb`
4. `04_AKI_V2_FEATURE_MATRIX_SOURCE.ipynb`
5. `05_AKI_V2_MODEL_DEVELOPMENT_SOURCE.ipynb`
6. `06_AKI_V2_STRENGTHENING_SOURCE.ipynb`
7. `07_AKI_V2_TABLE1_BASELINE_SOURCE.ipynb`

All notebooks are source-only. Outputs and execution history were removed before
public release. Execution requires credentialed eICU access through PhysioNet,
an authorized Google Cloud project, and the applicable Data Use Agreement.

Set the following environment variables or answer the notebook prompts:

- `GOOGLE_CLOUD_PROJECT`
- `AKI_DATASET_ID` (default: `aki_jcmc_v2`)
- `EICU_SOURCE_DATASET` (default: `physionet-data.eicu_crd`)
- `BIGQUERY_LOCATION` (default: `US`)
- `AKI_OUTPUT_ROOT` (default: `/content/AKI_JCMC_V2_PUBLIC_RUN`)

The primary analysis was frozen before the targeted strengthening and Table 1 runs.
The strengthening notebooks do not retune or reselect the primary model.
