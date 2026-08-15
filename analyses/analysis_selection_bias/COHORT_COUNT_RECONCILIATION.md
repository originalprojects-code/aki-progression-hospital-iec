# Cohort count reconciliation

The manuscript flow and the selection-analysis universe are different counting layers and must not be subtracted interchangeably.

| Layer | Unit/count | Explanation |
|---|---:|---|
| Adult ICU stays ≥12 h | 172,392 stays | Initial stay-level screen |
| First eligible ICU unit per hospital stay | 154,529 stays | One eligible ICU unit per hospital stay; still not one row per unique patient |
| Qualifying reference creatinine | 94,093 stays | Stay-level manuscript flow checkpoint |
| Patient-level deterministic comparison universe | 126,324 patients/stays | Excludes cross-hospital patients and retains the deterministic patient/stay rank 1 |
| Group B: no qualifying reference creatinine | 41,614 patients | Mutually exclusive patient-level group after the additional patient-level restrictions |
| Final primary cohort | 58,491 patients | Group A |
| Other post-reference exclusions | 26,219 patients | Group C |

Thus 154,529 âˆ’ 94,093 = 60,436 is a stay-level transition, whereas 41,614 is a patient-level mutually exclusive comparison group. The difference reflects cross-hospital-patient exclusion and deterministic selection of one analytic stay per unique patient. It is not a manuscript inconsistency. The three comparison groups reconcile exactly: 58,491 + 41,614 + 26,219 = 126,324.
