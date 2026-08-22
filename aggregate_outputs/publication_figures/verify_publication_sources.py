from pathlib import Path
import re
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
expected={
 "FIG_2_five_model_metrics_and_calibration.csv":5,
 "FIG_2_xgboost_calibration_deciles.csv":10,
 "FIG_3_decision_curve.csv":19,
 "FIG_3_grouped_treeshap.csv":15,
 "FIG_S2_tier_b_calibration_points.csv":51,
 "FIG_S3_operating_points_full.csv":6,
 "FIG_S4_reference_creatinine_sensitivity.csv":4,
 "FIG_S11_event_time_histogram.csv":15,
 "FIG_S12_tier_b_auroc.csv":51,
 "FIG_S12_tier_b_calibration.csv":51,
 "FIG_S12_all_hospital_calibration_context.csv":198,
}
for name,n in expected.items():
 p=HERE/name; assert p.exists(), f"Missing {name}"
 d=pd.read_csv(p); assert len(d)==n, f"{name}: expected {n}, found {len(d)}"
 bad=[c for c in d.columns if any(k in c.lower() for k in ("hospital_id","group_hospital","patientunitstayid","patient_id"))]
 assert not bad, f"{name}: prohibited identifier columns {bad}"
s3=pd.read_csv(HERE/"FIG_S3_operating_points_full.csv")
assert np.allclose(s3.threshold.to_numpy(),[.01,.02,.03,.05,.075,.10])
s11=pd.read_csv(HERE/"FIG_S11_event_time_histogram.csv")
assert int(s11.n_events.sum())==3032
assert s11.start_hour.tolist()==list(range(12,72,4))
f2=pd.read_csv(HERE/"FIG_2_five_model_metrics_and_calibration.csv")
assert f2.model.tolist()==["Clinical comparator","Logistic regression","Random forest","CatBoost","XGBoost"]
assert abs(float(f2.loc[f2.model.eq("XGBoost"),"auroc"].iloc[0])-0.8758038099504537)<1e-9
cal=pd.read_csv(HERE/"FIG_2_xgboost_calibration_deciles.csv")
assert int(cal.patients.sum())==58491 and int(cal.events.sum())==3032
dca=pd.read_csv(HERE/"FIG_3_decision_curve.csv")
assert np.allclose(dca.threshold_percent.to_numpy(),[1+.5*i for i in range(19)])
sh=pd.read_csv(HERE/"FIG_3_grouped_treeshap.csv")
assert sh.pooled_rank.tolist()==list(range(1,16))
hex64=re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
for name in expected:
 assert not hex64.search((HERE/name).read_text(encoding="utf-8")), f"{name}: possible hashed identifier"
print("PASS: publication-source integrity and disclosure-safety checks")
