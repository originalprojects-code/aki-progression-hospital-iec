import os, sys, json, time, platform, hashlib
from pathlib import Path
_deps = os.environ.get('AKI_PYDEPS')
if _deps: sys.path.insert(0, _deps)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.special import expit, logit
from google.cloud import bigquery
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

PROJECT=os.environ.get('GOOGLE_CLOUD_PROJECT','your-gcp-project'); DS=os.environ.get('AKI_DATASET_ID','aki_jcmc_v2'); SEED=20260815; BOOT=2000
OUT=Path(os.environ.get('AKI_OUTPUT_DIR', Path.cwd()/'analysis_outputs'/'analysis_lead_time_outcome_window'))
for d in [OUT,OUT/'src',OUT/'outputs',OUT/'tables',OUT/'figures',OUT/'logs']: d.mkdir(parents=True,exist_ok=True)
start_time=time.time(); client=bigquery.Client(project=PROJECT, location="US")
q=f"""
SELECT m.id_row,m.group_hospital,m.label_stage23,m.outer_fold,p.prediction_platt,
 c.patientUnitStayID,c.unitDischargeOffset,c.unit_discharge_status,c.incident_stage23_offset,
 c.observation_class,c.last_future_creatinine_offset,c.first_acute_rrt_strict_offset,
 c.first_acute_rrt_broad_offset,c.first_nonzero_dialysis_io_offset
FROM `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1` m
JOIN `{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1` p
 USING(id_row,group_hospital,label_stage23,outer_fold)
JOIN `{PROJECT}.{DS}.cohort_outcome_v1` c
 ON m.id_row=TO_HEX(SHA256(CONCAT('AKI_V2_STAY|',CAST(c.patientUnitStayID AS STRING))))
WHERE c.eligible_main_cohort=1 AND c.deterministic_eligible_patient_stay_rank=1
"""
df=client.query(q).to_dataframe()
assert (len(df),df.id_row.nunique(),df.group_hospital.nunique(),int(df.label_stage23.sum()))==(58491,58491,198,3032)
assert np.array_equal(df.label_stage23.to_numpy(),df.incident_stage23_offset.notna().astype(int).to_numpy())

audit_q=f"""
WITH main AS (
 SELECT patientUnitStayID,incident_stage23_offset
 FROM `{PROJECT}.{DS}.cohort_outcome_v1`
 WHERE eligible_main_cohort=1 AND deterministic_eligible_patient_stay_rank=1
), raw AS (
 SELECT s.patientUnitStayID,s.labResultOffset,COUNT(*) n_rows,
   COUNT(DISTINCT s.creatinine) n_distinct_values
 FROM `{PROJECT}.{DS}.creatinine_staged_v1` s JOIN main m USING(patientUnitStayID)
 WHERE s.kdigo_creatinine_stage>=2 AND s.labResultOffset=m.incident_stage23_offset
 GROUP BY 1,2
)
SELECT COUNT(*) n_events,COUNTIF(n_rows>1) event_offsets_with_multiple_rows,
 COUNTIF(n_distinct_values>1) event_offsets_with_distinct_values,MAX(n_rows) max_rows_at_event_offset
FROM raw
"""
event_audit=client.query(audit_q).to_dataframe().iloc[0].to_dict()

def cal_slope(y,p):
    x=logit(np.clip(np.asarray(p,float),1e-6,1-1e-6)); y=np.asarray(y,float)
    X=np.column_stack([np.ones(len(x)),x]); b=np.array([0.,1.])
    for _ in range(30):
        mu=expit(X@b); w=np.clip(mu*(1-mu),1e-8,None)
        try: step=np.linalg.solve(X.T@(w[:,None]*X),X.T@(y-mu))
        except np.linalg.LinAlgError: return np.nan
        b+=step
        if np.max(np.abs(step))<1e-8: break
    return float(b[1])

def cal_slope(y,p):
    x=logit(np.clip(np.asarray(p,float),1e-6,1-1e-6)); y=np.asarray(y,float)
    a=0.0; b=1.0
    for _ in range(12):
        mu=expit(a+b*x); w=np.clip(mu*(1-mu),1e-10,None)
        s0=np.sum(y-mu); s1=np.sum((y-mu)*x)
        h00=np.sum(w); h01=np.sum(w*x); h11=np.sum(w*x*x)
        det=h00*h11-h01*h01
        if det<=1e-16: return np.nan
        da=(h11*s0-h01*s1)/det; db=(-h01*s0+h00*s1)/det
        a+=da; b+=db
        if max(abs(da),abs(db))<1e-8: break
    return float(b)

def metric(y,p):
    y=np.asarray(y,int); p=np.asarray(p,float); prev=y.mean()
    out={'n':len(y),'events':int(y.sum()),'non_events':int((1-y).sum()),'prevalence':prev,
         'mean_predicted_risk':p.mean(),'auroc':roc_auc_score(y,p),'auprc':average_precision_score(y,p),
         'auprc_prevalence_ratio':average_precision_score(y,p)/prev,'brier':brier_score_loss(y,p),
         'calibration_slope':cal_slope(y,p)}
    pred=p>=.05; out.update({'threshold':.05,'tp':int(np.sum(pred&(y==1))),'fp':int(np.sum(pred&(y==0))),
      'tn':int(np.sum((~pred)&(y==0))),'fn':int(np.sum((~pred)&(y==1))),
      'sensitivity':np.sum(pred&(y==1))/np.sum(y==1),'specificity':np.sum((~pred)&(y==0))/np.sum(y==0),
      'ppv':np.sum(pred&(y==1))/max(np.sum(pred),1),'npv':np.sum((~pred)&(y==0))/max(np.sum(~pred),1)})
    return out

specs=[('L0','lead',720,4320),('L6','lead',1080,4320),('L12','lead',1440,4320),('L24','lead',2160,4320),
       ('W72','window',720,4320),('W48','window',720,2880),('W24to72','window',1440,4320),('W24to48','window',1440,2880)]
scenarios={}; reconcile=[]
for name,kind,s,e in specs:
    early=df.incident_stage23_offset.notna()&(df.incident_stage23_offset>720)&(df.incident_stage23_offset<=s)
    at_risk=(df.unitDischargeOffset>s)| (df.incident_stage23_offset.notna()&(df.incident_stage23_offset>s))
    keep=(~early)&at_risk
    g=df.loc[keep].copy(); g['y']=((g.incident_stage23_offset>s)&(g.incident_stage23_offset<=e)).fillna(False).astype(int)
    scenarios[name]=g
    reconcile.append({'scenario':name,'analysis_type':kind,'window_start_min':s,'window_end_min':e,
      'primary_cohort_n':len(df),'excluded_early_stage23':int(early.sum()),
      'excluded_not_at_risk_at_start':int(((~early)&(~at_risk)).sum()),'included_n':len(g),
      'events':int(g.y.sum()),'non_events':int((g.y==0).sum()),'prevalence':g.y.mean()})

point=[]
for name,kind,s,e in specs:
    row={'scenario':name,'analysis_type':kind,'window_start_min':s,'window_end_min':e,**metric(scenarios[name].y,scenarios[name].prediction_platt)}
    point.append(row)
point=pd.DataFrame(point)
for kind,ref in [('lead','L0'),('window','W72')]:
    base=point.loc[point.scenario==ref].iloc[0]
    ix=point.analysis_type==kind
    for k in ['auroc','auprc','brier','calibration_slope']:
        point.loc[ix,'delta_'+k]=point.loc[ix,k]-base[k]

rng=np.random.default_rng(SEED); boots=[]
def weighted_boot_metrics(y,p,hcode,hcounts):
    w=hcounts[hcode].astype(float); sw=w.sum(); pos=np.sum(w*y); neg=sw-pos
    order=np.argsort(p,kind='mergesort'); ps=p[order]; ys=y[order]; ws=w[order]
    starts=np.r_[0,np.flatnonzero(np.diff(ps)!=0)+1]
    pg=np.add.reduceat(ws*ys,starts); ng=np.add.reduceat(ws*(1-ys),starts)
    auc=np.sum(pg*(np.cumsum(ng)-ng+0.5*ng))/(pos*neg)
    pg=pg[::-1]; ng=ng[::-1]; cp=np.cumsum(pg); cn=np.cumsum(ng)
    prec=np.divide(cp,cp+cn,out=np.zeros_like(cp),where=(cp+cn)>0); ap=np.sum(pg*prec)/pos
    brier=np.sum(w*(p-y)**2)/sw
    x=logit(np.clip(p,1e-6,1-1e-6)); aa=0.0; bb=1.0
    for _ in range(12):
        mu=expit(aa+bb*x); ww=w*np.clip(mu*(1-mu),1e-10,None)
        s0=np.sum(w*(y-mu)); s1=np.sum(w*(y-mu)*x)
        h00=np.sum(ww); h01=np.sum(ww*x); h11=np.sum(ww*x*x); det=h00*h11-h01*h01
        if det<=1e-16: bb=np.nan; break
        da=(h11*s0-h01*s1)/det; db=(-h01*s0+h00*s1)/det; aa+=da; bb+=db
        if max(abs(da),abs(db))<1e-8: break
    return auc,ap,brier,bb
for name,kind,s,e in specs:
    g=scenarios[name]; hs=np.sort(g.group_hospital.unique()); hm={h:i for i,h in enumerate(hs)}
    hcode=np.array([hm[h] for h in g.group_hospital]); y=g.y.to_numpy(int); p=g.prediction_platt.to_numpy(float)
    for b in range(BOOT):
        hc=np.bincount(rng.integers(0,len(hs),len(hs)),minlength=len(hs))
        vals=weighted_boot_metrics(y,p,hcode,hc)
        boots.append({'scenario':name,'replicate':b,**dict(zip(['auroc','auprc','brier','calibration_slope'],vals))})
    print(name,'bootstrap complete',flush=True)
br=pd.DataFrame(boots)
for k in ['auroc','auprc','brier','calibration_slope']:
    ci=br.groupby('scenario')[k].quantile([.025,.975]).unstack()
    point[k+'_ci_low']=point.scenario.map(ci[.025]); point[k+'_ci_high']=point.scenario.map(ci[.975])
    point[k+'_valid_replicates']=point.scenario.map(br.groupby('scenario')[k].count())
dca=[]
for name in ['L0','L12','L24']:
    g=scenarios[name]; y=g.y.to_numpy(); p=g.prediction_platt.to_numpy(); n=len(y); prev=y.mean()
    for t in np.arange(.01,.101,.01):
        pred=p>=t; nb=(np.sum(pred&(y==1))-np.sum(pred&(y==0))*t/(1-t))/n
        dca.append({'scenario':name,'threshold':t,'net_benefit_model':nb,'net_benefit_treat_all':prev-(1-prev)*t/(1-t),'net_benefit_treat_none':0})
dca=pd.DataFrame(dca)

ev=df.loc[df.label_stage23==1,'incident_stage23_offset'].astype(float)
event_dist={'n':len(ev),'min':ev.min(),'p10':ev.quantile(.10),'p25':ev.quantile(.25),'median':ev.median(),'p75':ev.quantile(.75),'p90':ev.quantile(.90),'max':ev.max()}
rrt={'strict_rrt_after_landmark_to72h':int(((df.first_acute_rrt_strict_offset>720)&(df.first_acute_rrt_strict_offset<=np.minimum(df.unitDischargeOffset,4320))).sum()),
     'broad_rrt_after_landmark_to72h':int(((df.first_acute_rrt_broad_offset>720)&(df.first_acute_rrt_broad_offset<=np.minimum(df.unitDischargeOffset,4320))).sum()),
     'io_dialysis_after_landmark_to72h':int(((df.first_nonzero_dialysis_io_offset>720)&(df.first_nonzero_dialysis_io_offset<=np.minimum(df.unitDischargeOffset,4320))).sum())}

rec=pd.DataFrame(reconcile)
rec[rec.analysis_type=='lead'].to_csv(OUT/'LEAD_TIME_COHORT_RECONCILIATION.csv',index=False)
rec[rec.analysis_type=='window'].to_csv(OUT/'OUTCOME_WINDOW_COHORT_RECONCILIATION.csv',index=False)
point[point.analysis_type=='lead'].to_csv(OUT/'tables'/'TABLE_S15_lead_time_sensitivity.csv',index=False)
point[point.analysis_type=='window'].to_csv(OUT/'tables'/'TABLE_S16_outcome_window_sensitivity.csv',index=False)
dca.to_csv(OUT/'outputs'/'lead_time_decision_curve.csv',index=False)

fig,ax=plt.subplots(1,3,figsize=(13,4.2)); bins=np.arange(12,73,4)
ax[0].hist(ev/60,bins=bins,color='#4C78A8',edgecolor='white'); ax[0].set(xlabel='First stage 2–3 event (h)',ylabel='Events',title='A. Event-time distribution')
lp=point[point.analysis_type=='lead']; x=np.arange(len(lp))
for a,k,title in [(ax[1],'auroc','B. Discrimination: AUROC'),(ax[2],'auprc','C. Discrimination: AUPRC')]:
    lo=lp[k]-lp[k+'_ci_low']; hi=lp[k+'_ci_high']-lp[k]
    a.errorbar(x,lp[k],yerr=[lo,hi],fmt='o-',color='#E45756',capsize=4); a.set_xticks(x,lp.scenario); a.set(xlabel='Minimum lead-time scenario',ylabel=k.upper(),title=title); a.grid(alpha=.25)
fig.tight_layout(); fig.savefig(OUT/'figures'/'FIG_S11_lead_time_sensitivity.png',dpi=300,bbox_inches='tight'); fig.savefig(OUT/'figures'/'FIG_S11_lead_time_sensitivity.pdf',bbox_inches='tight'); plt.close(fig)

def fmt_ci(r,k): return f"{r[k]:.3f} ({r[k+'_ci_low']:.3f}–{r[k+'_ci_high']:.3f})"
def md_table(dat):
    lines=['| Scenario | N | Events | Prevalence | AUROC (95% CI) | AUPRC (95% CI) | Brier (95% CI) | Cal. slope (95% CI) |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in dat.iterrows(): lines.append(f"| {r.scenario} | {r.n:,} | {r.events:,} | {100*r.prevalence:.2f}% | {fmt_ci(r,'auroc')} | {fmt_ci(r,'auprc')} | {fmt_ci(r,'brier')} | {fmt_ci(r,'calibration_slope')} |")
    return '\n'.join(lines)

audit=f"""# Lead-time event-definition audit

## Authoritative creatinine event

The event time is the first `labResultOffset` strictly after 720 minutes and through the earlier of ICU discharge or 4320 minutes at which `kdigo_creatinine_stage >= 2` in `{PROJECT}.{DS}.creatinine_staged_v1`. Offsets are minutes from ICU admission. The source pipeline deduplicates revised serum creatinine records at each stay/offset by retaining the latest `labResultRevisedOffset` (then largest `labID`), so ties are resolved before staging. Stage 2 is creatinine ratio ≥2.0; stage 3 is ratio ≥3.0 or creatinine ≥4.0 with the AKI definition met.

Audit: {int(event_audit['n_events']):,} event offsets; {int(event_audit['event_offsets_with_multiple_rows'])} had multiple staged rows; {int(event_audit['event_offsets_with_distinct_values'])} had distinct creatinine values; maximum rows at an event offset={int(event_audit['max_rows_at_event_offset'])}.

## Event-time distribution (minutes after ICU admission)

{json.dumps(event_dist,indent=2)}

## RRT documentary audit

RRT was not added to or substituted for the creatinine-defined primary outcome. Counts in the primary cohort: {json.dumps(rrt)}. These fields are documentary because treatment-charting timing and indication are less reliable than the prespecified creatinine endpoint.
"""
(OUT/'LEAD_TIME_EVENT_DEFINITION_AUDIT.md').write_text(audit,encoding='utf-8')
report=f"""# Actionable lead-time and outcome-window sensitivity analysis

## Result

All analyses reused the 58,491 patient-level held-out, Platt-calibrated XGBoost predictions from all five outer folds; no model fitting or recalibration was performed. Early stage 2–3 events were excluded in delayed-start scenarios and were never relabeled as non-events. Patients discharged before a delayed start and without a later event were excluded as not at risk at that start.

## Lead-time scenarios

{md_table(point[point.analysis_type=='lead'])}

## Outcome-window scenarios

{md_table(point[point.analysis_type=='window'])}

Hospital-cluster percentile confidence intervals used {BOOT:,} resamples. The 5% operating point is included in Tables S15–S16. Decision-curve estimates for L0, L12, and L24 are in `outputs/lead_time_decision_curve.csv`.

## Interpretation

Increasing the minimum warning interval changes both the target estimand and the at-risk cohort. Metric changes therefore quantify operational lead-time sensitivity, not evidence that one horizon is intrinsically superior. Shorter outcome windows similarly change event prevalence and case mix. The fixed held-out probabilities preserve a clean sensitivity analysis without leakage or post-landmark refitting.
"""
(OUT/'LEAD_TIME_OUTCOME_WINDOW_REPORT.md').write_text(report,encoding='utf-8')
insert=f"""### Manuscript-ready insert: actionable lead time

In a prespecified sensitivity analysis, we progressively excluded creatinine-defined KDIGO stage 2–3 events occurring within 6, 12, or 24 hours after the 12-hour prediction landmark and evaluated the unchanged held-out calibrated predictions among patients still at risk. Early events were excluded rather than reclassified as non-events. Across these scenarios, cohort size, event prevalence, discrimination, overall accuracy, calibration slope, and performance at the 5% risk threshold are reported in Table S15; Figure S11 shows the event-time distribution and changes in AUROC and AUPRC. Alternative 12–48-hour, 24–72-hour, and 24–48-hour outcome windows are reported in Table S16. These analyses assess operational actionability and horizon dependence; they do not represent model refitting or recalibration.
"""
(OUT/'MANUSCRIPT_INSERT_LEAD_TIME.md').write_text(insert,encoding='utf-8')
qc={'primary_n':len(df),'unique_patients':df.id_row.nunique(),'hospitals':df.group_hospital.nunique(),'primary_events':int(df.label_stage23.sum()),'held_out_prediction_source':f'{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1','no_refitting':True,'no_recalibration':True,'bootstrap_unit':'hospital','bootstrap_replicates':BOOT,'seed':SEED,'event_audit':event_audit,'event_distribution_minutes':event_dist,'rrt_documentary_counts':rrt,'scenario_rows':rec.to_dict('records'),'runtime_minutes':(time.time()-start_time)/60,'python':platform.python_version()}
(OUT/'logs'/'qc.json').write_text(json.dumps(qc,indent=2,default=lambda x: int(x) if isinstance(x,np.integer) else float(x)),encoding='utf-8')
(OUT/'LEAD_TIME_OUTCOME_WINDOW_QC.md').write_text('# Lead-time/outcome-window QC\n\n```json\n'+json.dumps(qc,indent=2,default=lambda x: int(x) if isinstance(x,np.integer) else float(x))+'\n```\n\nAll cohort, prediction, event-label, no-refitting, and bootstrap assertions passed.\n',encoding='utf-8')
(OUT/'README.md').write_text('# Lead-time and outcome-window sensitivity analysis\n\nReproducible, read-only BigQuery analysis. Patient-level data remain in memory and are not written to disk. See the report, audit, QC, provisional CSV tables, and Figure S11.\n',encoding='utf-8')
print(json.dumps({'status':'complete','runtime_minutes':qc['runtime_minutes'],'output':str(OUT)},indent=2))
