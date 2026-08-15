# Lead-time event-definition audit

## Authoritative creatinine event

The event time is the first `labResultOffset` strictly after 720 minutes and through the earlier of ICU discharge or 4320 minutes at which `kdigo_creatinine_stage >= 2` in `{{GOOGLE_CLOUD_PROJECT}}.{{AKI_DATASET_ID}}.creatinine_staged_v1`. Offsets are minutes from ICU admission. The source pipeline deduplicates revised serum creatinine records at each stay/offset by retaining the latest `labResultRevisedOffset` (then largest `labID`), so ties are resolved before staging. Stage 2 is creatinine ratio ≥2.0; stage 3 is ratio ≥3.0 or creatinine ≥4.0 with the AKI definition met.

Audit: 3,032 event offsets; 0 had multiple staged rows; 0 had distinct creatinine values; maximum rows at an event offset=1.

## Event-time distribution (minutes after ICU admission)

{
  "n": 3032,
  "min": 721.0,
  "p10": 875.1,
  "p25": 1160.75,
  "median": 1818.0,
  "p75": 2546.25,
  "p90": 3454.4000000000005,
  "max": 4319.0
}

## RRT documentary audit

RRT was not added to or substituted for the creatinine-defined primary outcome. Counts in the primary cohort: {"strict_rrt_after_landmark_to72h": 349, "broad_rrt_after_landmark_to72h": 634, "io_dialysis_after_landmark_to72h": 523}. These fields are documentary because treatment-charting timing and indication are less reliable than the prespecified creatinine endpoint.
