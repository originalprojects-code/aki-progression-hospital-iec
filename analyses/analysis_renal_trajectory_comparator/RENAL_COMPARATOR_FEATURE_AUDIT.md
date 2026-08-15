# Renal comparator feature audit

## Authoritative temporal definitions

The reference creatinine is the earliest qualifying revised creatinine between max(hospital admission offset, -1440 min) and +360 min. Landmark summaries use valid laboratory results from 0 through 720 min. Stage 1 is `max_stage_by_12h = 1`; the outcome begins strictly after 720 min and extends through 72 h. The main cohort excludes stage 2-3 and strict acute RRT at or before 720 min.

Automated offset checks found **0 violations** among first/last creatinine offsets used for trajectory derivation. Stage 1 at landmark was present in 2,949 patients, including 781 subsequent events.

The primary comparator was prespecified before performance review as reference creatinine, last and maximum 0-12 h creatinine, creatinine slope per hour, measurement count, and landmark stage 1 status. Complete candidate decisions are in `outputs/renal_feature_audit.csv`. Urine output was rejected because no validated urine-output predictor exists in the locked registry. RRT was not used as a predictor: pre-landmark RRT defines exclusion and future RRT would leak outcome information.
