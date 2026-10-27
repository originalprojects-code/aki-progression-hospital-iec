# Paper 1 scientific data contracts

This versioned contract layer turns the Paper 1 audit into executable, synthetic checks. It does not execute BigQuery, load patient-level data, alter frozen SQL or notebooks, rebuild a cohort, or train a model.

## Scope

`src/aki_rebuild/contracts/v1.py` defines the 720-minute prediction landmark, censored primary outcome window `(720, min(discharge, 4320)]`, reference cohort-selection invariants, laboratory timing evidence, history timing evidence, respiratory timing evidence, and hospital-disjoint validation guards.

The primary outcome is explicitly `creatinine_based_kdigo_stage_2_or_3`. The separate RRT composite in the frozen implementation is not silently substituted for that primary outcome.

## Machine-readable records

- `contracts/feature_timing_policy.v1.json` is the feature timing policy.
- `contracts/decision_register.v1.json` lists unresolved scientific choices. Every listed decision remains `requires_researcher_approval`.
- `contracts/policy_traceability.v1.csv` links each policy to frozen source SQL/code and audit evidence.

The 58,491/3,032/198 original report and 59,612/3,060/199 original-code rebuild are historical audit references only. Neither is a corrected-cohort target. The 59,423 reference-only sensitivity is likewise not a corrected cohort.

## Timing cautions encoded here

A laboratory sample time, final revision time, and first-result availability are distinct. A missing availability time remains unknown; a late revision is not interpreted as evidence that the first result was late. Past history keeps `pastHistoryOffset` separate from `pastHistoryEnteredOffset`. Respiratory care keeps ventilation event time separate from documentation time. Infusion and treatment offsets retain their frozen documented semantics pending researcher approval.

The affected-patient figures in the decision register are not additive and do not demonstrate a changed prediction for any patient.

## Tests

Run local synthetic checks with:

```powershell
& 'C:\Users\bmmcagdas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -t . -v
```

The tests do not connect to BigQuery or read eICU data.
