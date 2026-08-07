# Parameterized BigQuery SQL

Replace the placeholders before execution:

- `{{PROJECT_ID}}`: authorized Google Cloud project
- `{{DATASET_ID}}`: working dataset, normally `aki_jcmc_v2`

The source eICU dataset remains `physionet-data.eicu_crd` and requires credentialed
PhysioNet access and acceptance of the applicable Data Use Agreement.

Recommended construction order:

1. base stays
2. creatinine long table
3. renal flags
4. staged creatinine
5. final cohort/outcome
6. static features
7. laboratory features
8. vital-sign features
9. context features
10. full feature matrix and modeling view
11. core and extended views
12. hospital-disjoint outer-fold views

No credentials, patient-level extracts, or query results are included.
